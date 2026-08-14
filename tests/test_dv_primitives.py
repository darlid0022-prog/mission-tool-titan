import math
import importlib
import unittest

# Conventions used in these tests:
# - Units are SI: meters (m) for distance, seconds (s) for time, meters per second (m/s) for velocities.
# - Gravitational parameter `mu` is therefore in m^3 / s^2.
# The tests intentionally do not provide an implementation; they assert the
# mathematical contract that future primitives must satisfy. They will fail
# (with an explicit message) if `mission.physics` or the expected functions
# are not present.

class TestDVPrimitives(unittest.TestCase):
    def setUp(self):
        # Try to import the target module at runtime; if missing, fail with
        # an explicit message so the failure reason is the absence of the
        # primitives (as requested).
        try:
            self.physics = importlib.import_module("mission.physics")
        except ModuleNotFoundError:
            self.physics = None

    def fail_if_no_physics(self):
        if self.physics is None:
            self.fail(
                "mission.physics module not found. Physical ΔV primitives are not implemented yet."
            )

    def test_injection_vinf_zero(self):
        """A. Injection with v_inf = 0: ΔV = sqrt(2*mu/r) - sqrt(mu/r) (SI units)."""
        self.fail_if_no_physics()
        mu = 3.986004418e14  # Earth's mu in m^3/s^2 (SI)
        r = (6371e3 + 700e3)  # 700 km above Earth's surface => meters
        v_inf = 0.0

        expected = math.sqrt(2 * mu / r) - math.sqrt(mu / r)
        result = self.physics.delta_v_injection(v_inf, mu, r)

        self.assertAlmostEqual(result, expected, places=9)

    def test_injection_vinf_positive(self):
        """B. Injection with v_inf > 0: formula holds and ΔV > case v_inf=0."""
        self.fail_if_no_physics()
        mu = 3.986004418e14
        r = (6371e3 + 700e3)
        v_inf = 1000.0  # m/s

        expected = math.sqrt(v_inf * v_inf + 2 * mu / r) - math.sqrt(mu / r)
        result = self.physics.delta_v_injection(v_inf, mu, r)

        base = math.sqrt(2 * mu / r) - math.sqrt(mu / r)
        self.assertAlmostEqual(result, expected, places=9)
        self.assertGreater(result, base)

    def test_capture_vinf_zero(self):
        """C. Capture with v_inf = 0: ΔV = sqrt(2*mu/r) - sqrt(mu/r)."""
        self.fail_if_no_physics()
        mu = 3.986004418e14
        r = (6371e3 + 2000e3)  # 2000 km above Earth
        v_inf = 0.0

        expected = math.sqrt(2 * mu / r) - math.sqrt(mu / r)
        result = self.physics.delta_v_capture(v_inf, mu, r)

        self.assertAlmostEqual(result, expected, places=9)

    def test_capture_vinf_positive(self):
        """D. Capture with v_inf > 0: formula holds numerically."""
        self.fail_if_no_physics()
        mu = 3.986004418e14
        r = (6371e3 + 2000e3)
        v_inf = 500.0

        expected = math.sqrt(v_inf * v_inf + 2 * mu / r) - math.sqrt(mu / r)
        result = self.physics.delta_v_capture(v_inf, mu, r)

        self.assertAlmostEqual(result, expected, places=9)

    def test_invalid_inputs(self):
        """E. Invalid inputs should raise ValueError (mu<=0, r<=0, v_inf<0)."""
        self.fail_if_no_physics()
        mu = 3.986004418e14
        r = 7000e3

        with self.assertRaises(ValueError):
            self.physics.delta_v_injection(100.0, -1.0, r)
        with self.assertRaises(ValueError):
            self.physics.delta_v_injection(100.0, 0.0, r)
        with self.assertRaises(ValueError):
            self.physics.delta_v_injection(100.0, mu, 0.0)
        with self.assertRaises(ValueError):
            self.physics.delta_v_injection(-1.0, mu, r)

        with self.assertRaises(ValueError):
            self.physics.delta_v_capture(100.0, -1.0, r)
        with self.assertRaises(ValueError):
            self.physics.delta_v_capture(100.0, 0.0, r)
        with self.assertRaises(ValueError):
            self.physics.delta_v_capture(100.0, mu, 0.0)
        with self.assertRaises(ValueError):
            self.physics.delta_v_capture(-1.0, mu, r)

    def test_units_are_explicit(self):
        """F. Units: the API is defined in SI (m, s, m/s). This test documents that."""
        # This test does not exercise code; it documents the chosen SI convention.
        self.assertTrue(True)


if __name__ == "__main__":
    unittest.main()
