import unittest

from mission.models import Leg, Mission, TrajectoryResult


class TestMissionMultilegModel(unittest.TestCase):
    def test_mission_can_contain_multiple_ordered_legs(self):
        leg1 = Leg(
            origin="Earth",
            destination="Saturn",
            trajectory=TrajectoryResult(
                departure_mjd2000=9648.0,
                arrival_mjd2000=11109.0,
                tof_years=4.0,
                v_inf_depart=10432.306468285773,
                v_inf_arrival=6490.744714263188,
                delta_v=None,
                method="lambert",
            ),
        )
        leg2 = Leg(
            origin="Saturn",
            destination="Titan",
            trajectory=TrajectoryResult(
                departure_mjd2000=11109.0,
                arrival_mjd2000=12000.0,
                tof_years=2.0,
                v_inf_depart=2000.0,
                v_inf_arrival=1500.0,
                delta_v=None,
                method="placeholder",
            ),
        )

        mission = Mission(name="Earth -> Saturn -> Titan", legs=[leg1, leg2])

        self.assertEqual(len(mission.legs), 2)
        self.assertEqual(mission.legs[0].origin, "Earth")
        self.assertEqual(mission.legs[0].destination, "Saturn")
        self.assertEqual(mission.legs[1].origin, "Saturn")
        self.assertEqual(mission.legs[1].destination, "Titan")
        self.assertEqual(mission.legs[0].destination, mission.legs[1].origin)

        self.assertEqual(
            mission.legs[0].trajectory.arrival_mjd2000, leg1.trajectory.arrival_mjd2000
        )
        self.assertEqual(
            mission.legs[1].trajectory.departure_mjd2000, leg2.trajectory.departure_mjd2000
        )


if __name__ == "__main__":
    unittest.main()
