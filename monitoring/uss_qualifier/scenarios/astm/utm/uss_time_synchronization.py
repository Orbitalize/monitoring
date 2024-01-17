from datetime import datetime, timedelta
from typing import Dict

import arrow
import loguru
from implicitdict import StringBasedDateTime
from uas_standards.astm.f3548.v21.api import (
    OperationalIntentReference,
    OperationalIntent,
    Volume3D,
    Volume4D,
    OperationalIntentState,
    Time,
    OperationalIntentDetails,
)
from uas_standards.astm.f3548.v21.constants import Scope

from monitoring import monitorlib
from monitoring.monitorlib import geotemporal
from monitoring.monitorlib.clients.flight_planning.client import FlightPlannerClient
from monitoring.monitorlib.clients.flight_planning.client_scd import (
    SCDFlightPlannerClient,
)
from monitoring.monitorlib.clients.flight_planning.flight_info import (
    AirspaceUsageState,
    UasState,
)
from monitoring.monitorlib.clients.flight_planning.flight_info_template import (
    FlightInfoTemplate,
)
from monitoring.monitorlib.geo import make_latlng_rect
from monitoring.monitorlib.geotemporal import Volume4DCollection
from monitoring.monitorlib.infrastructure import UTMClientSession
from monitoring.monitorlib.mutate import scd as mutate
from monitoring.monitorlib.temporal import TimeDuringTest
from monitoring.prober.infrastructure import register_resource_type
from monitoring.uss_qualifier.resources import PlanningAreaResource
from monitoring.uss_qualifier.resources.astm.f3548.v21 import DSSInstanceResource
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import (
    DSSInstance,
    DUMMY_USS_BASE_URL,
)
from monitoring.uss_qualifier.resources.flight_planning import (
    FlightPlannerResource,
    FlightIntentsResource,
)
from monitoring.uss_qualifier.resources.flight_planning.flight_intent import (
    FlightIntent,
)
from monitoring.uss_qualifier.resources.flight_planning.flight_intent_validation import (
    ExpectedFlightIntent,
    validate_flight_intent_templates,
)
from monitoring.uss_qualifier.resources.interuss import IDGeneratorResource
from monitoring.uss_qualifier.scenarios.astm.utm.dss import test_step_fragments
from monitoring.uss_qualifier.scenarios.astm.utm.test_steps import OpIntentValidator
from monitoring.uss_qualifier.scenarios.flight_planning.test_steps import plan_flight
from monitoring.uss_qualifier.scenarios.scenario import TestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext


class USSTimeSynchronization(TestScenario):
    """
    A scenario that verifies that the USS is properly synchronizing its clocks and using the correct
    time in everything it timestamps.
    """

    OP_INTENT = register_resource_type(379, "Operational Intent Reference")
    SUB_ID = register_resource_type(380, "Subscription")

    _dss: DSSInstance

    _uss_client: FlightPlannerClient

    _op_intent_id: str
    _sub_id: str

    _intents_extent: geotemporal.Volume4D

    _flight_template: FlightInfoTemplate

    # Set via setattr in the constructor
    flight_1: FlightInfoTemplate

    def __init__(
        self,
        id_generator: IDGeneratorResource,
        dss: DSSInstanceResource,
        tested_uss: FlightPlannerResource,
        flight_intents: FlightIntentsResource,
    ):
        super().__init__()
        self._dss = dss.get_instance(
            {
                Scope.StrategicCoordination: "create operational intent references on the DSS to simulate operational intent creation and updates on a USS",
            }
        )
        # TODO proper resource (or cast/check here?)
        self._uss_client = tested_uss.client

        self._op_intent_id = id_generator.id_factory.make_id(self.OP_INTENT)
        self._sub_id = id_generator.id_factory.make_id(self.SUB_ID)

        expected_flight_intents = [
            ExpectedFlightIntent(
                "flight_1",
                "Flight 1",
                usage_state=AirspaceUsageState.Planned,
                uas_state=UasState.Nominal,
            ),
        ]

        templates = flight_intents.get_flight_intents()
        try:
            validate_flight_intent_templates(templates, expected_flight_intents)
        except ValueError as e:
            raise ValueError(
                f"`{self.me()}` TestScenario requirements for flight_intents not met: {e}"
            )

        f1_template = templates["flight_1"]
        intent = FlightIntent.from_flight_info_template(f1_template)
        extents = intent.request.operational_intent.volumes
        self._flight_1 = f1_template
        self._flight_1_extents = extents

        self._intents_extent = Volume4DCollection.from_interuss_scd_api(
            extents
        ).bounding_volume

    def run(self, context: ExecutionContext):
        times = {
            TimeDuringTest.StartOfTestRun: monitorlib.temporal.Time(context.start_time),
            TimeDuringTest.StartOfScenario: monitorlib.temporal.Time(
                arrow.utcnow().datetime
            ),
        }
        self.begin_test_scenario(context)

        self.begin_test_case("Setup")

        self.begin_test_step("Ensure clean workspace")
        # TODO remove: the flight planner preparation should guarantee that we start
        # from a clean state
        self._ensure_test_entities_do_not_exist()
        self.end_test_step()
        self.end_test_case()

        self.begin_test_case("Attempt to plan something in the past")
        self.begin_test_step("Attempt to plan something in the past")
        self._try_to_plan_in_the_past(times)

        self.end_test_step()

        self.end_test_case()

        self.end_test_scenario()

    def _ensure_test_entities_do_not_exist(self):

        test_step_fragments.cleanup_sub(
            self, self._dss, self._sub_id
        )

        (oi_ref, q) = self._dss.get_op_intent_reference(self._op_intent_id)
        self.record_query(q)

        with self.check(
            "Operational intent references can be queried by ID",
            [self._dss.participant_id],
        ) as check:
            if q.status_code not in [200, 404]:
                check.record_failed(
                    summary=f"Operational intent reference query failed",
                    details=f"Operational intent reference query failed with status code {q.status_code}. We expected either a proper response or a 404.",
                    query_timestamps=[q.request.timestamp],
                )

        if oi_ref is None:
            return

        _, _, q = self._dss.delete_op_intent(self._op_intent_id, oi_ref.ovn)
        self.record_query(q)

        with self.check(
            "Operational intent references can be deleted by their owner",
            [self._dss.participant_id],
        ) as check:
            if q.status_code != 200:
                check.record_failed(
                    summary=f"Operational intent reference deletion failed",
                    details=f"Operational intent reference deletion returned with status code {q.status_code} where 200 was expected.",
                    query_timestamps=[q.request.timestamp],
                )

        q = mutate.upsert_operational_intent(
            self._uss_client._session,
            operational_intent_id=self._op_intent_id,
            operational_intent=_op_intent_for_deletion(oi_ref),
            subscriptions=[],  # confirm if we're allowed to omit this?
            participant_id=self._uss_client.participant_id,
        )
        self.record_query(q)

        with self.check(
            "Operational intent can be removed from the USS",
            [self._uss_client.participant_id],
        ) as check:
            if q.status_code not in [200, 404]:
                check.record_failed(
                    summary="Operational intent update failed on the USS",
                    details=f"The USS is expected to accept deletion requests for operational intents. The response code was {q.status_code}.",
                    query_timestamps=[q.request.timestamp],
                )

    def _try_to_plan_in_the_past(self, times: Dict[TimeDuringTest, Time]):
        # TODO - request that the USS plan a flight
        #      - Create an operational intent on the DSS that requires us to notify the USS
        #      - Call the USS via the base_url it specified in its subscription
        #      - send a notification for an operational intent that ends in the past and check it fails

        # Request that the USS plan a flight
        times[TimeDuringTest.TimeOfEvaluation] = monitorlib.temporal.Time(
            arrow.utcnow().datetime
        )
        flight_1 = self._flight_1.resolve(times)
        with OpIntentValidator(
            self,
            self._uss_client,
            self._dss,
            self._intents_extent.to_f3548v21(),
        ) as validator:
            flight_1_planning_time = monitorlib.temporal.Time(arrow.utcnow().datetime)
            _, self._flight_1_id = plan_flight(self, self._uss_client, flight_1)
            flight_1_oi_ref = validator.expect_shared(flight_1)

        # start 10 minutes from now
        start_time = datetime.utcnow()
        # end 10 minutes later
        end_time = start_time + timedelta(minutes=10)

        # Create a subscriptions to get op intent ref
        new_sub = self._dss.upsert_subscription(
            area_vertices=make_latlng_rect(self._intents_extent.volume),
            start_time=start_time,
            end_time=end_time,
            base_url=DUMMY_USS_BASE_URL,
            sub_id=self._sub_id,
            notify_for_op_intents=True,
            notify_for_constraints=False,
            min_alt_m=0,
            max_alt_m=3048,
        )

        loguru.logger.debug(f"new_sub: {new_sub}")

        ovns = [oir.ovn for oir in new_sub.operational_intent_references]
        loguru.logger.debug(f"ovns: {ovns}")
        oir, _, q = self._dss.put_op_intent(
            id=self._op_intent_id,
            extents=self._flight_1_extents,
            key=ovns,
            state=OperationalIntentState.Accepted,
            base_url=DUMMY_USS_BASE_URL,
        )
        self.record_query(q)

        with self.check(
            "Create an operational intent on the DSS", [self._dss.participant_id]
        ) as check:
            if q.status_code != 201:
                loguru.logger.debug(f"failed creation response: {q}"),
                check.record_failed(
                   f"Could not create operational intent",
                    details=f"DSS responded with {q.response.status_code} to attempt to create OI {self._op_intent_id}",
                    query_timestamps=[q.request.timestamp],
                )


        # Better way to pass creds? Should we be using the mock_uss?
        uss_session = UTMClientSession(
            prefix_url=uss_notif_url,
            auth_adapter=self._uss_client._session.auth_adapter,
        )

        q = mutate.upsert_operational_intent(
            utm_client=uss_session,
            operational_intent_id=self._op_intent_id,
            operational_intent=OperationalIntent(
                reference=oir,
                details=OperationalIntentDetails(volume=extents),
            ),
            subscriptions=[],
            participant_id=self._uss_client.participant_id,
        )
        self.record_query(q)
        with self.check(
            "Notify USS of operational intent with valid details",
            [self._uss_client.participant_id],
        ) as check:
            if q.status_code != 200:
                loguru.logger.debug(f"failed notification response: {q.response.body}"),
                loguru.logger.debug(f"query details: {q.request}")
                check.record_failed(
                    summary="Operational intent update failed on the USS",
                    details=f"The USS is expected to accept operational intent updates. The response code was {q.status_code}.",
                    query_timestamps=[q.request.timestamp],
                )

    def cleanup(self):
        self.begin_cleanup()
        self._ensure_test_entities_do_not_exist()
        self.end_cleanup()


def _op_intent_for_deletion(oir: OperationalIntentReference) -> OperationalIntent:
    # From the OpenAPI spec: to delete an operational intent
    # the 'operational_intent_reference' must be omitted, but the nested reference must still
    # contain the ovn.
    # My first interpretation of this is that we only pass the ovn and omit all the other fields and nested fields
    return OperationalIntent(
        reference=OperationalIntentReference(
            id=oir.id,
            manager=None,
            uss_availability=None,
            version=None,
            state=None,
            ovn=oir.ovn,
            time_start=None,
            time_end=None,
            uss_base_url=None,
            subscription_id=None,
        ),
        details=None,
    )
