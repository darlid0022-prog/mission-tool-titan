import math
import unittest

from mission.gravity_assist import (
    DEMO_EARTH_DEPARTURE,
    DEMO_SATURN_ARRIVAL,
    DEMO_SECOND_VENUS_FLYBY_ALTITUDE_M,
    CASSINI_SOI_PERIAPSIS_ALTITUDE_M,
    GravityAssistResult,
    OrbitInsertionResult,
    compute_cassini_historical_tour,
    compute_earth_flyby_demonstration,
    compute_jupiter_flyby_demonstration,
    compute_saturn_orbit_insertion,
    compute_second_venus_flyby_demonstration,
    compute_venus_flyby_demonstration,
)


def _magnitude(vector) -> float:
    return math.sqrt(sum(value**2 for value in vector))


class TestSecondVenusFlyby(unittest.TestCase):
    def test_uses_the_documented_second_flyby_altitude(self):
        result = compute_second_venus_flyby_demonstration()

        self.assertEqual(result.periapsis_altitude_m, DEMO_SECOND_VENUS_FLYBY_ALTITUDE_M)
        self.assertAlmostEqual(result.periapsis_altitude_m, 600_000.0)

    def test_conserves_v_infinity_magnitude_and_has_a_physical_turn(self):
        result = compute_second_venus_flyby_demonstration()

        self.assertAlmostEqual(
            _magnitude(result.v_infinity_out_m_s),
            result.v_infinity_magnitude_m_s,
            delta=1e-9,
        )
        self.assertGreater(result.turn_angle_rad, 0.0)
        self.assertLess(result.turn_angle_rad, math.pi)

    def test_is_reproducible(self):
        self.assertEqual(
            compute_second_venus_flyby_demonstration(),
            compute_second_venus_flyby_demonstration(),
        )

    def test_first_and_second_flyby_use_different_documented_altitudes(self):
        # Regression guard for the historical fix this task made: the first
        # flyby (284 km) and second flyby (600 km) must not share one altitude.
        first = compute_venus_flyby_demonstration()
        second = compute_second_venus_flyby_demonstration()

        self.assertNotEqual(first.periapsis_altitude_m, second.periapsis_altitude_m)
        self.assertAlmostEqual(first.periapsis_altitude_m, 284_000.0)
        self.assertAlmostEqual(second.periapsis_altitude_m, 600_000.0)


class TestSaturnOrbitInsertion(unittest.TestCase):
    def test_uses_the_documented_periapsis_altitude(self):
        result = compute_saturn_orbit_insertion()

        self.assertEqual(result.periapsis_altitude_m, CASSINI_SOI_PERIAPSIS_ALTITUDE_M)
        self.assertAlmostEqual(result.periapsis_altitude_m, 20_000_000.0)
        # Cross-checked against the ESA-documented ~80,230 km periapsis radius
        # from Saturn's center (see SOI_SOURCE) - within a reasonable margin
        # given the different reference-radius conventions.
        self.assertAlmostEqual(result.periapsis_radius_m, 80_230_000.0, delta=500_000.0)

    def test_is_a_propulsive_capture_not_an_unpowered_flyby(self):
        result = compute_saturn_orbit_insertion()

        self.assertIsInstance(result, OrbitInsertionResult)
        self.assertGreater(result.delta_v_m_s, 0.0)
        self.assertGreater(result.v_infinity_magnitude_m_s, 0.0)

    def test_is_reproducible(self):
        self.assertEqual(compute_saturn_orbit_insertion(), compute_saturn_orbit_insertion())


class TestCassiniHistoricalTour(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tour = compute_cassini_historical_tour()

    def test_chains_five_segments_in_the_correct_order(self):
        self.assertEqual(len(self.tour), 5)
        self.assertEqual(
            [(segment.departure_body, segment.arrival_body) for segment in self.tour],
            [
                ("Earth", "Venus"),
                ("Venus", "Venus"),
                ("Venus", "Earth"),
                ("Earth", "Jupiter"),
                ("Jupiter", "Saturn"),
            ],
        )

    def test_first_four_segments_are_unpowered_flybys_last_is_orbit_insertion(self):
        for segment in self.tour[:4]:
            with self.subTest(segment=segment.name):
                self.assertIsInstance(segment.result, GravityAssistResult)
        self.assertIsInstance(self.tour[-1].result, OrbitInsertionResult)

    def test_segments_are_positionally_continuous(self):
        """Each segment's arrival position/epoch/body must exactly equal the
        next segment's departure position/epoch/body - the same body sampled
        at the same epoch should always agree, but this is checked explicitly
        rather than assumed."""
        for earlier, later in zip(self.tour, self.tour[1:]):
            with self.subTest(leg=f"{earlier.name} -> {later.name}"):
                self.assertEqual(earlier.arrival_body, later.departure_body)
                self.assertEqual(earlier.arrival_epoch_mjd2000, later.departure_epoch_mjd2000)
                self.assertEqual(earlier.arrival_position_m, later.departure_position_m)

    def test_tour_epochs_span_the_real_mission_dates(self):
        first_departure = self.tour[0].departure_epoch_mjd2000
        last_arrival = self.tour[-1].arrival_epoch_mjd2000
        self.assertLess(first_departure, last_arrival)

        import pykep as pk

        self.assertEqual(first_departure, pk.epoch(DEMO_EARTH_DEPARTURE).mjd2000)
        self.assertEqual(last_arrival, pk.epoch(DEMO_SATURN_ARRIVAL).mjd2000)
        duration_days = last_arrival - first_departure
        # Real Cassini cruise, October 1997 -> July 2004, is about 6.7 years.
        self.assertAlmostEqual(duration_days / 365.25, 6.7, delta=0.1)

    def test_tour_segment_results_match_the_standalone_demonstration_functions(self):
        """The chain must reuse the exact same per-leg computation as the
        individual compute_*_demonstration functions - not a re-derived copy."""
        expected = (
            compute_venus_flyby_demonstration(),
            compute_second_venus_flyby_demonstration(),
            compute_earth_flyby_demonstration(),
            compute_jupiter_flyby_demonstration(),
            compute_saturn_orbit_insertion(),
        )
        for segment, expected_result in zip(self.tour, expected):
            with self.subTest(segment=segment.name):
                self.assertEqual(segment.result, expected_result)


if __name__ == "__main__":
    unittest.main()
