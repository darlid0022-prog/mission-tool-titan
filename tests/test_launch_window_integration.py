import unittest
from dataclasses import replace
from datetime import date

from launch_window_engine_adapter import (
    MissionLaunchWindowSearchAdapter,
    engine_result_to_ui_result,
    request_to_engine_config,
)
from launch_window_plot import build_candidates_dataframe
from launch_window_service import (
    LAUNCH_WINDOW_OBJECTIVE_MIN_C3,
    LAUNCH_WINDOW_OBJECTIVE_MIN_DELTA_V,
    LAUNCH_WINDOW_OBJECTIVE_MIN_DURATION,
    LAUNCH_WINDOW_OBJECTIVE_TRADE_OFF,
    LAUNCH_WINDOW_RESOLUTION_DETAILED,
    LAUNCH_WINDOW_RESOLUTION_FAST,
    LaunchWindowSearchRequest,
)
from mission.launch_search import evaluate_launch_scenario
from mission.launch_search_models import (
    LaunchSearchConfig,
    LaunchSearchResult,
    SearchObjective,
    SearchTrajectorySegment,
)
from mission.trajectory_scene import segments_from_launch_search


def request(**overrides) -> LaunchWindowSearchRequest:
    values = {
        "search_window_start": date(2028, 1, 1),
        "search_window_end": date(2032, 1, 1),
        "min_time_of_flight_days": 1_600.0,
        "max_time_of_flight_days": 3_200.0,
        "objective": LAUNCH_WINDOW_OBJECTIVE_MIN_DELTA_V,
        "resolution": LAUNCH_WINDOW_RESOLUTION_FAST,
        "max_results": 5,
    }
    values.update(overrides)
    return LaunchWindowSearchRequest(**values)


class TestRequestAdapter(unittest.TestCase):
    def test_maps_all_four_objectives(self):
        expected = {
            LAUNCH_WINDOW_OBJECTIVE_MIN_DELTA_V: SearchObjective.MINIMUM_TOTAL_DELTA_V,
            LAUNCH_WINDOW_OBJECTIVE_MIN_DURATION: SearchObjective.MINIMUM_DURATION,
            LAUNCH_WINDOW_OBJECTIVE_MIN_C3: SearchObjective.MINIMUM_C3,
            LAUNCH_WINDOW_OBJECTIVE_TRADE_OFF: SearchObjective.BALANCED_DELTA_V_DURATION,
        }
        for ui_objective, engine_objective in expected.items():
            with self.subTest(objective=ui_objective):
                config = request_to_engine_config(request(objective=ui_objective))
                self.assertIs(config.objective, engine_objective)

    def test_maps_dates_flight_times_and_result_count_without_change(self):
        ui_request = request()
        config = request_to_engine_config(ui_request)
        self.assertEqual(config.launch_start, ui_request.search_window_start)
        self.assertEqual(config.launch_end, ui_request.search_window_end)
        self.assertEqual(config.min_time_of_flight_days, 1_600.0)
        self.assertEqual(config.max_time_of_flight_days, 3_200.0)
        self.assertEqual(config.keep_count, 5)

    def test_fast_and_detailed_have_explicit_distinct_grids(self):
        fast = request_to_engine_config(request(resolution=LAUNCH_WINDOW_RESOLUTION_FAST))
        detailed = request_to_engine_config(
            request(resolution=LAUNCH_WINDOW_RESOLUTION_DETAILED)
        )
        self.assertEqual(
            (fast.departure_step_days, fast.arrival_step_days, fast.fast_mode),
            (60.0, 60.0, True),
        )
        self.assertEqual(
            (
                detailed.departure_step_days,
                detailed.arrival_step_days,
                detailed.refinement_count,
                detailed.fast_mode,
            ),
            (15.0, 30.0, 3, False),
        )


class TestEngineResultAdapter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scenario = evaluate_launch_scenario(10_407.0, 12_427.0, sample_count=16)
        cls.config = request_to_engine_config(request())

    def engine_result(self, solutions=None, pareto=None):
        solutions = (self.scenario,) if solutions is None else solutions
        pareto = (self.scenario,) if pareto is None else pareto
        return LaunchSearchResult(
            config=self.config,
            solutions=solutions,
            pareto_front=pareto,
            rejected_pairs=(),
            evaluated_pair_count=len(solutions),
            ephemeris_evaluation_count=2 * len(solutions),
        )

    def test_engine_values_flow_to_candidate_and_table(self):
        result = engine_result_to_ui_result(request(), self.engine_result())
        candidate = result.candidates[0]
        manoeuvres = dict(self.scenario.delta_v_by_manoeuvre_m_s)
        self.assertEqual(candidate.departure_datetime.date(), date(2028, 6, 29))
        self.assertEqual(candidate.saturn_arrival_datetime.date(), date(2034, 1, 9))
        self.assertEqual(candidate.c3_km2_s2, self.scenario.c3_m2_s2 / 1_000_000.0)
        self.assertEqual(candidate.delta_v_total_m_s, self.scenario.total_delta_v_m_s)
        self.assertEqual(
            candidate.delta_v_total_m_s,
            sum(
                (
                    candidate.delta_v_departure_m_s,
                    candidate.delta_v_capture_m_s,
                    candidate.delta_v_titan_circularization_m_s,
                )
            ),
        )
        self.assertEqual(candidate.delta_v_departure_m_s, manoeuvres["Earth departure injection"])
        table = build_candidates_dataframe(result.candidates, selected_rank=1)
        self.assertEqual(table.iloc[0]["Delta-v total (m/s)"], self.scenario.total_delta_v_m_s)

    def test_real_pareto_membership_becomes_candidate_ranks(self):
        second = replace(self.scenario, scenario_id="second")
        engine_result = self.engine_result(
            solutions=(self.scenario, second),
            pareto=(second,),
        )
        result = engine_result_to_ui_result(
            request(max_results=2),
            engine_result,
        )
        self.assertEqual(result.pareto_candidate_ranks, (2,))

    def test_empty_engine_result_stays_empty(self):
        result = engine_result_to_ui_result(
            request(),
            self.engine_result(solutions=(), pareto=()),
        )
        self.assertEqual(result.candidates, ())
        self.assertEqual(result.pareto_candidate_ranks, ())

    def test_assumptions_and_no_flyby_gain_are_preserved(self):
        result = engine_result_to_ui_result(request(), self.engine_result())
        candidate = result.candidates[0]
        text = " ".join((*candidate.notes, *result.assumptions)).lower()
        self.assertIn("no titan phasing", text)
        self.assertNotIn("flyby gain coverage", text)
        self.assertEqual(len(self.scenario.delta_v_by_manoeuvre_m_s), 3)

    def test_scene_filter_never_mixes_frames_or_units(self):
        candidate = engine_result_to_ui_result(
            request(), self.engine_result()
        ).candidates[0]
        heliocentric = candidate.segments_for_scene(
            reference_frame="heliocentric", distance_unit="AU"
        )
        saturn = candidate.segments_for_scene(
            reference_frame="saturn_centred", distance_unit="km"
        )
        self.assertTrue(heliocentric)
        self.assertTrue(saturn)
        self.assertTrue(
            all(
                segment.frame == "heliocentric" and segment.unit == "AU"
                for segment in heliocentric
            )
        )
        self.assertTrue(
            all(
                segment.frame == "saturn_centred" and segment.unit == "km"
                for segment in saturn
            )
        )
        drawable = segments_from_launch_search(
            heliocentric,
            reference_frame="heliocentric",
            distance_unit="AU",
        )
        self.assertTrue(all(segment.metadata["distance_unit"] == "AU" for segment in drawable))

        wrong_unit = replace(heliocentric[0], unit="km")
        contaminated = replace(candidate, segments=(*candidate.segments, wrong_unit))
        with self.assertRaisesRegex(ValueError, "refusing to mix"):
            contaminated.segments_for_scene(
                reference_frame="heliocentric", distance_unit="AU"
            )

    def test_segment_contract_names_frame_and_unit_explicitly(self):
        annotations = SearchTrajectorySegment.__annotations__
        self.assertIn("frame", annotations)
        self.assertIn("unit", annotations)


class TestServiceDelegation(unittest.TestCase):
    def test_form_request_reaches_engine_as_config_and_ranking_is_retained(self):
        captured = []
        scenario = TestEngineResultAdapter.scenario

        def fake_engine(config: LaunchSearchConfig) -> LaunchSearchResult:
            captured.append(config)
            return LaunchSearchResult(config, (scenario,), (scenario,), (), 1, 2)

        service = MissionLaunchWindowSearchAdapter(fake_engine)
        result = service.search(request(objective=LAUNCH_WINDOW_OBJECTIVE_MIN_C3))
        self.assertEqual(captured[0].objective, SearchObjective.MINIMUM_C3)
        self.assertEqual(result.candidates[0].rank, 1)

    def test_engine_no_feasible_result_becomes_empty_ui_result(self):
        def empty_engine(_config):
            raise RuntimeError("No feasible direct Earth-to-Saturn Lambert solution was found.")

        result = MissionLaunchWindowSearchAdapter(empty_engine).search(request())
        self.assertEqual(result.candidates, ())


if __name__ == "__main__":
    unittest.main()
