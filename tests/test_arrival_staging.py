import math
import unittest

from mission.arrival_staging import (
    ArrivalStagingResult,
    StagingRadiusGuard,
    adapt_arrival_staging_to_leg,
    compute_arrival_to_staging,
)
from mission.constants import JPL_SATURN_SYSTEM_SOURCE, SATURN_MU_M3_S2
from mission.models import Leg, TrajectoryResult
from mission.saturn_staging import (
    MIN_SATURN_STAGING_RADIUS_M,
    compute_saturn_arrival_to_staging,
)

EARTH_MU_M3_S2 = 3.986004418e14
EARTH_PERIAPSIS_RADIUS_M = 7.0e6
EARTH_STAGING_RADIUS_M = 4.2e7
PROVENANCE = "Test-only parent radius plus a documented periapsis altitude"


def generic_earth_result() -> ArrivalStagingResult:
    return compute_arrival_to_staging(
        parent_body="Earth",
        parent_mu_m3_s2=EARTH_MU_M3_S2,
        arrival_v_infinity_m_s=2_500.0,
        periapsis_radius_m=EARTH_PERIAPSIS_RADIUS_M,
        staging_radius_m=EARTH_STAGING_RADIUS_M,
        source="Test constant",
        periapsis_radius_provenance=PROVENANCE,
    )


class TestGenericArrivalStagingPhysics(unittest.TestCase):
    def test_result_preserves_two_body_energy_and_delta_v_accounting(self):
        result = generic_earth_result()

        incoming_energy = result.hyperbolic_periapsis_speed_m_s**2 / 2.0 - (
            EARTH_MU_M3_S2 / result.periapsis_radius_m
        )
        transfer_energy_at_periapsis = result.transfer_periapsis_speed_m_s**2 / 2.0 - (
            EARTH_MU_M3_S2 / result.periapsis_radius_m
        )
        transfer_energy_at_apoapsis = result.transfer_apoapsis_speed_m_s**2 / 2.0 - (
            EARTH_MU_M3_S2 / result.staging_radius_m
        )
        expected_transfer_energy = -EARTH_MU_M3_S2 / (2.0 * result.transfer_semimajor_axis_m)

        self.assertAlmostEqual(
            incoming_energy,
            result.arrival_v_infinity_m_s**2 / 2.0,
            delta=1e-6,
        )
        self.assertAlmostEqual(
            transfer_energy_at_periapsis,
            expected_transfer_energy,
            delta=1e-6,
        )
        self.assertAlmostEqual(
            transfer_energy_at_apoapsis,
            expected_transfer_energy,
            delta=1e-6,
        )
        self.assertEqual(
            result.total_delta_v_m_s,
            result.capture_to_ellipse_delta_v_m_s + result.staging_circularisation_delta_v_m_s,
        )
        self.assertEqual(result.parent_body, "Earth")
        self.assertGreater(result.time_of_flight_days, 0.0)

    def test_capture_delta_v_increases_with_arrival_v_infinity(self):
        common = {
            "parent_body": "Earth",
            "parent_mu_m3_s2": EARTH_MU_M3_S2,
            "periapsis_radius_m": EARTH_PERIAPSIS_RADIUS_M,
            "staging_radius_m": EARTH_STAGING_RADIUS_M,
            "source": "Test constant",
            "periapsis_radius_provenance": PROVENANCE,
        }
        low = compute_arrival_to_staging(arrival_v_infinity_m_s=1_000.0, **common)
        high = compute_arrival_to_staging(arrival_v_infinity_m_s=5_000.0, **common)

        self.assertGreater(high.capture_to_ellipse_delta_v_m_s, low.capture_to_ellipse_delta_v_m_s)


class TestGenericArrivalStagingValidation(unittest.TestCase):
    def test_body_mu_and_provenance_must_be_valid(self):
        valid = {
            "parent_body": "Earth",
            "parent_mu_m3_s2": EARTH_MU_M3_S2,
            "arrival_v_infinity_m_s": 2_500.0,
            "periapsis_radius_m": EARTH_PERIAPSIS_RADIUS_M,
            "staging_radius_m": EARTH_STAGING_RADIUS_M,
            "source": "Test constant",
            "periapsis_radius_provenance": PROVENANCE,
        }
        for field, value, message in (
            ("parent_body", "", "non-empty"),
            ("source", "   ", "non-empty"),
            ("parent_mu_m3_s2", 0.0, "positive"),
            ("parent_mu_m3_s2", math.inf, "finite"),
            ("periapsis_radius_provenance", "", "non-empty"),
        ):
            with self.subTest(field=field):
                invalid = {**valid, field: value}
                with self.assertRaisesRegex(ValueError, message):
                    compute_arrival_to_staging(**invalid)

    def test_optional_body_specific_guard_is_enforced(self):
        with self.assertRaisesRegex(ValueError, "radiation-zone guard"):
            compute_arrival_to_staging(
                parent_body="Example",
                parent_mu_m3_s2=EARTH_MU_M3_S2,
                arrival_v_infinity_m_s=2_500.0,
                periapsis_radius_m=EARTH_PERIAPSIS_RADIUS_M,
                staging_radius_m=2.0e7,
                source="Test constant",
                periapsis_radius_provenance=PROVENANCE,
                staging_radius_guard=StagingRadiusGuard(
                    minimum_radius_m=2.0e7,
                    description="the radiation-zone guard",
                ),
            )

    def test_without_guard_only_orbital_geometry_limits_staging_radius(self):
        result = compute_arrival_to_staging(
            parent_body="Example",
            parent_mu_m3_s2=EARTH_MU_M3_S2,
            arrival_v_infinity_m_s=2_500.0,
            periapsis_radius_m=EARTH_PERIAPSIS_RADIUS_M,
            staging_radius_m=2.0e7,
            source="Test constant",
            periapsis_radius_provenance=PROVENANCE,
        )

        self.assertEqual(result.staging_radius_m, 2.0e7)


class TestSaturnArrivalStagingFacadeRegression(unittest.TestCase):
    def test_legacy_saturn_facade_matches_generic_engine_exactly(self):
        v_infinity = 6_490.744714263188
        periapsis = 62_330_000.0
        staging = 600_000_000.0
        generic = compute_arrival_to_staging(
            parent_body="Saturn",
            parent_mu_m3_s2=SATURN_MU_M3_S2,
            arrival_v_infinity_m_s=v_infinity,
            periapsis_radius_m=periapsis,
            staging_radius_m=staging,
            source=JPL_SATURN_SYSTEM_SOURCE,
            periapsis_radius_provenance=PROVENANCE,
            staging_radius_guard=StagingRadiusGuard(
                minimum_radius_m=MIN_SATURN_STAGING_RADIUS_M,
                description="the preliminary outer E-ring guard",
            ),
        )
        legacy = compute_saturn_arrival_to_staging(
            v_infinity,
            periapsis,
            staging,
            periapsis_radius_provenance=PROVENANCE,
        )

        common_fields = (
            "origin_state",
            "destination_state",
            "method",
            "source",
            "arrival_v_infinity_m_s",
            "periapsis_radius_m",
            "staging_radius_m",
            "transfer_semimajor_axis_m",
            "hyperbolic_periapsis_speed_m_s",
            "transfer_periapsis_speed_m_s",
            "capture_to_ellipse_delta_v_m_s",
            "transfer_apoapsis_speed_m_s",
            "staging_circular_speed_m_s",
            "staging_circularisation_delta_v_m_s",
            "total_delta_v_m_s",
            "time_of_flight_s",
            "periapsis_radius_provenance",
        )
        for field in common_fields:
            with self.subTest(field=field):
                self.assertEqual(getattr(legacy, field), getattr(generic, field))

    def test_legacy_saturn_guard_error_remains_unchanged(self):
        with self.assertRaisesRegex(ValueError, "preliminary outer E-ring guard"):
            compute_saturn_arrival_to_staging(
                6_490.0,
                62_330_000.0,
                MIN_SATURN_STAGING_RADIUS_M,
                periapsis_radius_provenance=PROVENANCE,
            )


class TestGenericArrivalStagingAdapter(unittest.TestCase):
    def test_adapter_uses_canonical_types_and_parent_body(self):
        result = generic_earth_result()
        leg = adapt_arrival_staging_to_leg(result, capture_epoch_mjd2000=12_000.0)

        self.assertIsInstance(leg, Leg)
        self.assertEqual((leg.origin, leg.destination), ("Earth", "Earth"))
        self.assertIsInstance(leg.trajectory, TrajectoryResult)
        assert leg.trajectory is not None
        self.assertEqual(leg.trajectory.departure_mjd2000, 12_000.0)
        self.assertEqual(
            leg.trajectory.arrival_mjd2000,
            12_000.0 + result.time_of_flight_days,
        )
        self.assertEqual([event.body for event in leg.events], ["Earth", "Earth"])
        self.assertEqual([event.event_type for event in leg.events], ["capture", "insertion"])


if __name__ == "__main__":
    unittest.main()
