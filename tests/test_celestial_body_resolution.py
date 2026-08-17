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
        self.assertAlmostEqual(body.get_mu_self(), 3.986004418e14)
        self.assertNotEqual(body.get_mu_self(), body.get_mu_central_body())

    def test_saturn_resolves_correctly(self):
        body = resolve_body("Saturn")
        self.assertEqual(body.name, "Saturn")
        self.assertTrue(callable(body.eph))
        self.assertGreater(body.get_mu_central_body(), 0.0)
        self.assertAlmostEqual(body.get_mu_self(), 3.7931187e16)
        self.assertNotEqual(body.get_mu_self(), body.get_mu_central_body())

    def test_titan_resolves_correctly(self):
        body = resolve_body("Titan")
        self.assertEqual(body.name, "Titan")
        self.assertTrue(callable(body.eph))
        self.assertEqual(body.get_mu_self(), 8.978138e12)
        with self.assertRaises(NotImplementedError):
            body.get_mu_central_body()

    def test_unknown_body_names_raise_clear_error(self):
        with self.assertRaisesRegex(ValueError, "Unsupported body 'Vulcan'"):
            resolve_body("Vulcan")


class TestNewlySupportedPlanets(unittest.TestCase):
    """Mercury, Venus, Mars, Jupiter, Uranus, Neptune - jpl_lp, Lambert-capable."""

    PLANETS_AND_EXPECTED_MU_SELF = (
        # Exact values exposed by the pinned PyKEP 3.0.0 jpl_lp table.
        ("Mercury", 2.2032e13),
        ("Venus", 3.24859e14),
        ("Mars", 4.2828e13),
        ("Jupiter", 1.26686534e17),
        ("Uranus", 5.793939e15),
        ("Neptune", 6.836529e15),
    )

    def test_each_planet_resolves_and_supports_lambert(self):
        for name, expected_mu_self in self.PLANETS_AND_EXPECTED_MU_SELF:
            with self.subTest(planet=name):
                body = resolve_body(name)
                self.assertEqual(body.name, name)
                self.assertTrue(callable(body.eph))
                self.assertTrue(body.supports_lambert)
                self.assertGreater(body.get_mu_central_body(), 0.0)
                self.assertGreater(body.get_mu_self(), 0.0)
                self.assertNotEqual(body.get_mu_self(), body.get_mu_central_body())
                self.assertEqual(body.get_mu_self(), expected_mu_self)

    def test_case_insensitive_resolution(self):
        for name, _ in self.PLANETS_AND_EXPECTED_MU_SELF:
            with self.subTest(planet=name):
                self.assertIs(resolve_body(name.lower()), resolve_body(name.upper()))


class TestNewlySupportedMoons(unittest.TestCase):
    """Phobos, Deimos, Io, Europa, Ganymede, Callisto - artificial orbit, no Lambert.

    Same pattern as the existing Titan body: known GM (JPL "Planetary
    Satellite Physical Parameters", see mission/constants.py), no PyKEP
    ephemeris, Lambert transfer intentionally disabled.
    """

    MOONS_AND_EXPECTED_MU_SELF = (
        ("Phobos", 7.087e5),
        ("Deimos", 9.62e4),
        ("Io", 5.95991547e12),
        ("Europa", 3.20271210e12),
        ("Ganymede", 9.88783275e12),
        ("Callisto", 7.17928340e12),
        ("Ceres", 6.26e10),
        ("Pluto", 8.70e11),
    )

    def test_each_moon_resolves_with_known_mu_and_no_lambert(self):
        for name, expected_mu_self in self.MOONS_AND_EXPECTED_MU_SELF:
            with self.subTest(moon=name):
                body = resolve_body(name)
                self.assertEqual(body.name, name)
                self.assertFalse(body.supports_lambert)
                self.assertAlmostEqual(body.get_mu_self(), expected_mu_self)
                with self.assertRaises(NotImplementedError):
                    body.get_mu_central_body()
                with self.assertRaises(NotImplementedError):
                    body.eph(0.0)


class TestTitanAndCoreBodiesRemainUnchanged(unittest.TestCase):
    """Regression guard: the bodies.py refactor must not move Earth/Saturn/Titan."""

    def test_titan_still_matches_pre_refactor_value(self):
        body = resolve_body("Titan")
        self.assertEqual(body.get_mu_self(), 8.978138e12)
        self.assertIsNone(body.pykep_body)
        self.assertFalse(body.supports_lambert)

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
