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

from trajectory import compute_trajectory


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

REGRESSION_DV_DEPART_M_S = 11588.374686233732
REGRESSION_V_INF_SATURN_M_S = 8643.436621212077
REGRESSION_DV_TOTAL_M_S = 20231.81130744581
REGRESSION_BEST_LAUNCH_MJD2000 = 9648.0
REGRESSION_ARRIVAL_MJD2000 = 10926.375


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


if __name__ == "__main__":
    unittest.main()
