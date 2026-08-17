import unittest

from mission.capabilities import (
    MOON_DESTINATIONS,
    PLANET_DESTINATIONS,
    PLANNED_DESTINATIONS,
    PLANNED_MISSION_FEATURES,
)


class TestAppCapabilities(unittest.TestCase):
    def test_saturn_is_a_calculable_planet_destination(self):
        self.assertIn("Saturn", PLANET_DESTINATIONS)

    def test_planet_destinations_are_exactly_the_lambert_capable_planets(self):
        self.assertEqual(
            PLANET_DESTINATIONS,
            ("Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune"),
        )

    def test_titan_is_a_moon_destination_reached_through_saturn(self):
        self.assertEqual(MOON_DESTINATIONS["Titan"], "Saturn")
        self.assertNotIn("Titan", PLANNED_DESTINATIONS)
        self.assertNotIn("Titan", PLANET_DESTINATIONS)

    def test_planet_moon_and_planned_destinations_do_not_overlap(self):
        self.assertTrue(set(PLANET_DESTINATIONS).isdisjoint(PLANNED_DESTINATIONS))
        self.assertTrue(set(MOON_DESTINATIONS).isdisjoint(PLANNED_DESTINATIONS))
        self.assertTrue(set(PLANET_DESTINATIONS).isdisjoint(MOON_DESTINATIONS))

    def test_unimplemented_mission_features_are_declared_as_planned(self):
        self.assertIn("High-fidelity Saturn to Titan trajectory", PLANNED_MISSION_FEATURES)
        self.assertIn("High-fidelity Titan EDL and landing dynamics", PLANNED_MISSION_FEATURES)


if __name__ == "__main__":
    unittest.main()
