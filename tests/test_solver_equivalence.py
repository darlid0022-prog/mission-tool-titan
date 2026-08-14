import unittest
from datetime import date

from mission.leg_solver import compute_lambert_leg
from trajectory import _compute_lambert_earth_saturn_grid


class TestSolverEquivalence(unittest.TestCase):
    def test_generic_leg_solver_matches_legacy_earth_saturn_solver(self):
        launch_start = date(2026, 6, 1)
        launch_end = date(2027, 6, 1)

        legacy = _compute_lambert_earth_saturn_grid(launch_start, launch_end)
        generic = compute_lambert_leg("Earth", "Saturn", launch_start, launch_end)

        self.assertEqual(len(legacy), len(generic))

        for legacy_solution, generic_solution in zip(legacy, generic):
            self.assertAlmostEqual(
                legacy_solution["departure_mjd2000"],
                generic_solution.departure_mjd2000,
                delta=1e-6,
            )
            self.assertAlmostEqual(
                legacy_solution["arrival_mjd2000"],
                generic_solution.arrival_mjd2000,
                delta=1e-6,
            )
            self.assertAlmostEqual(
                legacy_solution["tof_years"],
                generic_solution.tof_years,
                delta=1e-9,
            )
            self.assertAlmostEqual(
                legacy_solution["dv_depart"],
                generic_solution.v_inf_depart,
                delta=1e-6,
            )
            self.assertAlmostEqual(
                legacy_solution["v_infinity_saturn"],
                generic_solution.v_inf_arrival,
                delta=1e-6,
            )


if __name__ == "__main__":
    unittest.main()
