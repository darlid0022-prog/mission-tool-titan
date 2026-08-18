import math
import unittest
from dataclasses import replace
from datetime import date

import pykep as pk

from mission.constants import ASTRONOMICAL_UNIT_M, TITAN_MEAN_ORBIT_RADIUS_M
from mission.launch_search import (
    compute_pareto_front,
    evaluate_launch_scenario,
    rank_scenarios,
    search_direct_earth_saturn_titan,
)
from mission.launch_search_ephemeris import (
    clear_launch_search_caches,
    heliocentric_state,
    solve_earth_saturn_lambert,
)
from mission.launch_search_models import LaunchSearchConfig, SearchObjective


def epoch(value: str) -> float:
    return float(pk.epoch(value).mjd2000)


class TestLaunchSearchValidation(unittest.TestCase):
    def test_rejects_reversed_launch_window(self):
        with self.assertRaisesRegex(ValueError, "launch_end"):
            LaunchSearchConfig(date(2030, 1, 2), date(2030, 1, 1), 1800, 2400, 30, 60)

    def test_rejects_reversed_or_invalid_flight_time_range(self):
        with self.assertRaisesRegex(ValueError, "max_time_of_flight_days"):
            LaunchSearchConfig(date(2030, 1, 1), date(2030, 2, 1), 2400, 1800, 30, 60)
        with self.assertRaisesRegex(ValueError, "departure_step_days"):
            LaunchSearchConfig(date(2030, 1, 1), date(2030, 2, 1), 1800, 2400, 0, 60)

    def test_lambert_rejects_non_chronological_epochs(self):
        with self.assertRaisesRegex(ValueError, "arrival"):
            solve_earth_saturn_lambert(10_000.0, 10_000.0)


class TestEphemerisAndLambert(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.departure = epoch("2031-04-01")
        cls.arrival = epoch("2037-04-01")
        cls.transfer = solve_earth_saturn_lambert(cls.departure, cls.arrival, 24)

    def test_planetary_states_are_finite(self):
        for body, at_epoch in (("Earth", self.departure), ("Saturn", self.arrival)):
            position, velocity = heliocentric_state(body, at_epoch)
            self.assertTrue(all(math.isfinite(value) for value in (*position, *velocity)))

    def test_lambert_arc_matches_ephemeris_endpoints(self):
        earth_position, _ = heliocentric_state("Earth", self.departure)
        saturn_position, _ = heliocentric_state("Saturn", self.arrival)
        self.assertEqual(
            self.transfer.sample_positions_au[0],
            tuple(value / ASTRONOMICAL_UNIT_M for value in earth_position),
        )
        self.assertEqual(
            self.transfer.sample_positions_au[-1],
            tuple(value / ASTRONOMICAL_UNIT_M for value in saturn_position),
        )
        self.assertEqual(
            self.transfer.time_of_flight_s,
            (self.arrival - self.departure) * 86_400.0,
        )

    def test_cache_returns_same_immutable_transfer(self):
        clear_launch_search_caches()
        first = solve_earth_saturn_lambert(self.departure, self.arrival, 12)
        second = solve_earth_saturn_lambert(self.departure, self.arrival, 12)
        self.assertIs(first, second)
        self.assertGreaterEqual(solve_earth_saturn_lambert.cache_info().hits, 1)


class TestScenarioPhysics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scenario = evaluate_launch_scenario(epoch("2031-04-01"), epoch("2037-04-01"), sample_count=20)

    def test_c3_is_squared_earth_v_infinity(self):
        self.assertEqual(
            self.scenario.c3_m2_s2,
            self.scenario.earth_v_infinity_m_s**2,
        )

    def test_connected_budget_is_exact_manoeuvre_sum(self):
        self.assertEqual(
            self.scenario.total_delta_v_m_s,
            sum(value for _, value in self.scenario.delta_v_by_manoeuvre_m_s),
        )

    def test_budget_contains_no_flyby_or_gravity_assist_gain(self):
        labels = " ".join(name.lower() for name, _ in self.scenario.delta_v_by_manoeuvre_m_s)
        self.assertNotIn("flyby", labels)
        self.assertNotIn("gravity", labels)
        self.assertEqual(len(self.scenario.delta_v_by_manoeuvre_m_s), 3)

    def test_dates_and_durations_are_strictly_chronological(self):
        self.assertLess(self.scenario.launch_mjd2000, self.scenario.saturn_arrival_mjd2000)
        self.assertLess(
            self.scenario.saturn_arrival_mjd2000,
            self.scenario.reference_phase_end_mjd2000,
        )
        self.assertEqual(
            self.scenario.total_duration_days,
            self.scenario.reference_phase_end_mjd2000 - self.scenario.launch_mjd2000,
        )

    def test_segments_are_serializable_and_3d_compatible(self):
        self.assertEqual(len(self.scenario.segments), 2)
        for segment in self.scenario.segments:
            self.assertGreaterEqual(len(segment.x), 2)
            self.assertEqual(len(segment.x), len(segment.y))
            self.assertEqual(len(segment.x), len(segment.z))
            self.assertIn(segment.frame, {"heliocentric", "saturn_centred"})
            self.assertIn(segment.unit, {"AU", "km"})
        capture = self.scenario.segments[1]
        radii = [math.hypot(x, y) for x, y in zip(capture.x, capture.y)]
        self.assertAlmostEqual(min(radii), 150_000.0, delta=1e-6)
        self.assertAlmostEqual(max(radii), TITAN_MEAN_ORBIT_RADIUS_M / 1_000.0, delta=1e-6)
        self.assertIsInstance(self.scenario.to_dict(), dict)


class TestRankingAndSearch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base = evaluate_launch_scenario(epoch("2030-01-01"), epoch("2036-01-01"), sample_count=8)
        cls.low_delta = replace(base, scenario_id="low-delta", total_delta_v_m_s=10.0, delta_v_by_manoeuvre_m_s=(("burn", 10.0),), total_duration_days=8.0, c3_m2_s2=30.0)
        cls.fast = replace(base, scenario_id="fast", total_delta_v_m_s=20.0, delta_v_by_manoeuvre_m_s=(("burn", 20.0),), total_duration_days=4.0, c3_m2_s2=20.0)
        cls.low_c3 = replace(base, scenario_id="low-c3", total_delta_v_m_s=30.0, delta_v_by_manoeuvre_m_s=(("burn", 30.0),), total_duration_days=6.0, c3_m2_s2=10.0)
        cls.points = (cls.low_delta, cls.fast, cls.low_c3)

    def test_each_objective_orders_by_its_declared_metric(self):
        expected = {
            SearchObjective.MINIMUM_TOTAL_DELTA_V: "low-delta",
            SearchObjective.MINIMUM_DURATION: "fast",
            SearchObjective.MINIMUM_C3: "low-c3",
        }
        for objective, scenario_id in expected.items():
            with self.subTest(objective=objective):
                self.assertEqual(rank_scenarios(self.points, objective)[0].scenario_id, scenario_id)
        balanced = rank_scenarios(self.points, SearchObjective.BALANCED_DELTA_V_DURATION)
        self.assertEqual(balanced[0].scenario_id, "fast")

    def test_pareto_front_contains_only_non_dominated_points(self):
        dominated = replace(self.low_c3, scenario_id="dominated", total_delta_v_m_s=40.0, delta_v_by_manoeuvre_m_s=(("burn", 40.0),), total_duration_days=9.0)
        front = compute_pareto_front((*self.points, dominated))
        self.assertNotIn("dominated", {point.scenario_id for point in front})
        for candidate in front:
            self.assertFalse(
                any(
                    other.total_delta_v_m_s <= candidate.total_delta_v_m_s
                    and other.total_duration_days <= candidate.total_duration_days
                    and (other.total_delta_v_m_s, other.total_duration_days)
                    != (candidate.total_delta_v_m_s, candidate.total_duration_days)
                    for other in front
                )
            )

    def test_search_is_deterministic_and_keeps_requested_count(self):
        config = LaunchSearchConfig(
            date(2030, 1, 1),
            date(2030, 3, 1),
            1_900.0,
            2_500.0,
            30.0,
            150.0,
            keep_count=4,
            refinement_count=1,
            fast_mode=True,
        )
        clear_launch_search_caches()
        first = search_direct_earth_saturn_titan(config)
        second = search_direct_earth_saturn_titan(config)
        self.assertEqual(first, second)
        self.assertEqual(len(first.solutions), 4)
        self.assertTrue(all(solution.feasible for solution in first.solutions))

    def test_full_mode_refines_the_coarse_grid(self):
        config = LaunchSearchConfig(
            date(2030, 1, 1),
            date(2030, 2, 1),
            2_000.0,
            2_300.0,
            31.0,
            150.0,
            keep_count=2,
            refinement_count=1,
        )
        result = search_direct_earth_saturn_titan(config)
        coarse_count = 2 * 3
        self.assertGreater(result.evaluated_pair_count, coarse_count)


if __name__ == "__main__":
    unittest.main()
