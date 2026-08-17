import math
import unittest

from mission.gravity_assist import (
    compute_unpowered_gravity_assist,
    compute_venus_flyby_demonstration,
    flyby_turn_angle,
)


class GravityAssistPhysicsTests(unittest.TestCase):
    def test_unpowered_flyby_conserves_v_infinity_magnitude(self):
        result = compute_unpowered_gravity_assist(
            body="test body",
            body_radius_m=6_000_000.0,
            gravitational_parameter_m3_s2=3.25e14,
            periapsis_altitude_m=600_000.0,
            v_infinity_in_m_s=(8_000.0, 0.0, 0.0),
            body_heliocentric_velocity_m_s=(0.0, 35_000.0, 0.0),
            turn_axis=(0.0, 0.0, 1.0),
            turn_direction=1,
        )

        outgoing_magnitude = math.sqrt(sum(value**2 for value in result.v_infinity_out_m_s))
        self.assertAlmostEqual(outgoing_magnitude, result.v_infinity_magnitude_m_s, delta=1e-9)

    def test_turn_angle_is_physical_and_decreases_with_periapsis(self):
        low_periapsis = flyby_turn_angle(
            gravitational_parameter_m3_s2=3.24859e14,
            periapsis_radius_m=6_652_000.0,
            v_infinity_m_s=8_000.0,
        )
        high_periapsis = flyby_turn_angle(
            gravitational_parameter_m3_s2=3.24859e14,
            periapsis_radius_m=12_000_000.0,
            v_infinity_m_s=8_000.0,
        )

        self.assertGreater(low_periapsis, high_periapsis)
        self.assertGreater(high_periapsis, 0.0)
        self.assertLess(low_periapsis, math.pi)

    def test_fixed_venus_demonstration_is_reproducible_and_gains_solar_frame_speed(self):
        first = compute_venus_flyby_demonstration()
        second = compute_venus_flyby_demonstration()

        self.assertEqual(first, second)
        self.assertGreater(first.heliocentric_speed_change_m_s, 0.0)
        outgoing_magnitude = math.sqrt(sum(value**2 for value in first.v_infinity_out_m_s))
        self.assertAlmostEqual(outgoing_magnitude, first.v_infinity_magnitude_m_s, delta=1e-9)


if __name__ == "__main__":
    unittest.main()
