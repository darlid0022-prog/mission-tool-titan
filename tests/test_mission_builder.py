import unittest
from datetime import date

from trajectory import compute_trajectory_alternatives
from mission.builder import build_mission_from_trajectory_alternatives


class TestMissionBuilder(unittest.TestCase):
    def setUp(self):
        self.alternatives = compute_trajectory_alternatives(
            "Saturn",
            "Direct",
            date(2026, 6, 1),
            date(2027, 6, 1),
            True,
            False,
            False,
            1000.0,
        )
        self.mission = build_mission_from_trajectory_alternatives(self.alternatives)

    def test_earth_saturn_trajectory_can_be_converted_to_mission(self):
        self.assertIsNotNone(self.mission)
        self.assertEqual(self.mission.name, "Earth -> Saturn")

    def test_mission_contains_exactly_one_leg(self):
        self.assertEqual(len(self.mission.legs), 1)

    def test_leg_origin_and_destination(self):
        leg = self.mission.legs[0]
        self.assertEqual(leg.origin, "Earth")
        self.assertEqual(leg.destination, "Saturn")

    def test_trajectory_result_contains_correct_vinf_values(self):
        leg = self.mission.legs[0]
        trajectory = leg.trajectory
        self.assertIsNotNone(trajectory)

        reference = self.alternatives["best_by_departure_v_inf"]
        self.assertEqual(trajectory.departure_mjd2000, reference["departure_mjd2000"])
        self.assertEqual(trajectory.arrival_mjd2000, reference["arrival_mjd2000"])
        self.assertEqual(trajectory.tof_years, reference["tof_years"])
        self.assertEqual(trajectory.v_inf_depart, reference["dv_depart"])
        self.assertEqual(trajectory.v_inf_arrival, reference["v_infinity_saturn"])

    def test_propulsive_delta_v_remains_unset(self):
        leg = self.mission.legs[0]
        self.assertIsNone(leg.trajectory.delta_v)

    def test_original_trajectory_values_are_unchanged(self):
        reference = self.alternatives["best_by_departure_v_inf"]
        leg = self.mission.legs[0]
        trajectory = leg.trajectory

        self.assertEqual(reference["departure_mjd2000"], trajectory.departure_mjd2000)
        self.assertEqual(reference["arrival_mjd2000"], trajectory.arrival_mjd2000)
        self.assertEqual(reference["tof_years"], trajectory.tof_years)
        self.assertEqual(reference["dv_depart"], trajectory.v_inf_depart)
        self.assertEqual(reference["v_infinity_saturn"], trajectory.v_inf_arrival)


if __name__ == "__main__":
    unittest.main()
