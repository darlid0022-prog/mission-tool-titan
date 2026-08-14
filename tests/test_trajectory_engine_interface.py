import unittest

from mission.models import TrajectoryResult
from mission.trajectory_engine import TrajectoryEngine


class DummyEngine:
    def compute_trajectory(self, *args, **kwargs) -> TrajectoryResult:
        return TrajectoryResult(
            departure_mjd2000=1.0,
            arrival_mjd2000=2.0,
            tof_years=1.0,
            v_inf_depart=2.5,
            v_inf_arrival=3.5,
            delta_v=None,
            method="dummy",
            notes="test implementation",
        )


class TestTrajectoryEngineInterface(unittest.TestCase):
    def test_interface_can_be_imported(self):
        self.assertTrue(callable(TrajectoryEngine))

    def test_implementation_can_be_used(self):
        engine = DummyEngine()
        result = engine.compute_trajectory()
        self.assertIsInstance(result, TrajectoryResult)
        self.assertEqual(result.method, "dummy")


if __name__ == "__main__":
    unittest.main()
