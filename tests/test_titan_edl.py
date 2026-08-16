import math
import unittest

from mission.constants import TITAN_MEAN_RADIUS_M, TITAN_MU_M3_S2
from mission.titan_edl import (
    DEFAULT_BALLISTIC_COEFFICIENT_KG_M2,
    DEFAULT_DENSITY_SCALE_HEIGHT_M,
    DEFAULT_ENTRY_FLIGHT_PATH_ANGLE_DEG,
    DEFAULT_ENTRY_INTERFACE_ALTITUDE_M,
    DEFAULT_PARACHUTE_DEPLOYMENT_SPEED_M_S,
    DEFAULT_SURFACE_DENSITY_KG_M3,
    TitanEdlResult,
    ballistic_speed_at_altitude,
    compute_titan_edl,
    estimate_ballistic_deployment_altitude,
)

NOMINAL_V_INFINITY_M_S = 1_049.833274
REFERENCE_CAPTURE_DV_M_S = 862.725696


class TestTitanEdl(unittest.TestCase):
    def test_nominal_direct_entry_result(self):
        result = compute_titan_edl(NOMINAL_V_INFINITY_M_S, REFERENCE_CAPTURE_DV_M_S)

        self.assertIsInstance(result, TitanEdlResult)
        self.assertEqual(result.method, "ballistic_direct_entry_exponential_atmosphere")
        self.assertAlmostEqual(result.entry_velocity_m_s, 2_402.597286, delta=1e-6)
        self.assertAlmostEqual(
            result.estimated_parachute_deployment_altitude_m,
            151_240.722049,
            delta=1e-6,
        )
        self.assertAlmostEqual(result.atmospheric_velocity_reduction_m_s, 2_002.597286, delta=1e-6)
        self.assertEqual(result.propulsive_equivalent_savings_m_s, REFERENCE_CAPTURE_DV_M_S)

    def test_entry_velocity_uses_hyperbolic_energy_at_interface(self):
        result = compute_titan_edl(NOMINAL_V_INFINITY_M_S, REFERENCE_CAPTURE_DV_M_S)
        interface_radius = TITAN_MEAN_RADIUS_M + DEFAULT_ENTRY_INTERFACE_ALTITUDE_M
        expected = math.sqrt(NOMINAL_V_INFINITY_M_S**2 + 2.0 * TITAN_MU_M3_S2 / interface_radius)

        self.assertEqual(result.entry_velocity_m_s, expected)

    def test_huygens_parameters_reach_400_m_s_in_published_deployment_altitude_range(self):
        altitude = estimate_ballistic_deployment_altitude(6_000.0, 400.0)

        self.assertGreaterEqual(altitude, 140_000.0)
        self.assertLessEqual(altitude, 180_000.0)
        reconstructed_speed = ballistic_speed_at_altitude(6_000.0, altitude)
        self.assertAlmostEqual(reconstructed_speed, 400.0, delta=1e-9)

    def test_defaults_match_published_huygens_and_titan_parameters(self):
        self.assertEqual(DEFAULT_ENTRY_INTERFACE_ALTITUDE_M, 1_270_000.0)
        self.assertEqual(DEFAULT_ENTRY_FLIGHT_PATH_ANGLE_DEG, 65.0)
        self.assertEqual(DEFAULT_BALLISTIC_COEFFICIENT_KG_M2, 38.0)
        self.assertEqual(DEFAULT_SURFACE_DENSITY_KG_M3, 5.43)
        self.assertEqual(DEFAULT_DENSITY_SCALE_HEIGHT_M, 22_000.0)
        self.assertEqual(DEFAULT_PARACHUTE_DEPLOYMENT_SPEED_M_S, 400.0)

    def test_lower_ballistic_coefficient_decelerates_higher(self):
        low_beta_speed = ballistic_speed_at_altitude(
            6_000.0,
            160_000.0,
            ballistic_coefficient_kg_m2=30.0,
        )
        high_beta_speed = ballistic_speed_at_altitude(
            6_000.0,
            160_000.0,
            ballistic_coefficient_kg_m2=60.0,
        )

        self.assertLess(low_beta_speed, high_beta_speed)

    def test_result_states_required_exclusions(self):
        result = compute_titan_edl(NOMINAL_V_INFINITY_M_S, REFERENCE_CAPTURE_DV_M_S)
        exclusions = " ".join(result.exclusions)

        for expected in ("Heat-shield", "Entry-corridor", "g-load", "Parachute", "Landing-site"):
            with self.subTest(expected=expected):
                self.assertIn(expected, exclusions)

    def test_rejects_invalid_inputs(self):
        for value in (math.nan, math.inf, -1.0, True, "1049"):
            with self.subTest(value=value):
                with self.assertRaises((TypeError, ValueError)):
                    compute_titan_edl(value, REFERENCE_CAPTURE_DV_M_S)

        with self.assertRaisesRegex(ValueError, "less than"):
            estimate_ballistic_deployment_altitude(400.0, 400.0)


if __name__ == "__main__":
    unittest.main()
