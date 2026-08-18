import unittest
from datetime import date, datetime, timezone

import pandas as pd

import app_services
from launch_window_service import (
    LAUNCH_WINDOW_OBJECTIVE_MIN_DELTA_V,
    LAUNCH_WINDOW_OBJECTIVES,
    LAUNCH_WINDOW_RESOLUTION_FAST,
    LAUNCH_WINDOW_RESOLUTIONS,
    LaunchWindowCandidate,
    LaunchWindowSearchRequest,
    LaunchWindowSearchResult,
    apply_candidate_to_mission_setup,
    get_launch_window_service,
)


def _valid_request_kwargs() -> dict:
    return dict(
        search_window_start=date(2026, 6, 1),
        search_window_end=date(2027, 6, 1),
        min_time_of_flight_days=2_000.0,
        max_time_of_flight_days=3_500.0,
        objective=LAUNCH_WINDOW_OBJECTIVE_MIN_DELTA_V,
        resolution=LAUNCH_WINDOW_RESOLUTION_FAST,
        max_results=10,
    )


def _valid_candidate_kwargs(rank: int = 1) -> dict:
    return dict(
        rank=rank,
        departure_datetime=datetime(2026, 7, 1, 12, 0, tzinfo=timezone.utc),
        saturn_arrival_datetime=datetime(2033, 9, 1, 6, 0, tzinfo=timezone.utc),
        scenario_end_datetime=datetime(2033, 9, 20, 0, 0, tzinfo=timezone.utc),
        time_of_flight_days=2_618.75,
        c3_km2_s2=98.4,
        v_infinity_earth_m_s=10_432.3,
        v_infinity_saturn_m_s=6_490.7,
        delta_v_departure_m_s=3_620.1,
        delta_v_capture_m_s=2_280.8,
        delta_v_titan_circularization_m_s=862.7,
        delta_v_total_m_s=6_763.6,
    )


class TestLaunchWindowSearchRequestValidation(unittest.TestCase):
    def test_accepts_a_valid_request(self):
        request = LaunchWindowSearchRequest(**_valid_request_kwargs())
        self.assertEqual(request.objective, LAUNCH_WINDOW_OBJECTIVE_MIN_DELTA_V)

    def test_rejects_an_end_date_not_after_the_start_date(self):
        kwargs = _valid_request_kwargs()
        kwargs["search_window_end"] = kwargs["search_window_start"]
        with self.assertRaisesRegex(ValueError, "search_window_end"):
            LaunchWindowSearchRequest(**kwargs)

    def test_rejects_a_non_positive_minimum_time_of_flight(self):
        kwargs = _valid_request_kwargs()
        kwargs["min_time_of_flight_days"] = 0.0
        with self.assertRaisesRegex(ValueError, "min_time_of_flight_days"):
            LaunchWindowSearchRequest(**kwargs)

    def test_rejects_a_maximum_time_of_flight_below_the_minimum(self):
        kwargs = _valid_request_kwargs()
        kwargs["min_time_of_flight_days"] = 3_000.0
        kwargs["max_time_of_flight_days"] = 2_000.0
        with self.assertRaisesRegex(ValueError, "max_time_of_flight_days"):
            LaunchWindowSearchRequest(**kwargs)

    def test_rejects_an_unknown_objective(self):
        kwargs = _valid_request_kwargs()
        kwargs["objective"] = "fastest_ever"
        with self.assertRaisesRegex(ValueError, "objective"):
            LaunchWindowSearchRequest(**kwargs)

    def test_rejects_an_unknown_resolution(self):
        kwargs = _valid_request_kwargs()
        kwargs["resolution"] = "ultra"
        with self.assertRaisesRegex(ValueError, "resolution"):
            LaunchWindowSearchRequest(**kwargs)

    def test_rejects_a_non_positive_max_results(self):
        kwargs = _valid_request_kwargs()
        kwargs["max_results"] = 0
        with self.assertRaisesRegex(ValueError, "max_results"):
            LaunchWindowSearchRequest(**kwargs)

    def test_rejects_max_results_above_the_hard_cap(self):
        kwargs = _valid_request_kwargs()
        kwargs["max_results"] = 10_000
        with self.assertRaisesRegex(ValueError, "max_results"):
            LaunchWindowSearchRequest(**kwargs)

    def test_every_objective_and_resolution_constant_is_independently_valid(self):
        for objective in LAUNCH_WINDOW_OBJECTIVES:
            for resolution in LAUNCH_WINDOW_RESOLUTIONS:
                with self.subTest(objective=objective, resolution=resolution):
                    kwargs = _valid_request_kwargs()
                    kwargs["objective"] = objective
                    kwargs["resolution"] = resolution
                    LaunchWindowSearchRequest(**kwargs)  # must not raise


class TestLaunchWindowCandidateValidation(unittest.TestCase):
    def test_accepts_a_valid_candidate(self):
        candidate = LaunchWindowCandidate(**_valid_candidate_kwargs())
        self.assertEqual(candidate.rank, 1)
        self.assertAlmostEqual(candidate.time_of_flight_years, 2_618.75 / 365.25)

    def test_rejects_a_non_positive_rank(self):
        kwargs = _valid_candidate_kwargs()
        kwargs["rank"] = 0
        with self.assertRaisesRegex(ValueError, "rank"):
            LaunchWindowCandidate(**kwargs)

    def test_rejects_arrival_not_after_departure(self):
        kwargs = _valid_candidate_kwargs()
        kwargs["saturn_arrival_datetime"] = kwargs["departure_datetime"]
        with self.assertRaisesRegex(ValueError, "saturn_arrival_datetime"):
            LaunchWindowCandidate(**kwargs)

    def test_rejects_a_scenario_end_before_saturn_arrival(self):
        kwargs = _valid_candidate_kwargs()
        kwargs["scenario_end_datetime"] = kwargs["saturn_arrival_datetime"].replace(year=2020)
        with self.assertRaisesRegex(ValueError, "scenario_end_datetime"):
            LaunchWindowCandidate(**kwargs)

    def test_rejects_a_negative_delta_v_field(self):
        kwargs = _valid_candidate_kwargs()
        kwargs["delta_v_total_m_s"] = -1.0
        with self.assertRaisesRegex(ValueError, "delta_v_total_m_s"):
            LaunchWindowCandidate(**kwargs)

    def test_rejects_a_non_finite_c3(self):
        kwargs = _valid_candidate_kwargs()
        kwargs["c3_km2_s2"] = float("inf")
        with self.assertRaisesRegex(ValueError, "c3_km2_s2"):
            LaunchWindowCandidate(**kwargs)

    def test_total_duration_is_computed_from_dates_and_never_equals_flight_time(self):
        """Non-regression: total_duration_days (departure -> scenario end,
        including the post-arrival Saturn capture and Titan-orbital-radius
        circularization) must be a distinct, independently-computed value
        from time_of_flight_days (the Earth -> Saturn cruise only, straight
        from the engine) - never silently collapsed into the same number.
        """
        candidate = LaunchWindowCandidate(**_valid_candidate_kwargs())
        # departure 2026-07-01 12:00 -> scenario end 2033-09-20 00:00.
        self.assertAlmostEqual(candidate.total_duration_days, 2_637.5, places=6)
        self.assertNotAlmostEqual(candidate.total_duration_days, candidate.time_of_flight_days)
        self.assertGreater(candidate.total_duration_days, candidate.time_of_flight_days)
        self.assertAlmostEqual(
            candidate.total_duration_days - candidate.time_of_flight_days, 18.75, places=6
        )
        self.assertAlmostEqual(candidate.total_duration_years, 2_637.5 / 365.25)

    def test_total_duration_tracks_scenario_end_not_saturn_arrival(self):
        """total_duration_days must reflect scenario_end_datetime (post-arrival
        capture + circularization included), not stop at saturn_arrival_datetime."""
        kwargs = _valid_candidate_kwargs()
        candidate_short_scenario = LaunchWindowCandidate(
            **{**kwargs, "scenario_end_datetime": kwargs["saturn_arrival_datetime"]}
        )
        candidate_long_scenario = LaunchWindowCandidate(**kwargs)
        self.assertGreater(
            candidate_long_scenario.total_duration_days,
            candidate_short_scenario.total_duration_days,
        )


class TestLaunchWindowSearchResultValidation(unittest.TestCase):
    def test_accepts_a_valid_result_with_no_candidates(self):
        request = LaunchWindowSearchRequest(**_valid_request_kwargs())
        result = LaunchWindowSearchResult(
            request=request, candidates=(), engine_name="test-fixture-v0"
        )
        self.assertEqual(result.candidates, ())

    def test_rejects_duplicate_candidate_ranks(self):
        request = LaunchWindowSearchRequest(**_valid_request_kwargs())
        candidates = (
            LaunchWindowCandidate(**_valid_candidate_kwargs(rank=1)),
            LaunchWindowCandidate(**_valid_candidate_kwargs(rank=1)),
        )
        with self.assertRaisesRegex(ValueError, "unique ranks"):
            LaunchWindowSearchResult(
                request=request, candidates=candidates, engine_name="test-fixture-v0"
            )

    def test_rejects_more_candidates_than_max_results(self):
        kwargs = _valid_request_kwargs()
        kwargs["max_results"] = 1
        request = LaunchWindowSearchRequest(**kwargs)
        candidates = (
            LaunchWindowCandidate(**_valid_candidate_kwargs(rank=1)),
            LaunchWindowCandidate(**_valid_candidate_kwargs(rank=2)),
        )
        with self.assertRaisesRegex(ValueError, "max_results"):
            LaunchWindowSearchResult(
                request=request, candidates=candidates, engine_name="test-fixture-v0"
            )

    def test_rejects_pareto_ranks_not_present_among_candidates(self):
        request = LaunchWindowSearchRequest(**_valid_request_kwargs())
        candidates = (LaunchWindowCandidate(**_valid_candidate_kwargs(rank=1)),)
        with self.assertRaisesRegex(ValueError, "pareto_candidate_ranks"):
            LaunchWindowSearchResult(
                request=request,
                candidates=candidates,
                engine_name="test-fixture-v0",
                pareto_candidate_ranks=(99,),
            )


class TestEngineConnectedByDefault(unittest.TestCase):
    def test_get_launch_window_service_returns_the_real_adapter(self):
        service = get_launch_window_service()
        self.assertTrue(callable(service.search))


class TestApplyCandidateToMissionSetup(unittest.TestCase):
    def _mission_setup_inputs(self) -> app_services.MissionSetupInputs:
        return app_services.MissionSetupInputs(
            destination="Saturn",
            selected_moon="Titan",
            departure_type="LEO",
            leo_altitude_km=300.0,
            saturn_periapsis_radius_km=62_500.0,
            saturn_staging_radius_km=610_000.0,
            titan_capture_altitude_km=1_600.0,
            launch_window_start=date(2026, 1, 1),
            launch_window_end=date(2026, 12, 31),
            isp_s=340.0,
            instruments_df=pd.DataFrame(columns=app_services.INSTRUMENT_COLUMNS),
            trajectory_type=app_services.TRAJECTORY_TYPE_CASSINI_HISTORICAL,
        )

    def test_narrows_the_launch_window_to_the_candidates_departure_day(self):
        candidate = LaunchWindowCandidate(**_valid_candidate_kwargs())
        updated = apply_candidate_to_mission_setup(candidate, self._mission_setup_inputs())
        self.assertEqual(updated.launch_window_start, date(2026, 7, 1))
        self.assertEqual(updated.launch_window_end, date(2026, 7, 2))

    def test_forces_the_direct_trajectory_type(self):
        candidate = LaunchWindowCandidate(**_valid_candidate_kwargs())
        updated = apply_candidate_to_mission_setup(candidate, self._mission_setup_inputs())
        self.assertEqual(updated.trajectory_type, app_services.TRAJECTORY_TYPE_DIRECT)

    def test_leaves_every_other_field_unchanged(self):
        original = self._mission_setup_inputs()
        candidate = LaunchWindowCandidate(**_valid_candidate_kwargs())
        updated = apply_candidate_to_mission_setup(candidate, original)
        self.assertEqual(updated.destination, original.destination)
        self.assertEqual(updated.selected_moon, original.selected_moon)
        self.assertEqual(updated.departure_type, original.departure_type)
        self.assertEqual(updated.leo_altitude_km, original.leo_altitude_km)
        self.assertEqual(updated.saturn_periapsis_radius_km, original.saturn_periapsis_radius_km)
        self.assertEqual(updated.saturn_staging_radius_km, original.saturn_staging_radius_km)
        self.assertEqual(updated.titan_capture_altitude_km, original.titan_capture_altitude_km)
        self.assertEqual(updated.isp_s, original.isp_s)
        self.assertIs(updated.instruments_df, original.instruments_df)


if __name__ == "__main__":
    unittest.main()
