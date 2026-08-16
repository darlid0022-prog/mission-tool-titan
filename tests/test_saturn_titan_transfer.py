import math
import unittest

from mission.constants import (
    JPL_SATURN_SYSTEM_SOURCE,
    SATURN_MU_M3_S2,
    TITAN_MEAN_ECCENTRICITY,
    TITAN_MEAN_INCLINATION_RAD,
    TITAN_MEAN_ORBIT_RADIUS_M,
    TITAN_MEAN_RADIUS_M,
    TITAN_MU_M3_S2,
    TITAN_SIDEREAL_PERIOD_S,
)
from mission.moon_transfer import (
    DEFAULT_SATURN_STAGING_RADIUS_M,
    DEFAULT_TITAN_CAPTURE_ALTITUDE_M,
    MIN_SATURN_STAGING_RADIUS_M,
    SaturnTitanTransferResult,
    compute_saturn_titan_transfer,
)
from mission.physics import delta_v_capture

ABS_TOL_M_S = 1e-3
ABS_TOL_S = 1e-3


class TestSaturnTitanConstants(unittest.TestCase):
    def test_constants_match_jpl_sat441_specification(self):
        self.assertEqual(SATURN_MU_M3_S2, 3.793120623e16)
        self.assertEqual(TITAN_MU_M3_S2, 8.97813710e12)
        self.assertEqual(TITAN_MEAN_RADIUS_M, 2.57476e6)
        self.assertEqual(TITAN_MEAN_ORBIT_RADIUS_M, 1.2219e9)
        self.assertEqual(TITAN_MEAN_ECCENTRICITY, 0.029)
        self.assertAlmostEqual(TITAN_MEAN_INCLINATION_RAD, math.radians(0.3))
        self.assertEqual(TITAN_SIDEREAL_PERIOD_S, 1_377_686.7072)
        self.assertEqual(JPL_SATURN_SYSTEM_SOURCE, "JPL SAT441")


class TestSaturnTitanTransfer(unittest.TestCase):
    def test_nominal_result_matches_specification(self):
        result = compute_saturn_titan_transfer()

        self.assertIsInstance(result, SaturnTitanTransferResult)
        self.assertEqual(result.origin, "Saturn")
        self.assertEqual(result.destination, "Titan")
        self.assertEqual(result.method, "hohmann_circular_coplanar")
        self.assertEqual(result.source, "JPL SAT441")
        self.assertAlmostEqual(
            result.saturn_staging_circular_speed_m_s, 7_951.017359, delta=ABS_TOL_M_S
        )
        self.assertAlmostEqual(result.transfer_departure_speed_m_s, 9_208.592692, delta=ABS_TOL_M_S)
        self.assertAlmostEqual(result.departure_delta_v_m_s, 1_257.575332, delta=ABS_TOL_M_S)
        self.assertAlmostEqual(result.transfer_arrival_speed_m_s, 4_521.773971, delta=ABS_TOL_M_S)
        self.assertAlmostEqual(result.titan_orbital_speed_m_s, 5_571.607245, delta=ABS_TOL_M_S)
        self.assertAlmostEqual(result.v_infinity_titan_m_s, 1_049.833274, delta=ABS_TOL_M_S)
        self.assertAlmostEqual(result.time_of_flight_s, 443_499.726268, delta=ABS_TOL_S)
        self.assertAlmostEqual(result.time_of_flight_days, 5.133099, delta=1e-6)
        self.assertAlmostEqual(result.capture_delta_v_m_s, 862.725696, delta=ABS_TOL_M_S)
        self.assertAlmostEqual(result.total_delta_v_m_s, 2_120.301028, delta=ABS_TOL_M_S)

    def test_v_infinity_is_separate_from_propulsive_delta_v(self):
        result = compute_saturn_titan_transfer()

        self.assertNotEqual(result.v_infinity_titan_m_s, result.capture_delta_v_m_s)
        self.assertAlmostEqual(
            result.total_delta_v_m_s,
            result.departure_delta_v_m_s + result.capture_delta_v_m_s,
            delta=1e-12,
        )

    def test_titan_capture_uses_generic_vis_viva_capture_primitive(self):
        result = compute_saturn_titan_transfer()

        expected = delta_v_capture(
            result.v_infinity_titan_m_s,
            TITAN_MU_M3_S2,
            result.titan_capture_radius_m,
        )
        self.assertEqual(result.capture_delta_v_m_s, expected)

    def test_higher_capture_orbit_reduces_capture_delta_v_for_nominal_case(self):
        low = compute_saturn_titan_transfer(titan_capture_altitude_m=1.0e6)
        high = compute_saturn_titan_transfer(titan_capture_altitude_m=3.0e6)

        self.assertLess(high.capture_delta_v_m_s, low.capture_delta_v_m_s)

    def test_assumptions_expose_missing_saturn_staging_phase(self):
        result = compute_saturn_titan_transfer()

        self.assertTrue(any("arrival/capture to staging" in item for item in result.exclusions))

    def test_rejects_staging_radius_at_or_below_ring_guard(self):
        for radius in (MIN_SATURN_STAGING_RADIUS_M, MIN_SATURN_STAGING_RADIUS_M - 1.0):
            with self.subTest(radius=radius):
                with self.assertRaisesRegex(ValueError, "ring guard"):
                    compute_saturn_titan_transfer(saturn_staging_radius_m=radius)

    def test_rejects_staging_radius_at_or_above_titan_orbit(self):
        for radius in (TITAN_MEAN_ORBIT_RADIUS_M, TITAN_MEAN_ORBIT_RADIUS_M + 1.0):
            with self.subTest(radius=radius):
                with self.assertRaisesRegex(ValueError, "less than Titan"):
                    compute_saturn_titan_transfer(saturn_staging_radius_m=radius)

    def test_rejects_capture_altitude_below_guard(self):
        with self.assertRaisesRegex(ValueError, "non-atmospheric guard"):
            compute_saturn_titan_transfer(titan_capture_altitude_m=999_999.0)

    def test_rejects_non_finite_inputs(self):
        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "finite"):
                    compute_saturn_titan_transfer(saturn_staging_radius_m=value)

    def test_rejects_non_numeric_inputs_and_booleans(self):
        for value in ("600000000", True, None):
            with self.subTest(value=value):
                with self.assertRaisesRegex(TypeError, "real number"):
                    compute_saturn_titan_transfer(saturn_staging_radius_m=value)

    def test_default_inputs_are_preserved_in_result(self):
        result = compute_saturn_titan_transfer()

        self.assertEqual(result.saturn_staging_radius_m, DEFAULT_SATURN_STAGING_RADIUS_M)
        self.assertEqual(result.titan_capture_altitude_m, DEFAULT_TITAN_CAPTURE_ALTITUDE_M)
        self.assertEqual(
            result.titan_capture_radius_m,
            TITAN_MEAN_RADIUS_M + DEFAULT_TITAN_CAPTURE_ALTITUDE_M,
        )


if __name__ == "__main__":
    unittest.main()
