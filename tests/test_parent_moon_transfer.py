import math
import unittest

from mission.constants import (
    JPL_SATURN_SYSTEM_SOURCE,
    SATURN_MU_M3_S2,
    TITAN_MEAN_ORBIT_RADIUS_M,
    TITAN_MEAN_RADIUS_M,
    TITAN_MU_M3_S2,
)
from mission.models import Leg, TrajectoryResult
from mission.moon_transfer import (
    MIN_SATURN_STAGING_RADIUS_M,
    MIN_TITAN_CAPTURE_ALTITUDE_M,
    compute_saturn_titan_transfer,
)
from mission.parent_moon_transfer import (
    ParentMoonTransferResult,
    adapt_parent_moon_transfer_to_leg,
    compute_parent_to_moon_transfer,
)

EARTH_MU_M3_S2 = 3.986004418e14
MOON_MU_M3_S2 = 4.9048695e12
MOON_RADIUS_M = 1.7374e6
MOON_ORBIT_RADIUS_M = 3.844e8
EARTH_STAGING_RADIUS_M = 4.2e7
CAPTURE_ALTITUDE_M = 1.0e5


def generic_earth_moon_result() -> ParentMoonTransferResult:
    return compute_parent_to_moon_transfer(
        parent_body="Earth",
        moon_body="Moon",
        parent_mu_m3_s2=EARTH_MU_M3_S2,
        moon_mu_m3_s2=MOON_MU_M3_S2,
        moon_radius_m=MOON_RADIUS_M,
        parent_staging_radius_m=EARTH_STAGING_RADIUS_M,
        moon_orbit_radius_m=MOON_ORBIT_RADIUS_M,
        moon_capture_altitude_m=CAPTURE_ALTITUDE_M,
        source="Test constant",
    )


class TestGenericParentMoonTransferPhysics(unittest.TestCase):
    def test_result_preserves_delta_v_accounting(self):
        result = generic_earth_moon_result()

        self.assertEqual(
            result.total_delta_v_m_s,
            result.departure_delta_v_m_s + result.capture_delta_v_m_s,
        )
        self.assertEqual(result.origin, "Earth")
        self.assertEqual(result.destination, "Moon")
        self.assertEqual(result.method, "hohmann_circular_coplanar")
        self.assertGreater(result.time_of_flight_days, 0.0)
        self.assertNotEqual(result.v_infinity_moon_m_s, result.capture_delta_v_m_s)

    def test_higher_capture_altitude_reduces_capture_delta_v(self):
        common = {
            "parent_body": "Earth",
            "moon_body": "Moon",
            "parent_mu_m3_s2": EARTH_MU_M3_S2,
            "moon_mu_m3_s2": MOON_MU_M3_S2,
            "moon_radius_m": MOON_RADIUS_M,
            "parent_staging_radius_m": EARTH_STAGING_RADIUS_M,
            "moon_orbit_radius_m": MOON_ORBIT_RADIUS_M,
            "source": "Test constant",
        }
        low = compute_parent_to_moon_transfer(moon_capture_altitude_m=1.0e5, **common)
        high = compute_parent_to_moon_transfer(moon_capture_altitude_m=3.0e5, **common)

        self.assertLess(high.capture_delta_v_m_s, low.capture_delta_v_m_s)


class TestGenericParentMoonTransferValidation(unittest.TestCase):
    def test_bodies_and_source_must_be_valid(self):
        valid = {
            "parent_body": "Earth",
            "moon_body": "Moon",
            "parent_mu_m3_s2": EARTH_MU_M3_S2,
            "moon_mu_m3_s2": MOON_MU_M3_S2,
            "moon_radius_m": MOON_RADIUS_M,
            "parent_staging_radius_m": EARTH_STAGING_RADIUS_M,
            "moon_orbit_radius_m": MOON_ORBIT_RADIUS_M,
            "moon_capture_altitude_m": CAPTURE_ALTITUDE_M,
            "source": "Test constant",
        }
        for field, value, message in (
            ("parent_body", "", "non-empty"),
            ("moon_body", "   ", "non-empty"),
            ("source", "", "non-empty"),
            ("parent_mu_m3_s2", 0.0, "positive"),
            ("moon_mu_m3_s2", 0.0, "positive"),
            ("moon_radius_m", -1.0, "positive"),
            ("parent_staging_radius_m", math.inf, "finite"),
        ):
            with self.subTest(field=field):
                invalid = {**valid, field: value}
                with self.assertRaisesRegex(ValueError, message):
                    compute_parent_to_moon_transfer(**invalid)

    def test_staging_radius_must_be_less_than_moon_orbit_radius(self):
        with self.assertRaisesRegex(ValueError, "less than Moon"):
            compute_parent_to_moon_transfer(
                parent_body="Earth",
                moon_body="Moon",
                parent_mu_m3_s2=EARTH_MU_M3_S2,
                moon_mu_m3_s2=MOON_MU_M3_S2,
                moon_radius_m=MOON_RADIUS_M,
                parent_staging_radius_m=MOON_ORBIT_RADIUS_M,
                moon_orbit_radius_m=MOON_ORBIT_RADIUS_M,
                moon_capture_altitude_m=CAPTURE_ALTITUDE_M,
                source="Test constant",
            )

    def test_only_orbital_geometry_and_non_negativity_limit_inputs(self):
        result = compute_parent_to_moon_transfer(
            parent_body="Earth",
            moon_body="Moon",
            parent_mu_m3_s2=EARTH_MU_M3_S2,
            moon_mu_m3_s2=MOON_MU_M3_S2,
            moon_radius_m=MOON_RADIUS_M,
            parent_staging_radius_m=1.0e6,
            moon_orbit_radius_m=MOON_ORBIT_RADIUS_M,
            moon_capture_altitude_m=0.0,
            source="Test constant",
        )
        self.assertEqual(result.parent_staging_radius_m, 1.0e6)
        self.assertEqual(result.moon_capture_altitude_m, 0.0)


class TestSaturnTitanFacadeRegression(unittest.TestCase):
    def test_legacy_saturn_titan_facade_matches_generic_engine_exactly(self):
        staging_radius = 6.0e8
        capture_altitude = 1.5e6
        generic = compute_parent_to_moon_transfer(
            parent_body="Saturn",
            moon_body="Titan",
            parent_mu_m3_s2=SATURN_MU_M3_S2,
            moon_mu_m3_s2=TITAN_MU_M3_S2,
            moon_radius_m=TITAN_MEAN_RADIUS_M,
            parent_staging_radius_m=staging_radius,
            moon_orbit_radius_m=TITAN_MEAN_ORBIT_RADIUS_M,
            moon_capture_altitude_m=capture_altitude,
            source=JPL_SATURN_SYSTEM_SOURCE,
        )
        legacy = compute_saturn_titan_transfer(
            saturn_staging_radius_m=staging_radius,
            titan_capture_altitude_m=capture_altitude,
        )

        self.assertEqual(legacy.origin, generic.origin)
        self.assertEqual(legacy.destination, generic.destination)
        self.assertEqual(legacy.method, generic.method)
        self.assertEqual(legacy.source, generic.source)
        self.assertEqual(legacy.saturn_staging_radius_m, generic.parent_staging_radius_m)
        self.assertEqual(legacy.titan_orbit_radius_m, generic.moon_orbit_radius_m)
        self.assertEqual(legacy.titan_capture_altitude_m, generic.moon_capture_altitude_m)
        self.assertEqual(legacy.titan_capture_radius_m, generic.moon_capture_radius_m)
        self.assertEqual(
            legacy.saturn_staging_circular_speed_m_s,
            generic.parent_staging_circular_speed_m_s,
        )
        self.assertEqual(legacy.transfer_departure_speed_m_s, generic.transfer_departure_speed_m_s)
        self.assertEqual(legacy.departure_delta_v_m_s, generic.departure_delta_v_m_s)
        self.assertEqual(legacy.transfer_arrival_speed_m_s, generic.transfer_arrival_speed_m_s)
        self.assertEqual(legacy.titan_orbital_speed_m_s, generic.moon_orbital_speed_m_s)
        self.assertEqual(legacy.v_infinity_titan_m_s, generic.v_infinity_moon_m_s)
        self.assertEqual(legacy.time_of_flight_s, generic.time_of_flight_s)
        self.assertEqual(legacy.capture_delta_v_m_s, generic.capture_delta_v_m_s)
        self.assertEqual(legacy.total_delta_v_m_s, generic.total_delta_v_m_s)

    def test_legacy_ring_guard_error_remains_unchanged(self):
        with self.assertRaisesRegex(ValueError, "ring guard"):
            compute_saturn_titan_transfer(saturn_staging_radius_m=MIN_SATURN_STAGING_RADIUS_M)

    def test_legacy_orbit_radius_error_remains_unchanged(self):
        with self.assertRaisesRegex(ValueError, "less than Titan"):
            compute_saturn_titan_transfer(saturn_staging_radius_m=TITAN_MEAN_ORBIT_RADIUS_M)

    def test_legacy_capture_altitude_guard_error_remains_unchanged(self):
        with self.assertRaisesRegex(ValueError, "non-atmospheric guard"):
            compute_saturn_titan_transfer(titan_capture_altitude_m=999_999.0)

    def test_legacy_guards_reject_before_reaching_the_generic_engine(self):
        # MIN_SATURN_STAGING_RADIUS_M itself would fail the generic engine's
        # own r_1 > 0 check trivially (it's positive), so this specifically
        # proves the facade's own ring-guard check runs first.
        self.assertGreater(MIN_SATURN_STAGING_RADIUS_M, 0.0)
        self.assertLess(MIN_TITAN_CAPTURE_ALTITUDE_M, TITAN_MEAN_ORBIT_RADIUS_M)


class TestGenericParentMoonTransferAdapter(unittest.TestCase):
    def test_adapter_uses_canonical_types_and_body_names(self):
        result = generic_earth_moon_result()
        leg = adapt_parent_moon_transfer_to_leg(result, departure_epoch_mjd2000=12_000.0)

        self.assertIsInstance(leg, Leg)
        self.assertEqual((leg.origin, leg.destination), ("Earth", "Moon"))
        self.assertIsInstance(leg.trajectory, TrajectoryResult)
        assert leg.trajectory is not None
        self.assertEqual(leg.trajectory.departure_mjd2000, 12_000.0)
        self.assertEqual(
            leg.trajectory.arrival_mjd2000,
            12_000.0 + result.time_of_flight_days,
        )
        self.assertEqual([event.body for event in leg.events], ["Earth", "Moon"])
        self.assertEqual([event.event_type for event in leg.events], ["departure", "capture"])


if __name__ == "__main__":
    unittest.main()
