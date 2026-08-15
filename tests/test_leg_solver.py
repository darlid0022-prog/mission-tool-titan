import unittest
from datetime import date

from mission.leg_solver import compute_lambert_leg
from trajectory import _compute_lambert_earth_saturn_grid


class TestLambertLegSolver(unittest.TestCase):
    def test_earth_to_saturn_can_be_solved(self):
        results = compute_lambert_leg(
            "Earth",
            "Saturn",
            date(2026, 6, 1),
            date(2027, 6, 1),
        )
        self.assertGreater(len(results), 0)

    def test_result_contains_correct_departure_and_arrival_epochs(self):
        results = compute_lambert_leg(
            "Earth",
            "Saturn",
            date(2026, 6, 1),
            date(2027, 6, 1),
        )
        first = results[0]
        self.assertIsNotNone(first.departure_mjd2000)
        self.assertIsNotNone(first.arrival_mjd2000)
        self.assertLess(first.departure_mjd2000, first.arrival_mjd2000)

    def test_v_inf_values_are_positive(self):
        results = compute_lambert_leg(
            "Earth",
            "Saturn",
            date(2026, 6, 1),
            date(2027, 6, 1),
        )
        for result in results:
            self.assertGreater(result.v_inf_depart, 0.0)
            self.assertGreater(result.v_inf_arrival, 0.0)

    def test_matches_existing_earth_saturn_solver_within_tolerance(self):
        expected = _compute_lambert_earth_saturn_grid(
            date(2026, 6, 1),
            date(2027, 6, 1),
        )
        actual = compute_lambert_leg(
            "Earth",
            "Saturn",
            date(2026, 6, 1),
            date(2027, 6, 1),
        )

        self.assertEqual(len(expected), len(actual))

        for exp, act in zip(expected, actual):
            self.assertAlmostEqual(exp["departure_mjd2000"], act.departure_mjd2000, delta=1e-6)
            self.assertAlmostEqual(exp["arrival_mjd2000"], act.arrival_mjd2000, delta=1e-6)
            self.assertAlmostEqual(exp["tof_years"], act.tof_years, delta=1e-9)
            self.assertAlmostEqual(exp["dv_depart"], act.v_inf_depart, delta=1e-6)
            self.assertAlmostEqual(exp["v_infinity_saturn"], act.v_inf_arrival, delta=1e-6)

    def test_no_propulsive_delta_v_created(self):
        results = compute_lambert_leg(
            "Earth",
            "Saturn",
            date(2026, 6, 1),
            date(2027, 6, 1),
        )
        for result in results:
            self.assertIsNone(result.delta_v)

    def test_api_is_generic_and_not_earth_saturn_specific(self):
        self.assertTrue(hasattr(compute_lambert_leg, "__call__"))
        self.assertNotIn("earth_saturn", compute_lambert_leg.__name__.lower())
        self.assertNotIn("earth", compute_lambert_leg.__name__.lower())


if __name__ == "__main__":
    unittest.main()
