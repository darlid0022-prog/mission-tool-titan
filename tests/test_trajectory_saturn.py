"""
Regression tests for the Earth-to-Saturn Lambert engine in trajectory.py.

These tests lock the current implementation behaviour without modifying
production code.  Baseline numeric values were captured by running
compute_trajectory() with the fixed inputs below (not from theory).
"""

import unittest
from datetime import date

try:
    import pykep as pk

    PYKEP_AVAILABLE = True
except ImportError:
    PYKEP_AVAILABLE = False

from trajectory import (
    compute_trajectory,
    compute_trajectory_alternatives,
    _compute_lambert_earth_saturn_grid,
    select_best_by_departure_v_infinity,
    select_best_by_arrival_v_infinity,
    select_best_by_shortest_mission_duration,
    select_pareto_frontier,
)


# ---------------------------------------------------------------------------
# Fixed, deterministic inputs for the regression scenario
# ---------------------------------------------------------------------------
LAUNCH_START = date(2026, 6, 1)
LAUNCH_END = date(2027, 6, 1)

DEFAULT_KWARGS = dict(
    destination="Saturn",
    departure_type="Direct",
    launch_start=LAUNCH_START,
    launch_end=LAUNCH_END,
    has_moon_transfer=True,
    has_landing=False,
    is_flyby_only=False,
    dv_per_flyby=1000.0,
)


def _call_saturn_baseline(**overrides):
    params = {**DEFAULT_KWARGS, **overrides}
    return compute_trajectory(**params)


# ---------------------------------------------------------------------------
# API contract
# ---------------------------------------------------------------------------
EXPECTED_TOP_LEVEL_KEYS = frozenset({
    "dv_budget",
    "dv_total",
    "best_launch_date",
    "arrival_date",
    "note",
})

EXPECTED_MANEUVER_KEYS = frozenset({
    "dV from LEO",
    "dV DSM/Fly-By",
    "dV Capture at Destination",
    "dV Transfer to Moon",
    "dV Capture at Moon",
    "dV Lower to Final Orbit",
    "dV Break for landing",
    "dV Soft Landing",
})


# ---------------------------------------------------------------------------
# Regression baselines (current implementation, fixed inputs above)
# Captured on 2026-08-14 with pykep from conda-forge.
# Units follow PyKEP ephemeris / Lambert output: metres per second (m/s).
# ---------------------------------------------------------------------------
ABS_TOL_M_S = 1e-6
ABS_TOL_MJD2000 = 1e-6

REGRESSION_DV_DEPART_M_S = 10432.306468285773
REGRESSION_V_INF_SATURN_M_S = 6490.744714263188
REGRESSION_DV_TOTAL_M_S = 16923.05118254896
REGRESSION_BEST_LAUNCH_MJD2000 = 9681.181818181818
REGRESSION_ARRIVAL_MJD2000 = 12537.181818181829


@unittest.skipUnless(PYKEP_AVAILABLE, "pykep is required for trajectory tests")
class TestEarthSaturnTrajectoryRegression(unittest.TestCase):
    """Regression suite for compute_trajectory() — Earth to Saturn."""

    @classmethod
    def setUpClass(cls):
        cls.result = _call_saturn_baseline()

    def test_return_dict_has_expected_top_level_keys(self):
        self.assertEqual(set(self.result.keys()), EXPECTED_TOP_LEVEL_KEYS)

    def test_dv_budget_has_eight_maneuver_keys(self):
        self.assertEqual(set(self.result["dv_budget"].keys()), EXPECTED_MANEUVER_KEYS)
        self.assertEqual(len(self.result["dv_budget"]), 8)

    def test_dv_total_equals_sum_of_budget(self):
        budget_sum = sum(self.result["dv_budget"].values())
        self.assertAlmostEqual(
            self.result["dv_total"],
            budget_sum,
            delta=ABS_TOL_M_S,
        )

    def test_unimplemented_maneuvers_are_zero(self):
        zero_keys = EXPECTED_MANEUVER_KEYS - {
            "dV from LEO",
            "dV Capture at Destination",
        }
        for key in zero_keys:
            self.assertEqual(self.result["dv_budget"][key], 0.0, msg=key)

    def test_earth_saturn_departure_v_infinity_regression(self):
        """Lock departure v-infinity stored in 'dV from LEO'."""
        dv_depart = self.result["dv_budget"]["dV from LEO"]
        self.assertAlmostEqual(
            dv_depart,
            REGRESSION_DV_DEPART_M_S,
            delta=ABS_TOL_M_S,
        )

    def test_earth_saturn_arrival_v_infinity_regression(self):
        """Lock arrival v-infinity at Saturn (provisional capture slot)."""
        v_inf = self.result["dv_budget"]["dV Capture at Destination"]
        self.assertAlmostEqual(
            v_inf,
            REGRESSION_V_INF_SATURN_M_S,
            delta=ABS_TOL_M_S,
        )

    def test_earth_saturn_total_dv_regression(self):
        self.assertAlmostEqual(
            self.result["dv_total"],
            REGRESSION_DV_TOTAL_M_S,
            delta=ABS_TOL_M_S,
        )

    def test_best_launch_date_regression(self):
        self.assertIsInstance(self.result["best_launch_date"], pk.epoch)
        self.assertAlmostEqual(
            self.result["best_launch_date"].mjd2000,
            REGRESSION_BEST_LAUNCH_MJD2000,
            delta=ABS_TOL_MJD2000,
        )

    def test_arrival_date_regression(self):
        self.assertIsInstance(self.result["arrival_date"], pk.epoch)
        self.assertAlmostEqual(
            self.result["arrival_date"].mjd2000,
            REGRESSION_ARRIVAL_MJD2000,
            delta=ABS_TOL_MJD2000,
        )

    def test_note_indicates_saturn_lambert_engine(self):
        note = self.result["note"]
        self.assertIn("Terre -> Saturne", note)
        self.assertIn("Lambert", note)

    def test_compute_trajectory_is_deterministic(self):
        second = _call_saturn_baseline()
        self.assertAlmostEqual(
            second["dv_total"],
            self.result["dv_total"],
            delta=ABS_TOL_M_S,
        )
        self.assertAlmostEqual(
            second["dv_budget"]["dV from LEO"],
            self.result["dv_budget"]["dV from LEO"],
            delta=ABS_TOL_M_S,
        )


@unittest.skipUnless(PYKEP_AVAILABLE, "pykep is required for trajectory tests")
class TestEarthSaturnTrajectoryEdgeCases(unittest.TestCase):
    """Behaviour around the Saturn-only gate and input validation."""

    def test_non_saturn_destination_returns_zero_dv(self):
        result = _call_saturn_baseline(destination="Titan")
        self.assertEqual(result["dv_total"], 0.0)
        self.assertIsNone(result["best_launch_date"])
        self.assertIsNone(result["arrival_date"])
        self.assertEqual(set(result["dv_budget"].keys()), EXPECTED_MANEUVER_KEYS)
        self.assertIn("non encore implemente", result["note"])

    def test_destination_matching_is_case_insensitive(self):
        upper = _call_saturn_baseline(destination="Saturn")
        lower = _call_saturn_baseline(destination="saturn")
        self.assertAlmostEqual(
            upper["dv_total"],
            lower["dv_total"],
            delta=ABS_TOL_M_S,
        )

    def test_invalid_launch_window_raises_value_error(self):
        with self.assertRaises(ValueError):
            _call_saturn_baseline(
                launch_start=date(2027, 6, 1),
                launch_end=date(2026, 6, 1),
            )


@unittest.skipUnless(PYKEP_AVAILABLE, "pykep is required for trajectory tests")
class TestLambertGridComputation(unittest.TestCase):
    """Test the Lambert grid computation function."""

    @classmethod
    def setUpClass(cls):
        """Compute grid once for all tests in this class."""
        cls.solutions = _compute_lambert_earth_saturn_grid(
            LAUNCH_START,
            LAUNCH_END,
        )

    def test_grid_returns_nonempty_list(self):
        """Grid should return hundreds of solutions."""
        self.assertGreater(len(self.solutions), 500)

    def test_grid_solutions_have_required_keys(self):
        """Each solution dict must have all 5 required keys."""
        required_keys = {
            "dv_depart",
            "v_infinity_saturn",
            "departure_mjd2000",
            "arrival_mjd2000",
            "tof_years",
        }
        for solution in self.solutions:
            self.assertEqual(set(solution.keys()), required_keys)

    def test_grid_solutions_have_positive_v_infinity(self):
        """All v-infinity values must be positive."""
        for solution in self.solutions:
            self.assertGreater(solution["dv_depart"], 0.0, msg="dv_depart must be > 0")
            self.assertGreater(solution["v_infinity_saturn"], 0.0, msg="v_infinity_saturn must be > 0")

    def test_grid_solutions_have_valid_dates(self):
        """Arrival date must be after departure date."""
        for solution in self.solutions:
            self.assertLess(
                solution["departure_mjd2000"],
                solution["arrival_mjd2000"],
                msg="arrival_mjd2000 must be > departure_mjd2000",
            )

    def test_grid_contains_exactly_12_departure_dates(self):
        """The launch window is sampled at exactly 12 distinct departure dates."""
        departure_dates = sorted({solution["departure_mjd2000"] for solution in self.solutions})
        self.assertEqual(len(departure_dates), 12)

    def test_grid_time_of_flight_range_covers_about_4_to_8_years(self):
        """TOF values span roughly the configured 4.0-8.0 year mission range."""
        unique_tof = sorted({solution["tof_years"] for solution in self.solutions})
        self.assertAlmostEqual(unique_tof[0], 4.0, delta=1e-9)
        self.assertGreater(unique_tof[-1], 7.9)
        self.assertLess(unique_tof[-1], 8.0)

    def test_grid_tof_steps_are_approximately_15_days(self):
        """Consecutive unique TOF values should differ by ~15 days."""
        unique_tof = sorted({solution["tof_years"] for solution in self.solutions})
        diffs_days = [(next_tof - tof) * 365.25 for tof, next_tof in zip(unique_tof, unique_tof[1:])]
        self.assertTrue(diffs_days)
        for diff_days in diffs_days:
            self.assertAlmostEqual(diff_days, 15.0, delta=1e-6)

    def test_grid_solutions_have_positive_tof(self):
        """Time-of-flight must be positive and reasonable."""
        for solution in self.solutions:
            self.assertGreater(solution["tof_years"], 0.0, msg="tof_years must be > 0")
            self.assertLess(solution["tof_years"], 15.0, msg="tof_years should be < 15 years")

    def test_grid_computation_is_deterministic(self):
        """Same input window produces identical solution list."""
        second_run = _compute_lambert_earth_saturn_grid(
            LAUNCH_START,
            LAUNCH_END,
        )
        self.assertEqual(len(self.solutions), len(second_run))
        for sol1, sol2 in zip(self.solutions, second_run):
            self.assertAlmostEqual(sol1["dv_depart"], sol2["dv_depart"], delta=ABS_TOL_M_S)
            self.assertAlmostEqual(sol1["v_infinity_saturn"], sol2["v_infinity_saturn"], delta=ABS_TOL_M_S)
            self.assertAlmostEqual(sol1["departure_mjd2000"], sol2["departure_mjd2000"], delta=ABS_TOL_MJD2000)


@unittest.skipUnless(PYKEP_AVAILABLE, "pykep is required for trajectory tests")
class TestTrajectorySelection(unittest.TestCase):
    """Test the selection functions."""

    @classmethod
    def setUpClass(cls):
        """Compute grid once for all tests in this class."""
        cls.solutions = _compute_lambert_earth_saturn_grid(
            LAUNCH_START,
            LAUNCH_END,
        )

    def test_select_best_by_departure_minimizes_dv_depart(self):
        """Selected solution must have minimum dv_depart."""
        best = select_best_by_departure_v_infinity(self.solutions)
        min_dv = min(s["dv_depart"] for s in self.solutions)
        self.assertAlmostEqual(best["dv_depart"], min_dv, delta=ABS_TOL_M_S)

    def test_select_best_by_arrival_minimizes_v_inf_saturn(self):
        """Selected solution must have minimum v_infinity_saturn."""
        best = select_best_by_arrival_v_infinity(self.solutions)
        min_v_inf = min(s["v_infinity_saturn"] for s in self.solutions)
        self.assertAlmostEqual(best["v_infinity_saturn"], min_v_inf, delta=ABS_TOL_M_S)

    def test_select_best_by_shortest_tof_minimizes_tof(self):
        """Selected solution must have minimum tof_years."""
        best = select_best_by_shortest_mission_duration(self.solutions)
        min_tof = min(s["tof_years"] for s in self.solutions)
        self.assertAlmostEqual(best["tof_years"], min_tof, delta=1e-9)

    def test_selected_best_departure_belongs_to_solutions(self):
        """Best-by-departure must exist in original list."""
        best = select_best_by_departure_v_infinity(self.solutions)
        self.assertIn(best, self.solutions)

    def test_selected_best_arrival_belongs_to_solutions(self):
        """Best-by-arrival must exist in original list."""
        best = select_best_by_arrival_v_infinity(self.solutions)
        self.assertIn(best, self.solutions)

    def test_selected_best_tof_belongs_to_solutions(self):
        """Best-by-TOF must exist in original list."""
        best = select_best_by_shortest_mission_duration(self.solutions)
        self.assertIn(best, self.solutions)

    def test_selection_on_empty_list_raises_error(self):
        """Selecting from empty list should raise ValueError."""
        with self.assertRaises(ValueError):
            select_best_by_departure_v_infinity([])


@unittest.skipUnless(PYKEP_AVAILABLE, "pykep is required for trajectory tests")
class TestParetoFrontier(unittest.TestCase):
    """Test the Pareto frontier selection function."""

    @classmethod
    def setUpClass(cls):
        """Compute grid once for all tests in this class."""
        cls.solutions = _compute_lambert_earth_saturn_grid(
            LAUNCH_START,
            LAUNCH_END,
        )

    def test_pareto_frontier_is_nonempty(self):
        """Pareto frontier should contain at least one solution."""
        pareto = select_pareto_frontier(self.solutions)
        self.assertGreater(len(pareto), 0)

    def test_pareto_frontier_is_reasonable_size(self):
        """Pareto frontier should be much smaller than full grid."""
        pareto = select_pareto_frontier(self.solutions)
        self.assertLess(len(pareto), len(self.solutions) / 10)
        self.assertLess(len(pareto), 30)  # Typically 5-20 for 2 objectives

    def test_pareto_solutions_belong_to_original_list(self):
        """All Pareto solutions must exist in original grid."""
        pareto = select_pareto_frontier(self.solutions)
        for p in pareto:
            self.assertIn(p, self.solutions)

    def test_pareto_solutions_are_non_dominated_against_full_grid(self):
        """Each Pareto solution must not be dominated by any solution in the full grid."""
        pareto = select_pareto_frontier(
            self.solutions,
            objectives=["dv_depart", "v_infinity_saturn"],
        )
        for p in pareto:
            for other in self.solutions:
                if p is other:
                    continue
                other_better_or_equal = all(
                    other[obj] <= p[obj] for obj in ["dv_depart", "v_infinity_saturn"]
                )
                other_strictly_better = any(
                    other[obj] < p[obj] for obj in ["dv_depart", "v_infinity_saturn"]
                )
                self.assertFalse(
                    other_better_or_equal and other_strictly_better,
                    msg="Pareto solution is dominated by another solution in the full grid",
                )

    def test_pareto_frontier_empty_list_returns_empty(self):
        """Pareto frontier of empty list should return empty list."""
        pareto = select_pareto_frontier([])
        self.assertEqual(pareto, [])


@unittest.skipUnless(PYKEP_AVAILABLE, "pykep is required for trajectory tests")
class TestAlternativesAPI(unittest.TestCase):
    """Test the compute_trajectory_alternatives() API."""

    @classmethod
    def setUpClass(cls):
        cls.alternatives = compute_trajectory_alternatives(
            "Saturn",
            "Direct",
            LAUNCH_START,
            LAUNCH_END,
            True,
            False,
            False,
            1000.0,
        )

    def test_alternatives_dict_has_expected_keys(self):
        """Return dict must have all 8 expected keys."""
        expected_keys = {
            "all_solutions",
            "solution_count",
            "best_by_departure_v_inf",
            "best_by_arrival_v_inf",
            "best_by_shortest_tof",
            "pareto_frontier",
            "pareto_count",
            "note",
        }
        self.assertEqual(set(self.alternatives.keys()), expected_keys)

    def test_solution_count_matches_all_solutions(self):
        """solution_count must equal len(all_solutions)."""
        self.assertEqual(
            self.alternatives["solution_count"],
            len(self.alternatives["all_solutions"]),
        )

    def test_pareto_count_matches_pareto_frontier(self):
        """pareto_count must equal len(pareto_frontier)."""
        self.assertEqual(
            self.alternatives["pareto_count"],
            len(self.alternatives["pareto_frontier"]),
        )

    def test_best_by_departure_is_member_of_all_solutions(self):
        """best_by_departure_v_inf must exist in all_solutions."""
        best = self.alternatives["best_by_departure_v_inf"]
        self.assertIn(best, self.alternatives["all_solutions"])

    def test_best_by_arrival_is_member_of_all_solutions(self):
        """best_by_arrival_v_inf must exist in all_solutions."""
        best = self.alternatives["best_by_arrival_v_inf"]
        self.assertIn(best, self.alternatives["all_solutions"])

    def test_best_by_shortest_tof_is_member_of_all_solutions(self):
        """best_by_shortest_tof must exist in all_solutions."""
        best = self.alternatives["best_by_shortest_tof"]
        self.assertIn(best, self.alternatives["all_solutions"])

    def test_best_by_departure_really_minimizes_departure(self):
        """Verify best_by_departure has minimum dv_depart."""
        best = self.alternatives["best_by_departure_v_inf"]
        min_dv = min(s["dv_depart"] for s in self.alternatives["all_solutions"])
        self.assertAlmostEqual(best["dv_depart"], min_dv, delta=ABS_TOL_M_S)

    def test_best_by_arrival_really_minimizes_arrival(self):
        """Verify best_by_arrival has minimum v_infinity_saturn."""
        best = self.alternatives["best_by_arrival_v_inf"]
        min_v_inf = min(s["v_infinity_saturn"] for s in self.alternatives["all_solutions"])
        self.assertAlmostEqual(best["v_infinity_saturn"], min_v_inf, delta=ABS_TOL_M_S)

    def test_best_by_shortest_tof_really_minimizes_tof(self):
        """Verify best_by_shortest_tof has minimum tof_years."""
        best = self.alternatives["best_by_shortest_tof"]
        min_tof = min(s["tof_years"] for s in self.alternatives["all_solutions"])
        self.assertAlmostEqual(best["tof_years"], min_tof, delta=1e-9)

    def test_non_saturn_destination_returns_empty_alternatives(self):
        """Non-Saturn destination should return empty alternatives."""
        result = compute_trajectory_alternatives(
            "Titan",
            "Direct",
            LAUNCH_START,
            LAUNCH_END,
            True,
            False,
            False,
            1000.0,
        )
        self.assertEqual(result["solution_count"], 0)
        self.assertEqual(len(result["all_solutions"]), 0)
        self.assertIsNone(result["best_by_departure_v_inf"])


@unittest.skipUnless(PYKEP_AVAILABLE, "pykep is required for trajectory tests")
class TestBackwardCompatibility(unittest.TestCase):
    """Verify compute_trajectory() remains backward compatible."""

    def test_compute_trajectory_best_by_departure_matches_alternatives(self):
        """The best solution from compute_trajectory() should match
        best_by_departure_v_inf from compute_trajectory_alternatives()."""
        old = compute_trajectory(
            "Saturn",
            "Direct",
            LAUNCH_START,
            LAUNCH_END,
            True,
            False,
            False,
            1000.0,
        )
        new = compute_trajectory_alternatives(
            "Saturn",
            "Direct",
            LAUNCH_START,
            LAUNCH_END,
            True,
            False,
            False,
            1000.0,
        )
        # Extract values from old API
        old_dv_depart = old["dv_budget"]["dV from LEO"]
        old_v_inf_saturn = old["dv_budget"]["dV Capture at Destination"]
        
        # Extract values from new API best
        new_dv_depart = new["best_by_departure_v_inf"]["dv_depart"]
        new_v_inf_saturn = new["best_by_departure_v_inf"]["v_infinity_saturn"]
        
        # They must match
        self.assertAlmostEqual(old_dv_depart, new_dv_depart, delta=ABS_TOL_M_S)
        self.assertAlmostEqual(old_v_inf_saturn, new_v_inf_saturn, delta=ABS_TOL_M_S)


if __name__ == "__main__":
    unittest.main()
