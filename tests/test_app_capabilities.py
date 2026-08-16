import unittest

from mission.capabilities import (
    CONNECTED_CHAIN_DESTINATIONS,
    PLANNED_DESTINATIONS,
    PLANNED_MISSION_FEATURES,
    SUPPORTED_DESTINATIONS,
)


class TestAppCapabilities(unittest.TestCase):
    def test_saturn_is_the_only_calculable_destination(self):
        self.assertEqual(SUPPORTED_DESTINATIONS, ("Saturn",))

    def test_titan_is_connected_but_not_a_direct_lambert_target(self):
        self.assertIn("Titan", CONNECTED_CHAIN_DESTINATIONS)
        self.assertNotIn("Titan", PLANNED_DESTINATIONS)
        self.assertNotIn("Titan", SUPPORTED_DESTINATIONS)

    def test_supported_and_planned_destinations_do_not_overlap(self):
        self.assertTrue(set(SUPPORTED_DESTINATIONS).isdisjoint(PLANNED_DESTINATIONS))
        self.assertTrue(set(CONNECTED_CHAIN_DESTINATIONS).isdisjoint(PLANNED_DESTINATIONS))

    def test_unimplemented_mission_features_are_declared_as_planned(self):
        self.assertIn("High-fidelity Saturn to Titan trajectory", PLANNED_MISSION_FEATURES)
        self.assertIn("Landing and atmospheric descent", PLANNED_MISSION_FEATURES)


if __name__ == "__main__":
    unittest.main()
