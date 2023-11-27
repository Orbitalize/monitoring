from datetime import datetime
from typing import Optional, Dict

from monitoring.monitorlib import schema_validation
from monitoring.monitorlib.fetch import rid as fetch
from monitoring.monitorlib.fetch.rid import (
    ISA,
    FetchedISA,
    FetchedISAs,
    Subscription,
    FetchedSubscription,
    FetchedSubscriptions,
)
from monitoring.monitorlib.infrastructure import UTMClientSession
from monitoring.monitorlib.mutate import rid as mutate
from monitoring.monitorlib.mutate.rid import ChangedISA, ChangedSubscription
from monitoring.monitorlib.rid import RIDVersion
from monitoring.uss_qualifier.common_data_definitions import Severity
from monitoring.uss_qualifier.scenarios.scenario import (
    GenericTestScenario,
    PendingCheck,
)

MAX_SKEW = 1e-6  # seconds maximum difference between expected and actual timestamps


def delete_isa_if_exists(
    scenario: GenericTestScenario,
    isa_id: str,
    rid_version: RIDVersion,
    session: UTMClientSession,
    participant_id: Optional[str] = None,
):
    fetched = fetch.isa(
        isa_id,
        rid_version=rid_version,
        session=session,
        participant_id=participant_id,
    )
    scenario.record_query(fetched.query)
    with scenario.check("Successful ISA query", [participant_id]) as check:
        if not fetched.success and fetched.status_code != 404:
            check.record_failed(
                "ISA information could not be retrieved",
                Severity.High,
                f"{participant_id} DSS instance returned {fetched.status_code} when queried for ISA {isa_id}",
                query_timestamps=[fetched.query.request.timestamp],
            )

    if fetched.success:
        deleted = mutate.delete_isa(
            isa_id,
            fetched.isa.version,
            rid_version,
            session,
            participant_id=participant_id,
        )
        scenario.record_query(deleted.dss_query.query)
        for subscriber_id, notification in deleted.notifications.items():
            scenario.record_query(notification.query)
        with scenario.check("Removed pre-existing ISA", [participant_id]) as check:
            if not deleted.dss_query.success:
                check.record_failed(
                    "Could not delete pre-existing ISA",
                    Severity.High,
                    f"Attempting to delete ISA {isa_id} from the {participant_id} DSS returned error {deleted.dss_query.status_code}",
                    query_timestamps=[deleted.dss_query.query.request.timestamp],
                )

        for subscriber_url, notification in deleted.notifications.items():
            pid = (
                notification.query.participant_id
                if "participant_id" in notification.query
                else None
            )
            with scenario.check("Notified subscriber", [pid] if pid else []) as check:
                if not notification.success:
                    check.record_failed(
                        "Could not notify ISA subscriber",
                        Severity.Medium,
                        f"Attempting to notify subscriber for ISA {isa_id} at {subscriber_url} resulted in {notification.status_code}",
                        query_timestamps=[notification.query.request.timestamp],
                    )


class ISAValidator(object):
    """Wraps the validation logic for an ISA that was returned by the DSS.
    It will compare the returned ISA with the parameters specified at its creation.

    Inspired by the existing code in DSSWrapper.put_isa() – TODO consider refactoring to merge with it
    """

    _main_check: PendingCheck
    _scenario: GenericTestScenario
    _isa_params: Dict[str, any]
    _dss_id: [str]
    _rid_version: RIDVersion

    def __init__(
        self,
        main_check: PendingCheck,
        scenario: GenericTestScenario,
        isa_params: Dict[str, any],
        dss_id: str,
        rid_version: RIDVersion,
    ):
        self._main_check = main_check
        self._scenario = scenario
        self._isa_params = isa_params
        self._dss_id = [dss_id]
        self._rid_version = rid_version

    def _fail_sub_check(
        self, _sub_check: PendingCheck, _summary: str, _details: str, t_dss: datetime
    ) -> None:
        """Fails with Medium severity the sub_check and with High severity the main check."""

        _sub_check.record_failed(
            summary=_summary,
            severity=Severity.Medium,
            details=_details,
            query_timestamps=[t_dss],
        )

        self._main_check.record_failed(
            summary=f"ISA request succeeded, but the DSS response is not valid: {_summary}",
            severity=Severity.High,
            details=_details,
            query_timestamps=[t_dss],
        )

    def _validate_isa(
        self,
        expected_isa_id: str,
        dss_isa: ISA,
        t_dss: datetime,
        previous_version: Optional[
            str
        ] = None,  # If set, we control that the version changed
        expected_version: Optional[
            str
        ] = None,  # If set, we control that the version has not changed
    ) -> None:
        isa_id = expected_isa_id
        dss_id = self._dss_id
        with self._scenario.check("ISA ID matches", dss_id) as sub_check:
            if isa_id != dss_isa.id:
                self._fail_sub_check(
                    sub_check,
                    "DSS did not return correct ISA",
                    f"Expected ISA ID {dss_id} but got {dss_isa.id}",
                    t_dss,
                )

        if previous_version is not None:
            with self._scenario.check("ISA version changed", dss_id) as sub_check:
                if dss_isa.version == previous_version:
                    self._fail_sub_check(
                        sub_check,
                        "ISA version was not updated",
                        f"Got old version {previous_version} while expecting new version",
                        t_dss,
                    )

        if expected_version is not None:
            with self._scenario.check("ISA version matches", dss_id) as sub_check:
                if dss_isa.version != expected_version:
                    self._fail_sub_check(
                        sub_check,
                        "ISA version is not the previously held one, although no modification was done to the ISA",
                        f"Got old version {dss_isa.version} while expecting {expected_version}",
                        t_dss,
                    )

        with self._scenario.check("ISA version format", dss_id) as sub_check:
            if not all(c not in "\0\t\r\n#%/:?@[\]" for c in dss_isa.version):
                self._fail_sub_check(
                    sub_check,
                    f"DSS returned ISA (ID {isa_id}) with invalid version format",
                    f"DSS returned an ISA with a version that is not URL-safe: {dss_isa.version}",
                    t_dss,
                )

        with self._scenario.check("ISA start time matches", dss_id) as sub_check:
            expected_start = self._isa_params["start_time"]
            if abs((dss_isa.time_start - expected_start).total_seconds()) > MAX_SKEW:
                self._fail_sub_check(
                    sub_check,
                    f"DSS returned ISA (ID {isa_id}) with incorrect start time",
                    f"DSS should have returned an ISA with a start time of {expected_start}, but instead the ISA returned had a start time of {dss_isa.time_start}",
                    t_dss,
                )

        with self._scenario.check("ISA end time matches", dss_id) as sub_check:
            expected_end = self._isa_params["end_time"]
            if abs((dss_isa.time_end - expected_end).total_seconds()) > MAX_SKEW:
                self._fail_sub_check(
                    sub_check,
                    f"DSS returned ISA (ID {isa_id}) with incorrect end time",
                    f"DSS should have returned an ISA with an end time of {expected_end}, but instead the ISA returned had an end time of {dss_isa.time_end}",
                    t_dss,
                )

        with self._scenario.check("ISA URL matches", dss_id) as sub_check:
            expected_flights_url = self._rid_version.flights_url_of(
                self._isa_params["uss_base_url"]
            )
            actual_flights_url = dss_isa.flights_url
            if actual_flights_url != expected_flights_url:
                self._fail_sub_check(
                    sub_check,
                    f"DSS returned ISA (ID {isa_id}) with incorrect URL",
                    f"DSS should have returned an ISA with a flights URL of {expected_flights_url}, but instead the ISA returned had a flights URL of {actual_flights_url}",
                    t_dss,
                )

    def validate_fetched_isa(
        self,
        expected_isa_id: str,
        fetched_isa: FetchedISA,
        expected_version: str,
    ):
        """Validates the DSS reply to an ISA fetch request."""
        t_dss = fetched_isa.query.request.timestamp

        with self._scenario.check("ISA response format", self._dss_id) as sub_check:
            errors = schema_validation.validate(
                self._rid_version.openapi_path,
                self._rid_version.openapi_get_isa_response_path,
                fetched_isa.query.response.json,
            )
            if errors:
                details = "\n".join(f"[{e.json_path}] {e.message}" for e in errors)
                self._fail_sub_check(
                    sub_check,
                    "GET ISA response format was invalid",
                    "Found the following schema validation errors in the DSS response:\n"
                    + details,
                    t_dss,
                )

        self._validate_isa(
            expected_isa_id, fetched_isa.isa, t_dss, expected_version=expected_version
        )

    def validate_mutated_isa(
        self,
        expected_isa_id: str,
        mutated_isa: ChangedISA,
        previous_version: Optional[str] = None,
    ):
        """
        Validates the DSS reply to an ISA mutation request.
        Note that both creating or updating an ISA count as a mutation: the only difference from the
        perspective of this function is that previous_version is set in the case of a mutation and None
        in the case of a creation.
        """
        t_dss = mutated_isa.query.request.timestamp

        with self._scenario.check("ISA response format", self._dss_id) as sub_check:
            errors = schema_validation.validate(
                self._rid_version.openapi_path,
                self._rid_version.openapi_put_isa_response_path,
                mutated_isa.query.response.json,
            )
            if errors:
                details = "\n".join(f"[{e.json_path}] {e.message}" for e in errors)
                sub_check.record_failed(
                    "PUT ISA response format was invalid",
                    Severity.Medium,
                    "Found the following schema validation errors in the DSS response:\n"
                    + details,
                    query_timestamps=[t_dss],
                )

        self._validate_isa(
            expected_isa_id,
            mutated_isa.isa,
            t_dss,
            previous_version=previous_version,
            expected_version=None,
        )

    def validate_deleted_isa(
        self,
        expected_isa_id: str,
        deleted_isa: ChangedISA,
        expected_version: str,
    ):
        """Validates the DSS reply to an ISA deletion request."""
        t_dss = deleted_isa.query.request.timestamp

        with self._scenario.check("ISA response format", self._dss_id) as sub_check:
            errors = schema_validation.validate(
                self._rid_version.openapi_path,
                self._rid_version.openapi_delete_isa_response_path,
                deleted_isa.query.response.json,
            )
            if errors:
                details = "\n".join(f"[{e.json_path}] {e.message}" for e in errors)
                sub_check.record_failed(
                    "PUT ISA response format was invalid",
                    Severity.Medium,
                    "Found the following schema validation errors in the DSS response:\n"
                    + details,
                    query_timestamps=[t_dss],
                )

        self._validate_isa(
            expected_isa_id, deleted_isa.isa, t_dss, expected_version=expected_version
        )

    def validate_searched_isas(
        self,
        fetched_isas: FetchedISAs,
        expected_versions: Dict[str, str],
    ):
        """Validates the DSS reply to an ISA search request:
        based on the ISA ID's present in expected_versions, it will verify the content of the returned ISA's.
        Note that ISAs that are not part of the test are entirely ignored.
        """
        for isa_id, isa_version in expected_versions.items():
            self._validate_isa(
                isa_id,
                fetched_isas.isas[isa_id],
                fetched_isas.query.request.timestamp,
                expected_version=expected_versions[isa_id],
            )


class SubscriptionValidator(object):
    """Wraps the validation logic for a subscription that was returned by the DSS.
    It will compare the returned subscription with the parameters specified at its creation.
    """

    _main_check: PendingCheck
    _scenario: GenericTestScenario
    _sub_params: Dict[str, any]
    _dss_id: [str]
    _rid_version: RIDVersion
    _owner: str

    def __init__(
        self,
        main_check: PendingCheck,
        scenario: GenericTestScenario,
        sub_params: Dict[str, any],
        dss_id: str,
        rid_version: RIDVersion,
        owner: str,
    ):
        self._main_check = main_check
        self._scenario = scenario
        self._sub_params = sub_params
        self._dss_id = [dss_id]
        self._rid_version = rid_version
        self._owner = owner

    def _fail_sub_check(
        self, _sub_check: PendingCheck, _summary: str, _details: str, t_dss: datetime
    ) -> None:
        """Fails with Medium severity the sub_check and with High severity the main check."""

        _sub_check.record_failed(
            summary=_summary,
            severity=Severity.Medium,
            details=_details,
            query_timestamps=[t_dss],
        )

        self._main_check.record_failed(
            summary=f"Subscription request succeeded, but the DSS response is not valid: {_summary}",
            severity=Severity.High,
            details=_details,
            query_timestamps=[t_dss],
        )

    def _validate_subscription(
        self,
        expected_sub_id: str,
        sub: Subscription,
        t_dss: datetime,
        previous_version: Optional[
            str
        ] = None,  # If set, we control that the version changed
        expected_version: Optional[
            str
        ] = None,  # If set, we control that the version has not changed
    ) -> None:

        dss_id = self._dss_id
        with self._scenario.check("Subscription ID matches", dss_id) as sub_check:
            if expected_sub_id != sub.id:
                self._fail_sub_check(
                    sub_check,
                    "DSS did not return correct subscription",
                    f"Expected subscription ID {expected_sub_id} but got {sub.id}",
                    t_dss,
                )

        with self._scenario.check(
            "Subscription start time matches", dss_id
        ) as sub_check:
            expected_start = self._sub_params["start_time"]
            if abs((sub.time_start - expected_start).total_seconds()) > MAX_SKEW:
                self._fail_sub_check(
                    sub_check,
                    f"DSS returned subscription (ID {expected_sub_id}) with incorrect start time",
                    f"DSS should have returned a subscription with a start time of {expected_start}, but instead the subscription returned had a start time of {sub.time_start}",
                    t_dss,
                )

        with self._scenario.check("Subscription end time matches", dss_id) as sub_check:
            expected_end = self._sub_params["end_time"]
            if abs((sub.time_end - expected_end).total_seconds()) > MAX_SKEW:
                self._fail_sub_check(
                    sub_check,
                    f"DSS returned subscription (ID {expected_sub_id}) with incorrect end time",
                    f"DSS should have returned a subscription with an end time of {expected_end}, but instead the subscription returned had an end time of {sub.time_end}",
                    t_dss,
                )

        if previous_version is not None:
            with self._scenario.check(
                "Subscription version changed", dss_id
            ) as sub_check:
                if sub.version == previous_version:
                    self._fail_sub_check(
                        sub_check,
                        f"Subscription (ID {expected_sub_id}) version was not updated",
                        f"Got old version {previous_version} while expecting new version",
                        t_dss,
                    )

        if expected_version is not None:
            with self._scenario.check(
                "Subscription version matches", dss_id
            ) as sub_check:
                if sub.version != expected_version:
                    self._fail_sub_check(
                        sub_check,
                        f"Subscription (ID {expected_sub_id}) version is not the previously held one, although no modification was done to the subscription",
                        f"Got old version {sub.version} while expecting {expected_version}",
                        t_dss,
                    )

        with self._scenario.check(
            "Subscription flights url matches", dss_id
        ) as sub_check:
            # TODO Confirm that the base URL should contain the
            # ID in the path for v22a
            expected_isa_url = self._rid_version.post_isa_url_of(
                self._sub_params["uss_base_url"], expected_sub_id
            )
            if sub.isa_url != expected_isa_url:
                self._fail_sub_check(
                    sub_check,
                    f"DSS returned subscription (ID {expected_sub_id}) with incorrect ISA URL",
                    f"DSS should have returned a subscription with an ISA URL of {expected_isa_url}, but instead the subscription returned had an ISA URL of {sub.isa_url}",
                    t_dss,
                )

        with self._scenario.check("Subscription owner matches", dss_id) as sub_check:
            if sub.owner != self._owner:
                self._fail_sub_check(
                    sub_check,
                    f"DSS returned subscription (ID {expected_sub_id}) with incorrect owner",
                    f"DSS should have returned a subscription with an owner of {self._owner}, but instead the subscription returned had an owner of {sub.owner}",
                    t_dss,
                )

    def validate_fetched_subscription(
        self,
        expected_sub_id: str,
        sub: FetchedSubscription,
        expected_version: str,
    ):
        # Validate schema of Subscription:
        t_dss = sub.query.request.timestamp
        with self._scenario.check(
            "Subscription response format", self._dss_id
        ) as sub_check:
            errors = schema_validation.validate(
                self._rid_version.openapi_path,
                self._rid_version.openapi_get_subscription_response_path,
                sub.query.response.json,
            )
            if errors:
                details = "\n".join(f"[{e.json_path}] {e.message}" for e in errors)
                self._fail_sub_check(
                    sub_check,
                    "GET Subscription response format was invalid",
                    "Found the following schema validation errors in the DSS response:\n"
                    + details,
                    t_dss,
                )

        self._validate_subscription(
            expected_sub_id, sub.subscription, t_dss, expected_version=expected_version
        )

    def validate_mutated_subscription(
        self,
        expected_sub_id: str,
        mutated_sub: ChangedSubscription,
        previous_version: Optional[str] = None,
    ):
        # Validate schema of Subscription:
        t_dss = mutated_sub.query.request.timestamp
        with self._scenario.check(
            "Subscription response format", self._dss_id
        ) as sub_check:
            errors = schema_validation.validate(
                self._rid_version.openapi_path,
                self._rid_version.openapi_put_subscription_response_path,
                mutated_sub.query.response.json,
            )
            if errors:
                details = "\n".join(f"[{e.json_path}] {e.message}" for e in errors)
                self._fail_sub_check(
                    sub_check,
                    "Mutated Subscription response format was invalid",
                    "Found the following schema validation errors in the DSS response:\n"
                    + details,
                    t_dss,
                )

        self._validate_subscription(
            expected_sub_id,
            mutated_sub.subscription,
            t_dss,
            previous_version=previous_version,
            expected_version=None,
        )

    def validate_deleted_subscription(
        self,
        expected_sub_id: str,
        sub: ChangedSubscription,
        expected_version: str,
    ):
        # Validate schema of Subscription:
        t_dss = sub.query.request.timestamp
        with self._scenario.check(
            "Delete subscription response format", self._dss_id
        ) as sub_check:
            errors = schema_validation.validate(
                self._rid_version.openapi_path,
                self._rid_version.openapi_delete_subscription_response_path,
                sub.query.response.json,
            )
            if errors:
                details = "\n".join(f"[{e.json_path}] {e.message}" for e in errors)
                self._fail_sub_check(
                    sub_check,
                    "DELETE Subscription response format was invalid",
                    "Found the following schema validation errors in the DSS response:\n"
                    + details,
                    t_dss,
                )

        self._validate_subscription(
            expected_sub_id, sub.subscription, t_dss, expected_version=expected_version
        )

    def validate_searched_subscriptions(
        self,
        fetched_subscriptions: FetchedSubscriptions,
        current_subs: Dict[str, Subscription],
    ):
        with self._scenario.check(
            "Subscriptions response format", self._dss_id
        ) as sub_check:
            errors = schema_validation.validate(
                self._rid_version.openapi_path,
                self._rid_version.openapi_search_subscriptions_response_path,
                fetched_subscriptions.query.response.json,
            )
            if errors:
                details = "\n".join(f"[{e.json_path}] {e.message}" for e in errors)

                self._fail_sub_check(
                    sub_check,
                    "GET Subscriptions response format was invalid",
                    "Found the following schema validation errors in the DSS response:\n"
                    + details,
                    fetched_subscriptions.query.request.timestamp,
                )

        for sub_id, expected_sub in current_subs.items():
            self._validate_subscription(
                sub_id,
                fetched_subscriptions.subscriptions[sub_id],
                fetched_subscriptions.query.request.timestamp,
                expected_version=expected_sub.version,
            )
