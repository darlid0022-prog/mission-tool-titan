import unittest
from datetime import date

from mission.bodies import resolve_body
from mission.leg_solver import compute_lambert_leg
from trajectory import _compute_lambert_earth_saturn_grid


class TestCelestialBodyResolution(unittest.TestCase):
    def test_earth_resolves_correctly(self):
        body = resolve_body("Earth")
        self.assertEqual(body.name, "Earth")
        self.assertTrue(callable(body.eph))
        self.assertGreater(body.get_mu_central_body(), 0.0)

    def test_saturn_resolves_correctly(self):
        body = resolve_body("Saturn")
        self.assertEqual(body.name, "Saturn")
        self.assertTrue(callable(body.eph))
        self.assertGreater(body.get_mu_central_body(), 0.0)

    def test_titan_resolves_correctly(self):
        body = resolve_body("Titan")
        self.assertEqual(body.name, "Titan")
        self.assertTrue(callable(body.eph))
        self.assertGreater(body.get_mu_central_body(), 0.0)

    def test_unknown_body_names_raise_clear_error(self):
        with self.assertRaisesRegex(ValueError, "Unsupported body.*Earth, Saturn, Titan"):
            resolve_body("Mars")

    def test_existing_earth_saturn_generic_solver_results_remain_unchanged(self):
        start = date(2026, 6, 1)
        end = date(2027, 6, 1)

        expected = _compute_lambert_earth_saturn_grid(start, end)
        actual = compute_lambert_leg("Earth", "Saturn", start, end)

        self.assertEqual(len(expected), len(actual))
        for exp, act in zip(expected, actual):
            self.assertAlmostEqual(exp["departure_mjd2000"], act.departure_mjd2000, delta=1e-6)
            self.assertAlmostEqual(exp["arrival_mjd2000"], act.arrival_mjd2000, delta=1e-6)
            self.assertAlmostEqual(exp["tof_years"], act.tof_years, delta=1e-9)
            self.assertAlmostEqual(exp["dv_depart"], act.v_inf_depart, delta=1e-6)
            self.assertAlmostEqual(exp["v_infinity_saturn"], act.v_inf_arrival, delta=1e-6)


if __name__ == "__main__":
    unittest.main()
