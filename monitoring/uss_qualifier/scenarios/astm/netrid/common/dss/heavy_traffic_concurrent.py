import asyncio
import typing
from datetime import datetime
from typing import List, Dict

import arrow
import loguru
import requests
from uas_standards.astm.f3411 import v19, v22a

from monitoring.monitorlib.fetch import (
    describe_request,
    Query,
    describe_aiohttp_response,
)
from monitoring.monitorlib.fetch.rid import (
    FetchedISA,
    FetchedSubscription,
    Subscription,
)
from monitoring.monitorlib.infrastructure import AsyncUTMTestSession
from monitoring.monitorlib.mutate import rid as mutate
from monitoring.monitorlib.mutate.rid import ChangedISA, ChangedSubscription
from monitoring.monitorlib.rid import RIDVersion
from monitoring.prober.infrastructure import register_resource_type
from monitoring.uss_qualifier.common_data_definitions import Severity
from monitoring.uss_qualifier.resources.astm.f3411.dss import DSSInstanceResource
from monitoring.uss_qualifier.resources.interuss.id_generator import IDGeneratorResource
from monitoring.uss_qualifier.resources.netrid.service_area import ServiceAreaResource
from monitoring.uss_qualifier.scenarios.astm.netrid.common.dss.utils import (
    ISAValidator,
    delete_isa_if_exists,
    SubscriptionValidator,
)
from monitoring.uss_qualifier.scenarios.astm.netrid.dss_wrapper import DSSWrapper
from monitoring.uss_qualifier.scenarios.scenario import GenericTestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext

# Semaphore is added to limit the number of simultaneous requests.
# Should we consider making these configurable through the scenario's parameters?
ISA_SEMAPHORE = asyncio.Semaphore(20)
THREAD_COUNT = 10
CREATE_ISAS_COUNT = 100

# Subscriptions are currently created for the whole ISA footprint, so we can't have more than 10
# If we want to create more we need to split the ISA footprint.
CREATE_SUBSCRIPTIONS_COUNT = 10


class HeavyTrafficConcurrent(GenericTestScenario):
    """
    Based on prober/rid/v1/test_isa_simple_heavy_traffic_concurrent.py from the legacy prober tool.

    Essentially, this scenario:

    - creates a certain amount of ISAs & subscriptions concurrently
    - creates another amount of ISAs & subscriptions concurrently: verify that
        previously created ISAs and subscriptions are mentioned in the creation responses
    - fetches them concurrently and checks their content
    - searches for them in a single query: all should be found
    - deletes half of the ISAs and subscriptions concurrently
    - deletes the other half of the ISAs and subscriptions concurrently: verify that
        previously deleted subscriptions are not mentioned in the ISA deletion response anymore
    - fetches them again concurrently: all requests should return a 404
    - searches for them again in a single query: none should be found


    """

    ISA_TYPE = register_resource_type(373, "ISA")
    SUB_TYPE = register_resource_type(374, "Subscription")

    _isa_ids: List[str]

    _sub_ids: List[str]

    _isa_params: Dict[str, any]

    _sub_params: Dict[str, any]

    _isa_versions: Dict[str, str]

    _current_subs: Dict[str, Subscription]

    _async_session: AsyncUTMTestSession

    _owner: str

    def __init__(
        self,
        dss: DSSInstanceResource,
        id_generator: IDGeneratorResource,
        isa: ServiceAreaResource,
    ):
        super().__init__()
        self._dss = (
            dss.dss_instance
        )  # TODO: delete once _delete_isa_if_exists updated to use dss_wrapper
        self._dss_wrapper = DSSWrapper(self, dss.dss_instance)

        self._isa_versions = {}
        self._current_subs = {}
        self._isa = isa.specification

        now = arrow.utcnow().datetime
        self._isa_start_time = self._isa.shifted_time_start(now)
        self._isa_end_time = self._isa.shifted_time_end(now)
        self._isa_area = [vertex.as_s2sphere() for vertex in self._isa.footprint]

        # Note that when the test scenario ends prematurely, we may end up with an unclosed session.
        self._async_session = AsyncUTMTestSession(
            self._dss.base_url, self._dss.client.auth_adapter
        )

        isa_base_id = id_generator.id_factory.make_id(HeavyTrafficConcurrent.ISA_TYPE)
        # The base ID ends in 000: we simply increment it to generate the other IDs
        self._isa_ids = [f"{isa_base_id[:-3]}{i:03d}" for i in range(CREATE_ISAS_COUNT)]

        sub_base_id = id_generator.id_factory.make_id(HeavyTrafficConcurrent.SUB_TYPE)
        self._sub_ids = [
            f"{sub_base_id[:-3]}{i:03d}" for i in range(CREATE_SUBSCRIPTIONS_COUNT)
        ]

        # Split ids into two collections
        self._first_half_isas = self._isa_ids[: len(self._isa_ids) // 2]
        self._first_half_subs = self._sub_ids[: len(self._sub_ids) // 2]

        self._second_half_isas = self._isa_ids[len(self._isa_ids) // 2 :]
        self._second_half_subs = self._sub_ids[len(self._sub_ids) // 2 :]

        # currently all params are the same:
        # we could improve the test by having unique parameters per ISA
        self._isa_params = dict(
            area_vertices=self._isa_area,
            start_time=self._isa_start_time,
            end_time=self._isa_end_time,
            uss_base_url=self._isa.base_url,
            alt_lo=self._isa.altitude_min,
            alt_hi=self._isa.altitude_max,
        )

        self._sub_params = dict(
            area_vertices=self._isa_area,
            alt_lo=self._isa.altitude_min,
            alt_hi=self._isa.altitude_max,
            start_time=self._isa_start_time,
            end_time=self._isa_end_time,
            uss_base_url=self._isa.base_url,
            rid_version=self._dss.rid_version,
        )

        # TODO read from correct resource once the relevant PR is merged
        self._owner = id_generator.subscriber

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)

        self.begin_test_case("Setup")
        self.begin_test_step("Ensure clean workspace")
        self._delete_subscriptions_if_exists()
        self._delete_isas_if_exists()
        self.end_test_step()
        self.end_test_case()

        self.begin_test_case("Concurrent requests")

        # TODO rename step to 'create entities"
        self.begin_test_step("Create ISA concurrently")
        self._create_entities_first_half_step()
        self._create_entities_second_half_step()
        self.end_test_step()

        self.begin_test_step("Get ISAs concurrently")
        self._get_isas_by_id_concurrent_step()
        self.end_test_step()

        self.begin_test_step("Get subscriptions concurrently")
        self._get_subscriptions_by_id_concurrent_step()
        self.end_test_step()

        self.begin_test_step("Search available ISAs")
        self._search_area_step()
        self.end_test_step()

        self.begin_test_step("Search subscriptions")
        self._search_subscriptions_step()
        self.end_test_step()

        self.begin_test_step("Delete ISAs concurrently")
        self._delete_isas_step()
        self.end_test_step()

        self.begin_test_step("Delete subscriptions concurrently")
        self._delete_subscriptions_step()
        self.end_test_step()

        # TODO rename step to 'delete entities"
        self.begin_test_step("Access deleted ISAs")
        self._get_deleted_entities_step()
        self.end_test_step()

        self.begin_test_step("Search deleted ISAs")
        self._search_deleted_isas_step()
        self.end_test_step()

        self.begin_test_step("Search deleted subscriptions")
        self._search_deleted_subscriptions_step()
        self.end_test_step()

        self.end_test_case()
        self.end_test_scenario()

    def _delete_isas_if_exists(self):
        """Delete test ISAs if they exist. Done sequentially."""
        for isa_id in self._isa_ids:
            delete_isa_if_exists(
                self,
                isa_id=isa_id,
                rid_version=self._dss.rid_version,
                session=self._dss.client,
                participant_id=self._dss_wrapper.participant_id,
            )

    def _ensure_no_active_subs_exist(self):
        """Ensure that we don't currently have any other active subscriptions at the DSS:
        as there is a limit on how many simultaneous subscriptions we can create,
        we want to avoid potentially reaching the limit during this scenario."""

        with self.check(
            "Search for all subscriptions in ISA area",
            [self._dss_wrapper.participant_id],
        ) as check:
            subs_in_area = self._dss_wrapper.search_subs(
                check,
                self._isa_area,
            )

        for sub_id, sub in subs_in_area.subscriptions.items():
            with self.check(
                "Subscription can be deleted", [self._dss_wrapper.participant_id]
            ) as check:
                self._dss_wrapper.del_sub(check, sub_id, sub.version)

    def _delete_subscriptions_if_exists(self):
        # Start by dropping any active sub
        self._ensure_no_active_subs_exist()
        # Check for subscriptions that will collide with our IDs and drop them
        self._ensure_test_sub_ids_do_not_exist()

    def _ensure_test_sub_ids_do_not_exist(self):
        """
        Ensures no subscription with the IDs we intend to use exist.
        Note that expired subscriptions won't appear in searches,
        which is why we need to explicitly test for their presence.
        """
        for sub_id in self._sub_ids:
            self._dss_wrapper.cleanup_sub(sub_id)

    def _get_isas_by_id_concurrent_step(self):
        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(
            asyncio.gather(*[self._get_isa(isa_id) for isa_id in self._isa_ids])
        )

        results = typing.cast(Dict[str, FetchedISA], results)

        for _, fetched_isa in results:
            self.record_query(fetched_isa.query)

        with self.check(
            "Successful Concurrent ISA query", [self._dss_wrapper.participant_id]
        ) as main_check:
            for isa_id, fetched_isa in results:
                if fetched_isa.status_code != 200:
                    main_check.record_failed(
                        f"ISA retrieval query failed for {isa_id}",
                        severity=Severity.High,
                        details=f"ISA retrieval query for {isa_id} yielded code {fetched_isa.status_code}",
                    )

            isa_validator = ISAValidator(
                main_check=main_check,
                scenario=self,
                isa_params=self._isa_params,
                dss_id=self._dss.participant_id,
                rid_version=self._dss.rid_version,
            )

            for isa_id, fetched_isa in results:
                isa_validator.validate_fetched_isa(
                    isa_id, fetched_isa, expected_version=self._isa_versions[isa_id]
                )

    def _get_subscriptions_by_id_concurrent_step(self):
        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(
            asyncio.gather(
                *[self._get_subscription(sub_id) for sub_id in self._sub_ids]
            )
        )

        results = typing.cast(Dict[str, FetchedSubscription], results)

        for _, fetched_sub in results:
            self.record_query(fetched_sub.query)

        with self.check(
            "Successful concurrent subscription queries",
            [self._dss_wrapper.participant_id],
        ) as main_check:
            for sub_id, fetched_sub in results:
                if fetched_sub.query.response.code != 200:
                    main_check.record_failed(
                        f"Subscription retrieval query failed for {sub_id}",
                        severity=Severity.High,
                        details=f"Subscription retrieval query for {sub_id} yielded code {fetched_sub.query.response.code}",
                    )

            sub_validator = SubscriptionValidator(
                main_check=main_check,
                scenario=self,
                sub_params=self._sub_params,
                dss_id=self._dss.participant_id,
                rid_version=self._dss.rid_version,
                owner=self._owner,
            )

            for sub_id, fetched_sub in results:
                sub_validator.validate_fetched_subscription(
                    sub_id,
                    fetched_sub,
                    expected_version=self._current_subs[sub_id].version,
                )

        # With the creation of the second half of the ISAs, the notification indices of the
        # already existing subscriptions are expected to be incremented by at least
        # the amount of new ISAs:
        with self.check(
            "Notification indices incremented", [self._dss.participant_id]
        ) as check:
            for sub_id, fetched_sub in results:
                # Only check the subscriptions created before the second ISAs are created
                if sub_id in self._first_half_subs:
                    expected_notif_index = self._sub_notif_indices_before_second_half[
                        sub_id
                    ] + len(self._second_half_isas)
                    # We don't check for equality, as other events may have caused the index to be increased.
                    if (
                        fetched_sub.subscription.notification_index
                        < expected_notif_index
                    ):
                        check.record_failed(
                            f"Subscription {sub_id} notification index did not increment by at least {len(self._second_half_isas)}",
                            severity=Severity.High,
                            details=f"Subscription {sub_id} notification index was {fetched_sub.subscription.notification_index} "
                            f"when we expected at least {expected_notif_index}",
                            query_timestamps=[fetched_sub.query.request.timestamp],
                        )

    def _wrap_isa_get_query(self, q: Query) -> FetchedISA:
        """Wrap things into the correct utility class"""
        if self._dss.rid_version == RIDVersion.f3411_19:
            return FetchedISA(v19_query=q)
        elif self._dss.rid_version == RIDVersion.f3411_22a:
            return FetchedISA(v22a_query=q)
        else:
            raise ValueError(f"Unsupported RID version '{self._dss.rid_version}'")

    def _wrap_isa_put_query(self, q: Query, mutation: str) -> ChangedISA:
        """Wrap things into the correct utility class"""
        if self._dss.rid_version == RIDVersion.f3411_19:
            return ChangedISA(mutation=mutation, v19_query=q)
        elif self._dss.rid_version == RIDVersion.f3411_22a:
            return ChangedISA(mutation=mutation, v22a_query=q)
        else:
            raise ValueError(f"Unsupported RID version '{self._dss.rid_version}'")

    def _wrap_get_sub_query(self, q: Query) -> FetchedSubscription:
        """Wrap things into the correct utility class"""
        if self._dss.rid_version == RIDVersion.f3411_19:
            return FetchedSubscription(v19_query=q)
        elif self._dss.rid_version == RIDVersion.f3411_22a:
            return FetchedSubscription(v22a_query=q)
        else:
            raise ValueError(f"Unsupported RID version '{self._dss.rid_version}'")

    def _wrap_sub_put_query(self, q: Query, mutation: str) -> ChangedSubscription:
        """Wrap things into the correct utility class"""
        if self._dss.rid_version == RIDVersion.f3411_19:
            return ChangedSubscription(mutation=mutation, v19_query=q)
        elif self._dss.rid_version == RIDVersion.f3411_22a:
            return ChangedSubscription(mutation=mutation, v22a_query=q)
        else:
            raise ValueError(f"Unsupported RID version '{self._dss.rid_version}'")

    async def _get_isa(self, isa_id):
        async with ISA_SEMAPHORE:
            (_, url) = mutate.build_isa_url(self._dss.rid_version, isa_id)
            dq = await self._get_and_describe(url)
            return isa_id, self._wrap_isa_get_query(dq)

    async def _get_subscription(self, sub_id):
        (_, url) = mutate.build_subscription_url(sub_id, None, self._dss.rid_version)
        dq = await self._get_and_describe(url)
        return sub_id, self._wrap_get_sub_query(dq)

    async def _delete_subscription(self, sub_id, sub_version):
        (_, url) = mutate.build_subscription_url(
            sub_id, sub_version, self._dss.rid_version
        )
        dq = await self._delete_and_describe(url, is_subscription_delete=True)
        return sub_id, self._wrap_sub_put_query(dq, "delete")

    async def _get_and_describe(self, url):
        r = requests.Request(
            "GET",
            url,
        )
        prep = self._dss.client.prepare_request(r)
        t0 = datetime.utcnow()
        req_descr = describe_request(prep, t0)
        status, headers, resp_json = await self._async_session.get_with_headers(
            url=url, scope=self._read_scope()
        )
        duration = datetime.utcnow() - t0
        return Query(
            request=req_descr,
            response=describe_aiohttp_response(status, headers, resp_json, duration),
            participant_id=self._dss.participant_id,
        )

    async def _put_and_describe(self, url, payload, is_subscription_put: bool = False):
        r = requests.Request(
            "PUT",
            url,
            json=payload,
        )
        scope = self._write_scope()
        # Although we effectively write to the DSS when creating a subscription,
        # it expects a 'read' (or DisplayProvider) scope, or might fail.
        if is_subscription_put:
            scope = self._read_scope()

        prep = self._dss.client.prepare_request(r)
        t0 = datetime.utcnow()
        req_descr = describe_request(prep, t0)
        status, headers, resp_json = await self._async_session.put_with_headers(
            url=url, json=payload, scope=scope
        )
        duration = datetime.utcnow() - t0
        return Query(
            request=req_descr,
            response=describe_aiohttp_response(status, headers, resp_json, duration),
            participant_id=self._dss.participant_id,
        )

    async def _delete_and_describe(self, url, is_subscription_delete: bool = False):
        r = requests.Request(
            "DELETE",
            url,
        )
        scope = self._write_scope()
        # Although we effectively write to the DSS when deleting a subscription,
        # it expects a 'read' (or DisplayProvider) scope, or might fail.
        if is_subscription_delete:
            scope = self._read_scope()
        prep = self._dss.client.prepare_request(r)
        t0 = datetime.utcnow()
        req_descr = describe_request(prep, t0)
        status, headers, resp_json = await self._async_session.delete_with_headers(
            url=url, scope=scope
        )
        duration = datetime.utcnow() - t0
        return Query(
            request=req_descr,
            response=describe_aiohttp_response(status, headers, resp_json, duration),
            participant_id=self._dss.participant_id,
        )

    async def _create_subscription(self, sub_id):
        # No semaphore for subscriptions as we don't create that many:
        (_, url) = mutate.build_subscription_url(sub_id, None, self._dss.rid_version)
        payload = mutate.build_subscription_payload(sub_id, **self._sub_params)
        dq = await self._put_and_describe(url, payload, is_subscription_put=True)
        return sub_id, self._wrap_sub_put_query(dq, "create")

    async def _create_isa(self, isa_id):
        async with ISA_SEMAPHORE:
            payload = mutate.build_isa_payload(
                **self._isa_params,
                rid_version=self._dss.rid_version,
            )
            (_, url) = mutate.build_isa_url(self._dss.rid_version, isa_id)
            dq = await self._put_and_describe(url, payload)
            return isa_id, self._wrap_isa_put_query(dq, "create")

    async def _delete_isa(self, isa_id, isa_version):
        async with ISA_SEMAPHORE:
            (_, url) = mutate.build_isa_url(self._dss.rid_version, isa_id, isa_version)
            dq = await self._delete_and_describe(url)
            return isa_id, self._wrap_isa_put_query(dq, "delete")

    def _write_scope(self):
        if self._dss.rid_version == RIDVersion.f3411_19:
            return v19.constants.Scope.Write
        elif self._dss.rid_version == RIDVersion.f3411_22a:
            return v22a.constants.Scope.ServiceProvider
        else:
            raise ValueError(f"Unsupported RID version '{self._dss.rid_version}'")

    def _read_scope(self):
        if self._dss.rid_version == RIDVersion.f3411_19:
            return v19.constants.Scope.Read
        elif self._dss.rid_version == RIDVersion.f3411_22a:
            return v22a.constants.Scope.DisplayProvider
        else:
            raise ValueError(f"Unsupported RID version '{self._dss.rid_version}'")

    def _create_entities_first_half_step(self):
        """Create half of the ISAs and subscriptions concurrently.
        Only check response format but not interactions between subscriptions and ISAs
        """
        first_half_isas = self._isa_ids[: len(self._isa_ids) // 2]
        first_half_subs = self._sub_ids[: len(self._sub_ids) // 2]
        (isas, subs) = asyncio.get_event_loop().run_until_complete(
            asyncio.gather(
                self._create_isas_concurrently(first_half_isas),
                self._create_subscriptions_concurrently(first_half_subs),
            )
        )
        # Record the query _after_ they ran in parallel.
        # The scenario classes should not be considered thread-safe.
        for _, created_isa in isas:
            self.record_query(created_isa.query)

        for _, created_sub in subs:
            self.record_query(created_sub.query)

        # Save the current subscription state:
        for sub_id, changed_sub in subs:
            self._current_subs[sub_id] = changed_sub.subscription

    def _create_entities_second_half_step(self):
        """Create the other half of the ISAs and subscriptions concurrently.
        Check that the responses at least mention the previously created ISAs and subscriptions
        """
        second_half_isas = self._isa_ids[len(self._isa_ids) // 2 :]
        second_half_subs = self._sub_ids[len(self._sub_ids) // 2 :]

        # Save the current notification indices
        self._sub_notif_indices_before_second_half = {
            sub_id: sub.notification_index for sub_id, sub in self._current_subs.items()
        }

        (isas, subs) = asyncio.get_event_loop().run_until_complete(
            asyncio.gather(
                self._create_isas_concurrently(second_half_isas),
                self._create_subscriptions_concurrently(second_half_subs),
            )
        )
        isas = typing.cast(Dict[str, ChangedISA], isas)
        subs = typing.cast(Dict[str, ChangedSubscription], subs)

        # Record the query _after_ they ran in parallel.
        # The scenario classes should not be considered thread-safe.
        for _, created_isa in isas:
            self.record_query(created_isa.query)

        for _, created_sub in subs:
            self.record_query(created_sub.query)

        # Check ISAs mention the subscription we created earlier
        with self.check(
            "Created ISAs mention subscriptions known to exist",
            [self._dss.participant_id],
        ) as check:
            for isa_id, new_isa in isas:
                subs_for_new_isa = new_isa.sub_ids
                for expected_sub_id in self._first_half_subs:
                    if expected_sub_id not in subs_for_new_isa:
                        check.record_failed(
                            f"ISA {isa_id} does not mention subscription {expected_sub_id}",
                            severity=Severity.High,
                            details=f"ISA {isa_id} was created after some subscriptions were successfully created "
                            f"for the same area, but does not mention them."
                            f"Expected at least subscriptions: {self._first_half_subs}, found {subs_for_new_isa}",
                            query_timestamps=[new_isa.query.request.timestamp],
                        )

        # Check subscriptions mention the ISAs we created earlier
        with self.check(
            "Created subscriptions mention ISAs known to exist",
            [self._dss.participant_id],
        ) as check:
            for sub_id, new_sub in subs:
                isas_for_new_sub = [isa.id for isa in new_sub.isas]
                for expected_isa_id in self._first_half_isas:
                    if expected_isa_id not in isas_for_new_sub:
                        check.record_failed(
                            f"Subscription {sub_id} does not mention ISA {expected_isa_id}",
                            severity=Severity.High,
                            details=f"Subscription {sub_id} was created after some ISAs were successfully created "
                            f"for the same area, but does not mention them."
                            f"Expected at least ISAs: {self._first_half_isas}, found {isas_for_new_sub}",
                            query_timestamps=[new_sub.query.request.timestamp],
                        )

    async def _create_subscriptions_concurrently(
        self, subs_to_create: List[str]
    ) -> Dict[str, ChangedSubscription]:
        results = await asyncio.gather(
            *[self._create_subscription(sub_id) for sub_id in subs_to_create]
        )
        results = typing.cast(Dict[str, ChangedSubscription], results)

        with self.check(
            "Concurrent subscriptions creation", [self._dss_wrapper.participant_id]
        ) as main_check:
            for sub_id, changed_sub in results:
                if changed_sub.query.response.code != 200:
                    loguru.logger.error(
                        f"Failed sub req: {changed_sub.query.request.json}"
                    )
                    loguru.logger.error(
                        f"Failed sub rep: {changed_sub.query.response.body}"
                    )
                    main_check.record_failed(
                        f"Subscription creation failed for {sub_id}",
                        severity=Severity.High,
                        details=f"Subscription creation for {sub_id} returned {changed_sub.query.response.code} "
                        f"Query request: {changed_sub.query.request.json} "
                        f"Query response: {changed_sub.query.response.json}",
                    )
                else:
                    self._current_subs[sub_id] = changed_sub.subscription

            isa_validator = SubscriptionValidator(
                main_check=main_check,
                scenario=self,
                sub_params=self._sub_params,
                dss_id=self._dss.participant_id,
                rid_version=self._dss.rid_version,
                owner=self._owner,
            )

            for sub_id, changed_sub in results:
                isa_validator.validate_mutated_subscription(
                    sub_id, changed_sub, previous_version=None
                )
                pass

        return results

    async def _create_isas_concurrently(
        self, isas_to_create: List[str]
    ) -> Dict[str, ChangedISA]:
        results = await asyncio.gather(
            *[self._create_isa(isa_id) for isa_id in isas_to_create]
        )

        results = typing.cast(Dict[str, ChangedISA], results)

        with self.check(
            "Concurrent ISAs creation", [self._dss_wrapper.participant_id]
        ) as main_check:
            for isa_id, changed_isa in results:
                if changed_isa.query.response.code != 200:
                    main_check.record_failed(
                        f"ISA creation failed for {isa_id}",
                        severity=Severity.High,
                        details=f"ISA creation for {isa_id} returned {changed_isa.query.response.code}",
                    )
                else:
                    self._isa_versions[isa_id] = changed_isa.isa.version

            isa_validator = ISAValidator(
                main_check=main_check,
                scenario=self,
                isa_params=self._isa_params,
                dss_id=self._dss.participant_id,
                rid_version=self._dss.rid_version,
            )

            for isa_id, changed_isa in results:
                isa_validator.validate_mutated_isa(
                    isa_id, changed_isa, previous_version=None
                )

        return results

    def _search_area_step(self):
        with self.check(
            "Successful ISAs search", [self._dss_wrapper.participant_id]
        ) as main_check:
            isas = self._dss_wrapper.search_isas(
                main_check,
                area=self._isa_area,
            )

            with self.check(
                "Correct ISAs returned by search", [self._dss_wrapper.participant_id]
            ) as sub_check:
                for isa_id in self._isa_ids:
                    if isa_id not in isas.isas.keys():
                        sub_check.record_failed(
                            f"ISAs search did not return ISA {isa_id} that was just created",
                            severity=Severity.High,
                            details=f"Search in area {self._isa_area} returned ISAs {isas.isas.keys()} and is missing some of the created ISAs",
                            query_timestamps=[isas.dss_query.query.request.timestamp],
                        )

            isa_validator = ISAValidator(
                main_check=main_check,
                scenario=self,
                isa_params=self._isa_params,
                dss_id=self._dss.participant_id,
                rid_version=self._dss.rid_version,
            )

            isa_validator.validate_searched_isas(
                isas, expected_versions=self._isa_versions
            )

    def _search_subscriptions_step(self):
        with self.check(
            "Successful subscriptions search", [self._dss_wrapper.participant_id]
        ) as main_check:
            subs = self._dss_wrapper.search_subs(
                main_check,
                area=self._isa_area,
            )

            with self.check(
                "Correct subscriptions returned by search",
                [self._dss_wrapper.participant_id],
            ) as sub_check:
                for sub_id in self._sub_ids:
                    if sub_id not in subs.subscriptions.keys():
                        sub_check.record_failed(
                            f"Subscriptions search did not return subscription {sub_id} that was previously created",
                            severity=Severity.High,
                            details=f"Search in area {self._isa_area} returned subscriptions {subs.subscriptions.keys()} and is missing some of the created subscriptions",
                            query_timestamps=[subs.dss_query.query.request.timestamp],
                        )

            sub_validator = SubscriptionValidator(
                main_check=main_check,
                scenario=self,
                sub_params=self._sub_params,
                dss_id=self._dss.participant_id,
                rid_version=self._dss.rid_version,
                owner=self._owner,
            )

            sub_validator.validate_searched_subscriptions(
                subs, current_subs=self._current_subs
            )

    def _delete_isas_step(self):

        # Before deleting the ISAS, take a snapshot of the subscriptions notification indices:

        # Save the current notification indices
        self._sub_notif_indices_before_deletion = {
            sub_id: sub.notification_index for sub_id, sub in self._current_subs.items()
        }

        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(
            asyncio.gather(
                *[
                    self._delete_isa(isa_id, self._isa_versions[isa_id])
                    for isa_id in self._isa_ids
                ]
            )
        )

        results = typing.cast(Dict[str, ChangedISA], results)

        for _, fetched_isa in results:
            self.record_query(fetched_isa.query)

        with self.check(
            "ISAs deletion query success", [self._dss_wrapper.participant_id]
        ) as main_check:
            for isa_id, deleted_isa in results:
                if deleted_isa.query.response.code != 200:
                    main_check.record_failed(
                        f"ISA deletion failed for {isa_id}",
                        severity=Severity.High,
                        details=f"ISA deletion for {isa_id} returned {deleted_isa.query.response.code}",
                    )

            isa_validator = ISAValidator(
                main_check=main_check,
                scenario=self,
                isa_params=self._isa_params,
                dss_id=self._dss.participant_id,
                rid_version=self._dss.rid_version,
            )

            for isa_id, changed_isa in results:
                isa_validator.validate_deleted_isa(
                    isa_id, changed_isa, expected_version=self._isa_versions[isa_id]
                )

    def _delete_subscriptions_step(self):
        """
        Delete all the subscriptions, concurrently, then check their respective notification indices.
        """
        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(
            asyncio.gather(
                *[
                    self._delete_subscription(
                        sub_id, self._current_subs[sub_id].version
                    )
                    for sub_id in self._sub_ids
                ]
            )
        )

        results = typing.cast(Dict[str, ChangedSubscription], results)

        for _, fetched_sub in results:
            self.record_query(fetched_sub.query)

        with self.check(
            "Subscriptions deletion query success", [self._dss_wrapper.participant_id]
        ) as main_check:
            for sub_id, deleted_sub in results:
                if deleted_sub.query.response.code != 200:
                    main_check.record_failed(
                        f"Subscription deletion failed for {sub_id}",
                        severity=Severity.High,
                        details=f"Subscription deletion for {sub_id} returned {deleted_sub.query.response.code}",
                    )

            sub_validator = SubscriptionValidator(
                main_check=main_check,
                scenario=self,
                sub_params=self._sub_params,
                dss_id=self._dss.participant_id,
                rid_version=self._dss.rid_version,
                owner=self._owner,
            )

            for sub_id, changed_sub in results:
                sub_validator.validate_deleted_subscription(
                    sub_id,
                    changed_sub,
                    expected_version=self._current_subs[sub_id].version,
                )

        # Check that all subscriptions' notification indices have been
        # updated after the ISA's were deleted:
        with self.check(
            "Notification indices incremented", [self._dss.participant_id]
        ) as check:
            for sub_id, fetched_sub in results:
                expected_notif_index = self._sub_notif_indices_before_deletion[
                    sub_id
                ] + len(self._isa_ids)
                # We don't check for equality, as other events may have caused the index to be increased.
                if fetched_sub.subscription.notification_index < expected_notif_index:
                    check.record_failed(
                        f"Subscription {sub_id} notification index did not increment by at least {len(self._isa_ids)}",
                        severity=Severity.High,
                        details=f"Subscription {sub_id} notification index was {fetched_sub.subscription.notification_index} "
                        f"when we expected at least {expected_notif_index}",
                        query_timestamps=[fetched_sub.query.request.timestamp],
                    )

    def _get_deleted_entities_step(self):
        """Queries the ISAs and subscriptions that were previously deleted and expects
        all queries to fail.
        """
        loop = asyncio.get_event_loop()
        (isas, subs) = loop.run_until_complete(
            asyncio.gather(self._get_deleted_isas(), self._get_deleted_subscriptions())
        )
        isas = typing.cast(Dict[str, ChangedISA], isas)
        subs = typing.cast(Dict[str, ChangedSubscription], subs)

        for _, fetched_isa in isas:
            self.record_query(fetched_isa.query)

        for _, fetched_sub in subs:
            self.record_query(fetched_sub.query)

        with self.check("ISAs not found", [self._dss_wrapper.participant_id]) as check:
            for isa_id, fetched_isa in isas:
                if fetched_isa.status_code != 404:
                    check.record_failed(
                        f"ISA retrieval succeeded for {isa_id}",
                        severity=Severity.High,
                        details=f"ISA retrieval for {isa_id} returned {fetched_isa.status_code} "
                        f"when we expected 404, as the ISA has been deleted",
                        query_timestamps=[fetched_isa.query.request.timestamp],
                    )

        with self.check(
            "Subscriptions not found", [self._dss_wrapper.participant_id]
        ) as check:
            for sub_id, fetched_sub in subs:
                if fetched_sub.query.response.code != 404:
                    check.record_failed(
                        f"Subscription retrieval succeeded for {sub_id}",
                        severity=Severity.High,
                        details=f"Subscription retrieval for {sub_id} returned {fetched_sub.query.response.code} "
                        f"when we expected 404, as the subscription has been deleted",
                        query_timestamps=[fetched_sub.query.request.timestamp],
                    )

    async def _get_deleted_isas(self):
        return await asyncio.gather(
            *[self._get_isa(isa_id) for isa_id in self._isa_ids]
        )

    async def _get_deleted_subscriptions(self):
        return await asyncio.gather(
            *[self._get_subscription(sub_id) for sub_id in self._sub_ids]
        )

    def _search_deleted_isas_step(self):
        with self.check(
            "Successful ISAs search", [self._dss_wrapper.participant_id]
        ) as check:
            isas = self._dss_wrapper.search_isas(
                check,
                area=self._isa_area,
            )

        with self.check(
            "ISAs not returned by search", [self._dss_wrapper.participant_id]
        ) as check:
            for isa_id in self._isa_ids:
                if isa_id in isas.isas.keys():
                    check.record_failed(
                        f"ISAs search returned deleted ISA {isa_id}",
                        severity=Severity.High,
                        details=f"Search in area {self._isa_area} returned ISAs {isas.isas.keys()} that contained some of the ISAs we had previously deleted.",
                        query_timestamps=[isas.dss_query.query.request.timestamp],
                    )

    def _search_deleted_subscriptions_step(self):
        with self.check(
            "Successful subscriptions search", [self._dss_wrapper.participant_id]
        ) as check:
            subs = self._dss_wrapper.search_subs(
                check,
                area=self._isa_area,
            )

        with self.check(
            "Subscriptions not returned by search", [self._dss_wrapper.participant_id]
        ) as check:
            for sub_id in self._sub_ids:
                if sub_id in subs.subscriptions.keys():
                    check.record_failed(
                        f"Subscriptions search returned deleted subscription {sub_id}",
                        severity=Severity.High,
                        details=f"Search in area {self._isa_area} returned subscriptions {subs.subscriptions.keys()} that contained some of the subscriptions we had previously deleted.",
                        query_timestamps=[subs.dss_query.query.request.timestamp],
                    )

    def cleanup(self):
        self.begin_cleanup()

        self._delete_subscriptions_if_exists()
        self._delete_isas_if_exists()
        self._async_session.close()

        self.end_cleanup()
