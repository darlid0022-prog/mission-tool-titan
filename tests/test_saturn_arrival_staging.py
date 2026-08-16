import math
import unittest

from mission.constants import SATURN_MU_M3_S2
from mission.models import Leg, TrajectoryResult
from mission.saturn_staging import (
    ALTERNATE_E_RING_OUTER_RADIUS_M,
    D_RING_INNER_EDGE_RADIUS_M,
    DEFAULT_SATURN_STAGING_RADIUS_M,
    F_RING_REFERENCE_RADIUS_M,
    MIN_SATURN_STAGING_RADIUS_M,
    REPLACED_BUDGET_TERM,
    SaturnArrivalStagingResult,
    adapt_saturn_arrival_staging_to_leg,
    compute_saturn_arrival_to_staging,
)

NOMINAL_V_INFINITY_M_S = 6_490.744714263188
NOMINAL_PERIAPSIS_RADIUS_M = 62_330_000.0
NOMINAL_PROVENANCE = "PyKEP Saturn radius 60,330 km + UI capture altitude 2,000 km"
ABS_TOL_M_S = 1e-3
ABS_TOL_S = 1e-3


def nominal_result() -> SaturnArrivalStagingResult:
    return compute_saturn_arrival_to_staging(
        NOMINAL_V_INFINITY_M_S,
        NOMINAL_PERIAPSIS_RADIUS_M,
        periapsis_radius_provenance=NOMINAL_PROVENANCE,
    )


class TestSaturnArrivalStagingRegression(unittest.TestCase):
    def test_nominal_result_matches_specification(self):
        result = nominal_result()

        self.assertAlmostEqual(
            result.hyperbolic_periapsis_speed_m_s, 35_485.756342, delta=ABS_TOL_M_S
        )
        self.assertAlmostEqual(
            result.transfer_periapsis_speed_m_s, 33_204.976183, delta=ABS_TOL_M_S
        )
        self.assertAlmostEqual(
            result.capture_to_ellipse_delta_v_m_s, 2_280.780159, delta=ABS_TOL_M_S
        )
        self.assertAlmostEqual(result.transfer_apoapsis_speed_m_s, 3_449.443609, delta=ABS_TOL_M_S)
        self.assertAlmostEqual(result.staging_circular_speed_m_s, 7_951.017359, delta=ABS_TOL_M_S)
        self.assertAlmostEqual(
            result.staging_circularisation_delta_v_m_s, 4_501.573750, delta=ABS_TOL_M_S
        )
        self.assertAlmostEqual(result.total_delta_v_m_s, 6_782.353909, delta=ABS_TOL_M_S)
        self.assertAlmostEqual(result.time_of_flight_s, 97_211.622651, delta=ABS_TOL_S)
        self.assertAlmostEqual(result.time_of_flight_days, 1.125135, delta=1e-6)

    def test_budget_contract_and_ring_margins_are_explicit(self):
        result = nominal_result()

        self.assertEqual(result.replaces_budget_term, REPLACED_BUDGET_TERM)
        self.assertEqual(result.ring_clearance_status, "unresolved")
        self.assertEqual(result.transfer_safety_margin_status, "unestablished")
        self.assertEqual(result.f_ring_radial_margin_m, -77_850_000.0)
        self.assertEqual(result.periapsis_below_d_ring_inner_edge_m, 4_570_000.0)
        self.assertEqual(result.staging_e_ring_radial_margin_m, 118_000_000.0)
        self.assertEqual(F_RING_REFERENCE_RADIUS_M, 140_180_000.0)
        self.assertEqual(D_RING_INNER_EDGE_RADIUS_M, 66_900_000.0)
        self.assertEqual(ALTERNATE_E_RING_OUTER_RADIUS_M, 482_000_000.0)

    def test_phase_total_contains_exactly_the_two_modelled_burns(self):
        result = nominal_result()

        self.assertAlmostEqual(
            result.total_delta_v_m_s,
            result.capture_to_ellipse_delta_v_m_s + result.staging_circularisation_delta_v_m_s,
            delta=1e-12,
        )
        self.assertNotAlmostEqual(result.total_delta_v_m_s, 10_816.857540, delta=1e-3)


class TestSaturnArrivalStagingInvariants(unittest.TestCase):
    def test_specific_orbital_energy_is_consistent_at_both_apsides(self):
        result = nominal_result()
        mu = SATURN_MU_M3_S2

        incoming_energy = result.hyperbolic_periapsis_speed_m_s**2 / 2.0 - (
            mu / result.periapsis_radius_m
        )
        expected_incoming_energy = result.arrival_v_infinity_m_s**2 / 2.0
        transfer_energy_at_periapsis = result.transfer_periapsis_speed_m_s**2 / 2.0 - (
            mu / result.periapsis_radius_m
        )
        transfer_energy_at_apoapsis = result.transfer_apoapsis_speed_m_s**2 / 2.0 - (
            mu / result.staging_radius_m
        )
        expected_transfer_energy = -mu / (2.0 * result.transfer_semimajor_axis_m)

        self.assertAlmostEqual(incoming_energy, expected_incoming_energy, delta=1e-5)
        self.assertAlmostEqual(transfer_energy_at_periapsis, expected_transfer_energy, delta=1e-5)
        self.assertAlmostEqual(transfer_energy_at_apoapsis, expected_transfer_energy, delta=1e-5)

    def test_specific_angular_momentum_is_consistent_at_both_apsides(self):
        result = nominal_result()

        periapsis_momentum = result.periapsis_radius_m * result.transfer_periapsis_speed_m_s
        apoapsis_momentum = result.staging_radius_m * result.transfer_apoapsis_speed_m_s
        self.assertAlmostEqual(periapsis_momentum, apoapsis_momentum, delta=1e-3)

    def test_staging_state_satisfies_circular_orbit_identity(self):
        result = nominal_result()
        reconstructed_mu = result.staging_circular_speed_m_s**2 * result.staging_radius_m

        self.assertAlmostEqual(reconstructed_mu, SATURN_MU_M3_S2, delta=1.0)

    def test_capture_delta_v_increases_with_arrival_v_infinity(self):
        low = compute_saturn_arrival_to_staging(
            2_000.0,
            NOMINAL_PERIAPSIS_RADIUS_M,
            periapsis_radius_provenance=NOMINAL_PROVENANCE,
        )
        high = compute_saturn_arrival_to_staging(
            8_000.0,
            NOMINAL_PERIAPSIS_RADIUS_M,
            periapsis_radius_provenance=NOMINAL_PROVENANCE,
        )

        self.assertGreater(high.capture_to_ellipse_delta_v_m_s, low.capture_to_ellipse_delta_v_m_s)

    def test_zero_arrival_v_infinity_is_finite_and_non_negative(self):
        result = compute_saturn_arrival_to_staging(
            0.0,
            NOMINAL_PERIAPSIS_RADIUS_M,
            periapsis_radius_provenance=NOMINAL_PROVENANCE,
        )

        self.assertTrue(math.isfinite(result.total_delta_v_m_s))
        self.assertGreaterEqual(result.capture_to_ellipse_delta_v_m_s, 0.0)


class TestSaturnArrivalStagingValidation(unittest.TestCase):
    def test_rejects_non_numeric_boolean_and_non_finite_inputs(self):
        for value, exception in (
            ("6490", TypeError),
            (True, TypeError),
            (None, TypeError),
            (math.nan, ValueError),
            (math.inf, ValueError),
            (-math.inf, ValueError),
        ):
            with self.subTest(value=value):
                with self.assertRaises(exception):
                    compute_saturn_arrival_to_staging(
                        value,
                        NOMINAL_PERIAPSIS_RADIUS_M,
                        periapsis_radius_provenance=NOMINAL_PROVENANCE,
                    )

    def test_rejects_negative_v_infinity_and_non_positive_periapsis(self):
        with self.assertRaisesRegex(ValueError, "non-negative"):
            compute_saturn_arrival_to_staging(
                -1.0,
                NOMINAL_PERIAPSIS_RADIUS_M,
                periapsis_radius_provenance=NOMINAL_PROVENANCE,
            )
        for periapsis in (0.0, -1.0):
            with self.subTest(periapsis=periapsis):
                with self.assertRaisesRegex(ValueError, "positive"):
                    compute_saturn_arrival_to_staging(
                        NOMINAL_V_INFINITY_M_S,
                        periapsis,
                        periapsis_radius_provenance=NOMINAL_PROVENANCE,
                    )

    def test_rejects_staging_at_or_below_ring_guard(self):
        for staging in (MIN_SATURN_STAGING_RADIUS_M, MIN_SATURN_STAGING_RADIUS_M - 1.0):
            with self.subTest(staging=staging):
                with self.assertRaisesRegex(ValueError, "E-ring guard"):
                    compute_saturn_arrival_to_staging(
                        NOMINAL_V_INFINITY_M_S,
                        NOMINAL_PERIAPSIS_RADIUS_M,
                        staging,
                        periapsis_radius_provenance=NOMINAL_PROVENANCE,
                    )

    def test_rejects_staging_at_or_below_periapsis(self):
        periapsis = DEFAULT_SATURN_STAGING_RADIUS_M + 1.0
        with self.assertRaisesRegex(ValueError, "greater than periapsis"):
            compute_saturn_arrival_to_staging(
                NOMINAL_V_INFINITY_M_S,
                periapsis,
                DEFAULT_SATURN_STAGING_RADIUS_M,
                periapsis_radius_provenance=NOMINAL_PROVENANCE,
            )

    def test_rejects_empty_periapsis_provenance(self):
        for provenance in ("", "   ", None):
            with self.subTest(provenance=provenance):
                with self.assertRaisesRegex(ValueError, "non-empty"):
                    compute_saturn_arrival_to_staging(
                        NOMINAL_V_INFINITY_M_S,
                        NOMINAL_PERIAPSIS_RADIUS_M,
                        periapsis_radius_provenance=provenance,
                    )


class TestSaturnArrivalStagingAdapter(unittest.TestCase):
    def test_adapter_uses_existing_leg_trajectory_and_event_types(self):
        result = nominal_result()
        capture_epoch = 12_537.181818181829
        leg = adapt_saturn_arrival_staging_to_leg(result, capture_epoch_mjd2000=capture_epoch)

        self.assertIsInstance(leg, Leg)
        self.assertEqual((leg.origin, leg.destination), ("Saturn", "Saturn"))
        self.assertIsInstance(leg.trajectory, TrajectoryResult)
        trajectory = leg.trajectory
        assert trajectory is not None
        self.assertEqual(trajectory.departure_mjd2000, capture_epoch)
        self.assertAlmostEqual(
            trajectory.arrival_mjd2000,
            capture_epoch + result.time_of_flight_days,
            delta=1e-12,
        )
        self.assertIsNone(trajectory.v_inf_depart)
        self.assertEqual(trajectory.v_inf_arrival, result.arrival_v_infinity_m_s)
        self.assertEqual(trajectory.delta_v, result.total_delta_v_m_s)
        self.assertEqual(trajectory.method, result.method)
        self.assertEqual([event.event_type for event in leg.events], ["capture", "insertion"])
        self.assertEqual(leg.events[0].epoch, trajectory.departure_mjd2000)
        self.assertEqual(leg.events[1].epoch, trajectory.arrival_mjd2000)

    def test_adapter_without_epoch_preserves_unknown_event_times(self):
        leg = adapt_saturn_arrival_staging_to_leg(nominal_result())

        assert leg.trajectory is not None
        self.assertIsNone(leg.trajectory.departure_mjd2000)
        self.assertIsNone(leg.trajectory.arrival_mjd2000)
        self.assertTrue(all(event.epoch is None for event in leg.events))

    def test_adapter_rejects_wrong_result_and_invalid_epoch(self):
        with self.assertRaisesRegex(TypeError, "SaturnArrivalStagingResult"):
            adapt_saturn_arrival_staging_to_leg(object())
        with self.assertRaisesRegex(ValueError, "finite"):
            adapt_saturn_arrival_staging_to_leg(nominal_result(), capture_epoch_mjd2000=math.nan)


if __name__ == "__main__":
    unittest.main()
