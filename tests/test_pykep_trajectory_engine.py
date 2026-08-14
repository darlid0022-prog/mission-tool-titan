import unittest
from datetime import date

from mission.leg_solver import compute_lambert_leg
from mission.pykep_trajectory_engine import PyKEPTrajectoryEngine
from mission.trajectory_engine import TrajectoryEngine


class TestPyKEPTrajectoryEngine(unittest.TestCase):
    def test_backend_implements_engine_interface(self):
        engine = PyKEPTrajectoryEngine()
        self.assertTrue(isinstance(engine, TrajectoryEngine))

    def test_backend_delegates_to_existing_lambert_solver(self):
        engine = PyKEPTrajectoryEngine()
        start = date(2026, 6, 1)
        end = date(2027, 6, 1)

        delegated = engine.compute_trajectory("Earth", "Saturn", start, end)
        direct = compute_lambert_leg("Earth", "Saturn", start, end)

        self.assertEqual(len(delegated), len(direct))
        self.assertEqual(delegated[0].departure_mjd2000, direct[0].departure_mjd2000)
        self.assertEqual(delegated[0].arrival_mjd2000, direct[0].arrival_mjd2000)
        self.assertEqual(delegated[0].tof_years, direct[0].tof_years)


if __name__ == "__main__":
    unittest.main()
