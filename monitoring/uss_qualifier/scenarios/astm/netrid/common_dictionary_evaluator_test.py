from datetime import datetime, timedelta
from typing import List, Tuple, Optional
from dataclasses import dataclass

from implicitdict import StringBasedDateTime
from uas_standards.astm.f3411 import v22a
from uas_standards.astm.f3411.v22a.api import (
    Altitude,
    LatLngPoint,
    UAType,
)
from uas_standards.astm.f3411.v22a.constants import SpecialTrackDirection
from uas_standards.interuss.automated_testing.rid.v1 import injection
from uas_standards.interuss.automated_testing.rid.v1.observation import (
    OperatorAltitudeAltitudeType,
    RIDHeight,
)

from monitoring.monitorlib.fetch.rid import Flight
from monitoring.monitorlib.rid import RIDVersion
from monitoring.uss_qualifier.resources.netrid.evaluation import EvaluationConfiguration
from monitoring.uss_qualifier.scenarios.astm.netrid.common_dictionary_evaluator import (
    RIDCommonDictionaryEvaluator,
)
from monitoring.uss_qualifier.scenarios.interuss.unit_test import UnitTestScenario


def _assert_operator_id(value_inj: str, value_obs: str, outcome: bool):
    def step_under_test(self: UnitTestScenario):
        evaluator = RIDCommonDictionaryEvaluator(
            config=EvaluationConfiguration(),
            test_scenario=self,
            rid_version=RIDVersion.f3411_22a,
        )
        evaluator._evaluate_operator_id(value_inj, value_obs, [])

    unit_test_scenario = UnitTestScenario(step_under_test).execute_unit_test()
    assert unit_test_scenario.get_report().successful == outcome


def test_operator_id_non_ascii():
    _assert_operator_id("non_ascii©", "non_ascii©", False)


def test_operator_id_ascii():
    _assert_operator_id("ascii.1234", "ascii.1234", True)


def _assert_operator_location(
    position_inj,
    altitude_inj,
    altitude_type_inj,
    position,
    altitude,
    altitude_type,
    expected_passed_checks,
    expected_failed_checks,
):
    def step_under_test(self: UnitTestScenario):
        evaluator = RIDCommonDictionaryEvaluator(
            config=EvaluationConfiguration(),
            test_scenario=self,
            rid_version=RIDVersion.f3411_22a,
        )
        evaluator._evaluate_operator_location(
            position_inj,
            altitude_inj,
            altitude_type_inj,
            position,
            altitude,
            altitude_type,
            [],
        )

    unit_test_scenario = UnitTestScenario(step_under_test).execute_unit_test()
    assert (
        len(list(unit_test_scenario.get_report().query_passed_checks()))
        == expected_passed_checks
    )
    assert (
        len(list(unit_test_scenario.get_report().query_failed_checks()))
        == expected_failed_checks
    )


def test_operator_location():
    valid_locations: List[
        Tuple[
            Optional[LatLngPoint],
            Optional[Altitude],
            Optional[OperatorAltitudeAltitudeType],
            Optional[LatLngPoint],
            Optional[Altitude],
            Optional[OperatorAltitudeAltitudeType],
            int,
        ]
    ] = [
        (
            LatLngPoint(lat=1.0, lng=1.0),
            None,
            None,
            LatLngPoint(lat=1.0, lng=1.0),
            None,
            None,
            2,
        ),
        (
            LatLngPoint(lat=-90.0, lng=180.0),
            None,
            None,
            LatLngPoint(lat=-90.0, lng=180.0),
            None,
            None,
            2,
        ),
        (
            LatLngPoint(
                lat=46.2,
                lng=6.1,
            ),
            Altitude(value=1),
            OperatorAltitudeAltitudeType("Takeoff"),
            LatLngPoint(
                lat=46.2,
                lng=6.1,
            ),
            Altitude(value=1),
            OperatorAltitudeAltitudeType("Takeoff"),
            6,
        ),
    ]
    for valid_location in valid_locations:
        _assert_operator_location(*valid_location, 0)

    invalid_locations: List[
        Tuple[
            Optional[LatLngPoint],
            Optional[Altitude],
            Optional[OperatorAltitudeAltitudeType],
            int,
            int,
        ]
    ] = [
        (
            LatLngPoint(lat=-90.001, lng=0),  # out of range and valid
            None,
            None,
            LatLngPoint(lat=-90.001, lng=0),  # out of range and valid
            None,
            None,
            1,
            1,
        ),
        (
            LatLngPoint(
                lat=0,  # valid
                lng=180.001,  # out of range
            ),
            None,
            None,
            LatLngPoint(
                lat=0,  # valid
                lng=180.001,  # out of range
            ),
            None,
            None,
            0,
            1,
        ),
        (
            LatLngPoint(lat=-90.001, lng=180.001),  # both out of range
            None,
            None,
            LatLngPoint(lat=-90.001, lng=180.001),  # both out of range
            None,
            None,
            0,
            2,
        ),
        (
            LatLngPoint(
                lat=46.2,
                lng=6.1,
            ),
            None,
            None,
            LatLngPoint(
                lat="46°12'7.99 N",  # Float required
                lng="6°08'44.48 E",  # Float required
            ),
            None,
            None,
            0,
            2,
        ),
        (
            LatLngPoint(
                lat=46.2,
                lng=6.1,
            ),
            Altitude(value=1),
            "invalid",  # Invalid value
            LatLngPoint(
                lat=46.2,
                lng=6.1,
            ),
            Altitude(value=1),
            "invalid",  # Invalid value
            5,
            1,
        ),
        (
            LatLngPoint(
                lat=46.2,
                lng=6.1,
            ),
            Altitude(
                value=1000.9,
                units="FT",  # Invalid value
                reference="UNKNOWN",  # Invalid value
            ),
            "Takeoff",
            LatLngPoint(
                lat=46.2,
                lng=6.1,
            ),
            Altitude(
                value=1000.9,
                units="FT",  # Invalid value
                reference="UNKNOWN",  # Invalid value
            ),
            "Takeoff",
            5,
            2,
        ),
    ]
    for invalid_location in invalid_locations:
        _assert_operator_location(*invalid_location)


def _assert_operational_status(value: str, outcome: bool):
    def step_under_test(self: UnitTestScenario):
        evaluator = RIDCommonDictionaryEvaluator(
            config=EvaluationConfiguration(),
            test_scenario=self,
            rid_version=RIDVersion.f3411_22a,
        )

        evaluator._evaluate_operational_status(value, [])

    unit_test_scenario = UnitTestScenario(step_under_test).execute_unit_test()
    assert unit_test_scenario.get_report().successful == outcome


def test_operational_status():
    _assert_operational_status("Undeclared", True)  # v19 and v22a
    _assert_operational_status("Emergency", True)  # v22a only
    _assert_operational_status("Invalid", False)  # Invalid


def _assert_timestamp(value_inj: str, value_obs: str, outcome: bool):
    def step_under_test(self: UnitTestScenario):
        evaluator = RIDCommonDictionaryEvaluator(
            config=EvaluationConfiguration(),
            test_scenario=self,
            rid_version=RIDVersion.f3411_22a,
        )

        evaluator._evaluate_timestamp(
            StringBasedDateTime(value_inj), StringBasedDateTime(value_obs), []
        )

    unit_test_scenario = UnitTestScenario(step_under_test).execute_unit_test()
    assert unit_test_scenario.get_report().successful == outcome


def test_timestamp():
    _assert_timestamp("2023-09-13T04:43:00.1Z", "2023-09-13T04:43:00.1Z", True)  # Ok
    _assert_timestamp("2023-09-13T04:43:00Z", "2023-09-13T04:43:00Z", True)  # Ok
    _assert_timestamp(
        "2023-09-13T04:43:00.501Z", "2023-09-13T04:43:00.501Z", True
    )  # Ok
    _assert_timestamp(
        "2023-09-13T04:43:00.1+07:00", "2023-09-13T04:43:00.1+07:00", False
    )  # Wrong timezone


def _assert_speed(value_inj: float, value_obs: float, outcome: bool):
    def step_under_test(self: UnitTestScenario):
        evaluator = RIDCommonDictionaryEvaluator(
            config=EvaluationConfiguration(),
            test_scenario=self,
            rid_version=RIDVersion.f3411_22a,
        )

        evaluator._evaluate_speed(value_inj, value_obs, [])

    unit_test_scenario = UnitTestScenario(step_under_test).execute_unit_test()
    assert unit_test_scenario.get_report().successful == outcome


def test_speed():
    _assert_speed(1, 1, True)  # Ok
    _assert_speed(20.75, 20.75, True)  # Ok
    _assert_speed(400, 400, False)  # Fail, above MaxSpeed
    _assert_speed(23.3, 23.3, True)  # Ok
    _assert_speed(23.13, 23.25, True)  # Ok
    _assert_speed(23.12, 23.0, True)  # Ok
    _assert_speed(23.13, 23.0, False)  # Ok
    _assert_speed(23.13, 23.5, False)  # Ok


def _assert_track(value_inj: float, value_obs: float, outcome: bool):
    def step_under_test(self: UnitTestScenario):
        evaluator = RIDCommonDictionaryEvaluator(
            config=EvaluationConfiguration(),
            test_scenario=self,
            rid_version=RIDVersion.f3411_22a,
        )

        evaluator._evaluate_track(value_inj, value_obs, [])

    unit_test_scenario = UnitTestScenario(step_under_test).execute_unit_test()
    assert unit_test_scenario.get_report().successful == outcome


def test_track():
    _assert_track(1, 1, True)  # Ok
    _assert_track(-359, -359, True)  # Ok
    _assert_track(359.5, 0, True)  # Ok
    _assert_track(359.9, 0, True)  # Ok
    _assert_track(359.4, 0, False)  # Rounded the wrong way
    _assert_track(359.4, 359.0, True)  # Ok
    _assert_track(400, 400, False)  # Fail, above MaxTrackDirection
    _assert_track(-360, -360, False)  # Fail, below MinTrackDirection
    _assert_track(23.3, 23.3, True)  # Wrong resolution
    _assert_track(SpecialTrackDirection, SpecialTrackDirection, True)


def _assert_height(value_inj: injection.RIDHeight, value_obs: RIDHeight, outcome: bool):
    def step_under_test(self: UnitTestScenario):
        evaluator = RIDCommonDictionaryEvaluator(
            config=EvaluationConfiguration(),
            test_scenario=self,
            rid_version=RIDVersion.f3411_22a,
        )

        evaluator._evaluate_height(value_inj, value_obs, [])

    unit_test_scenario = UnitTestScenario(step_under_test).execute_unit_test()
    assert unit_test_scenario.get_report().successful == outcome


def test_height():
    _assert_height(None, None, True)  # Ok
    _assert_height(
        injection.RIDHeight(distance=10, reference="TakeoffLocation"),
        RIDHeight(distance=10, reference="TakeoffLocation"),
        True,
    )  # Ok
    _assert_height(
        injection.RIDHeight(distance=10.101, reference="TakeoffLocation"),
        RIDHeight(distance=10.101, reference="TakeoffLocation"),
        True,
    )  # Ok
    _assert_height(
        injection.RIDHeight(distance=10.101, reference="TakeoffLocation"),
        RIDHeight(distance=10.101, reference="Moon"),
        False,
    )  # Wrong reference
    _assert_height(
        injection.RIDHeight(distance=10.0, reference="TakeoffLocation"),
        RIDHeight(distance=11.1, reference="TakeoffLocation"),
        False,
    )  # Too far apart
    _assert_height(
        injection.RIDHeight(distance=10.0, reference="GroundLevel"),
        RIDHeight(distance=11.1, reference="TakeoffLocation"),
        False,
    )  # mismatching reference


def mock_flight(
    last_position_time: datetime,
    positions_count: int,
    positions_time_delta_s: int,
    position: Tuple[int, int] = (1.0, 1.0),
) -> Flight:
    v22a_flight = v22a.api.RIDFlight(
        id="flightId",
        aircraft_type=UAType.Aeroplane,
        current_state=None,  # Not required for tests at the moment
        operating_area=None,  # Not required for tests at the moment
        simulated=True,
        recent_positions=mock_positions(
            last_position_time, positions_count, positions_time_delta_s, position
        ),
    )
    return Flight(v22a_value=v22a_flight)


def mock_positions(
    last_time: datetime,
    amount: int,
    positions_time_delta_s: int,
    position: Tuple[int, int] = (1.0, 1.0),
) -> List[v22a.api.RIDRecentAircraftPosition]:
    """generate a list of positions with the last one at last_time and the next ones going back in time by 10 seconds"""
    return [
        v22a.api.RIDRecentAircraftPosition(
            time=v22a.api.Time(
                value=v22a.api.StringBasedDateTime(
                    last_time - timedelta(seconds=positions_time_delta_s * i)
                )
            ),
            position=v22a.api.RIDAircraftPosition(lat=position[0], lng=position[1]),
        )
        for i in range(amount)
    ]


def to_positions(
    coords: List[Tuple[float, float]],
    first_time: datetime,
    positions_time_delta_s: int = 1,
) -> v22a.api.RIDRecentAircraftPosition:
    """transform the collection of coordinates"""
    return [
        v22a.api.RIDRecentAircraftPosition(
            time=v22a.api.Time(
                value=v22a.api.StringBasedDateTime(
                    first_time - timedelta(seconds=positions_time_delta_s * i)
                )
            ),
            position=v22a.api.RIDAircraftPosition(lat=coords[i][0], lng=coords[i][1]),
        )
        for i in range(len(coords))
    ]


@dataclass
class GenericEvaluatorTestCase:
    test_name: str
    injected_value: str
    sp_value: str
    dp_value: str = None
    ignore_dp_test: bool = False


def _assert_generic_evaluator(testcase: GenericEvaluatorTestCase, outcome: bool):
    def value_validator(v: str) -> str:
        if v == "invalid":
            raise ValueError
        return v

    def value_comparator(v1: str, v2: str) -> bool:
        return v1 == v2

    dummy_injected_flight = {"test": testcase.injected_value}

    class DummySP:
        def __init__(self):
            self.test = testcase.sp_value

    dummy_dp = {"test": testcase.dp_value}

    def step_under_test(self: UnitTestScenario):
        evaluator = RIDCommonDictionaryEvaluator(
            config=EvaluationConfiguration(),
            test_scenario=self,
            rid_version=RIDVersion.f3411_22a,
        )

        # SP Check
        evaluator._generic_evaluator(
            injected_field_name="test",
            sp_field_name="test",
            dp_field_name="test",
            field_human_name="test",
            value_validator=value_validator,
            observed_value_validator=None,
            injection_required_field=False,
            unknown_value="default",
            value_comparator=value_comparator,
            injected_telemetry=None,
            injected_flight=dummy_injected_flight,
            sp_observed_flight=DummySP(),
            dp_observed_flight=None,
            participant=0,
            query_timestamp=datetime.now(),
        )

        if not testcase.ignore_dp_test:

            # DP Check
            evaluator._generic_evaluator(
                injected_field_name="test",
                sp_field_name="test",
                dp_field_name="test",
                field_human_name="test",
                value_validator=value_validator,
                observed_value_validator=None,
                injection_required_field=False,
                unknown_value="default",
                value_comparator=value_comparator,
                injected_telemetry=None,
                injected_flight=dummy_injected_flight,
                sp_observed_flight=None,
                dp_observed_flight=dummy_dp,
                participant=0,
                query_timestamp=datetime.now(),
            )

    unit_test_scenario = UnitTestScenario(step_under_test).execute_unit_test()

    assert unit_test_scenario.get_report().successful == outcome

    if not outcome:

        found_correct_reason = False

        for c in unit_test_scenario.get_report().cases:
            for step in c.steps:
                for failed_check in step.failed_checks:
                    if (
                        failed_check.additional_data[
                            "RIDCommonDictionaryEvaluatorCheckID"
                        ]
                        == testcase.test_name
                    ):
                        found_correct_reason = True

        assert found_correct_reason, testcase


def test_generic_evaluator():
    """Test various generic evaluator cases"""

    failling_tests = [
        GenericEvaluatorTestCase(
            test_name="C3",
            injected_value="valid",
            sp_value=None,
            ignore_dp_test=True,
        ),
        GenericEvaluatorTestCase(
            test_name="C5",
            injected_value="valid",
            sp_value="invalid",
            ignore_dp_test=True,
        ),
        GenericEvaluatorTestCase(
            test_name="C6",
            injected_value=None,
            sp_value="something-else",
            ignore_dp_test=True,
        ),
        GenericEvaluatorTestCase(
            test_name="C6",
            injected_value=None,
            sp_value=None,
            ignore_dp_test=True,
        ),
        GenericEvaluatorTestCase(
            test_name="C6",
            injected_value=None,
            sp_value="valid",
            ignore_dp_test=True,
        ),
        GenericEvaluatorTestCase(
            test_name="C6",
            injected_value=None,
            sp_value="invalid",
            ignore_dp_test=True,
        ),
        GenericEvaluatorTestCase(
            test_name="C7",
            injected_value="valid",
            sp_value="valid2",
            ignore_dp_test=True,
        ),
        GenericEvaluatorTestCase(
            test_name="C9",
            injected_value="valid",
            sp_value="valid",
            dp_value="invalid",
        ),
        GenericEvaluatorTestCase(
            test_name="C10",
            injected_value="valid",
            sp_value="valid",
            dp_value="valid2",
        ),
    ]

    success_tests = [
        GenericEvaluatorTestCase(
            test_name="C6 (But ok)",
            injected_value=None,
            sp_value="default",
            ignore_dp_test=True,
        ),
        GenericEvaluatorTestCase(
            test_name="C8",
            injected_value="valid",
            sp_value="valid",
            dp_value=None,
        ),
        GenericEvaluatorTestCase(
            test_name="C8",
            injected_value="valid2",
            sp_value="valid2",
            dp_value=None,
        ),
        GenericEvaluatorTestCase(
            test_name="General",
            injected_value="valid",
            sp_value="valid",
            dp_value="valid",
        ),
        GenericEvaluatorTestCase(
            test_name="General",
            injected_value="valid2",
            sp_value="valid2",
            dp_value="valid2",
        ),
    ]

    for test in failling_tests:
        _assert_generic_evaluator(test, False)
    for test in success_tests:
        _assert_generic_evaluator(test, True)
