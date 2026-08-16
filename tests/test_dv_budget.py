import math
import unittest

from mission.dv_budget import MissionDeltaVBudget, compose_complete_dv_budget
from mission.moon_transfer import compute_saturn_titan_transfer
from mission.saturn_staging import compute_saturn_arrival_to_staging


def studies():
    staging = compute_saturn_arrival_to_staging(
        arrival_v_infinity_m_s=6_490.744714263188,
        periapsis_radius_m=62_330_000.0,
        staging_radius_m=600_000_000.0,
        periapsis_radius_provenance="test",
    )
    titan = compute_saturn_titan_transfer(
        saturn_staging_radius_m=staging.staging_radius_m,
        titan_capture_altitude_m=1_500_000.0,
    )
    return staging, titan


class TestCompleteDeltaVBudget(unittest.TestCase):
    def test_composes_every_real_burn_and_ignores_legacy_saturn_capture(self):
        staging, titan = studies()
        earth_budget = {
            "dV from LEO": 4_000.0,
            "dV DSM/Fly-By": 125.0,
            "dV Capture at Destination": 999_999.0,
        }

        budget = compose_complete_dv_budget(earth_budget, staging, titan)

        self.assertIsInstance(budget, MissionDeltaVBudget)
        self.assertEqual(budget.earth_departure_m_s, 4_000.0)
        self.assertEqual(budget.dsm_flyby_m_s, 125.0)
        self.assertEqual(
            budget.saturn_capture_to_ellipse_m_s,
            staging.capture_to_ellipse_delta_v_m_s,
        )
        self.assertEqual(
            budget.saturn_staging_circularisation_m_s,
            staging.staging_circularisation_delta_v_m_s,
        )
        self.assertEqual(budget.saturn_titan_departure_m_s, titan.departure_delta_v_m_s)
        self.assertEqual(budget.titan_capture_m_s, titan.capture_delta_v_m_s)
        self.assertNotIn(999_999.0, budget.as_dict().values())
        self.assertEqual(budget.total_m_s, sum(budget.as_dict().values()))

    def test_nominal_total_has_no_double_counted_legacy_capture(self):
        staging, titan = studies()
        earth_budget = {
            "dV from LEO": 4_000.0,
            "dV DSM/Fly-By": 0.0,
            "dV Capture at Destination": 10_816.855098885902,
        }

        budget = compose_complete_dv_budget(earth_budget, staging, titan)
        expected = 4_000.0 + staging.total_delta_v_m_s + titan.total_delta_v_m_s

        self.assertAlmostEqual(budget.total_m_s, expected, delta=1e-12)

    def test_rejects_missing_or_invalid_earth_terms(self):
        staging, titan = studies()
        with self.assertRaisesRegex(ValueError, "missing required term"):
            compose_complete_dv_budget({"dV from LEO": 4_000.0}, staging, titan)

        for invalid in (-1.0, math.nan, math.inf):
            with self.subTest(invalid=invalid):
                with self.assertRaisesRegex(ValueError, "finite and non-negative"):
                    compose_complete_dv_budget(
                        {"dV from LEO": invalid, "dV DSM/Fly-By": 0.0},
                        staging,
                        titan,
                    )


if __name__ == "__main__":
    unittest.main()
