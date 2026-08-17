import math
import unittest

from mission.gravity_assist import (
    compute_earth_flyby_demonstration,
    compute_jupiter_flyby_demonstration,
)


def _magnitude(vector: tuple[float, float, float]) -> float:
    return math.sqrt(sum(value**2 for value in vector))


class AdditionalGravityAssistScenarioTests(unittest.TestCase):
    def test_earth_demonstration_conserves_energy_and_has_physical_turn(self):
        result = compute_earth_flyby_demonstration()

        self.assertAlmostEqual(
            _magnitude(result.v_infinity_out_m_s),
            result.v_infinity_magnitude_m_s,
            delta=1e-9,
        )
        self.assertGreater(result.turn_angle_rad, 0.0)
        self.assertLess(result.turn_angle_rad, math.pi)
        self.assertGreater(result.heliocentric_speed_change_m_s, 0.0)

    def test_jupiter_demonstration_conserves_energy_and_has_physical_turn(self):
        result = compute_jupiter_flyby_demonstration()

        self.assertAlmostEqual(
            _magnitude(result.v_infinity_out_m_s),
            result.v_infinity_magnitude_m_s,
            delta=1e-9,
        )
        self.assertGreater(result.turn_angle_rad, 0.0)
        self.assertLess(result.turn_angle_rad, math.pi)
        self.assertGreater(result.heliocentric_speed_change_m_s, 0.0)


if __name__ == "__main__":
    unittest.main()
