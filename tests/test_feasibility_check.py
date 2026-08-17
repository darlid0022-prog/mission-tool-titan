import unittest

from mission.feasibility_check import evaluate_single_stage_chemical_feasibility
from mission.mass_model import PayloadItem


class TestSingleStageFeasibility(unittest.TestCase):
    def test_direct_connected_mission_reports_calibrated_infeasibility(self):
        result = evaluate_single_stage_chemical_feasibility(
            16_284.134471417781,
            320.0,
            (PayloadItem("Science payload (aggregate)", 143.5, 323.0),),
        )

        self.assertFalse(result.is_feasible)
        self.assertAlmostEqual(result.maximum_feasible_delta_v_m_s, 3_833.463446431911, places=9)
        self.assertAlmostEqual(result.threshold_exceedance_factor, 4.247890895261994, places=12)
        self.assertIn("diverge", result.model_message)


if __name__ == "__main__":
    unittest.main()
