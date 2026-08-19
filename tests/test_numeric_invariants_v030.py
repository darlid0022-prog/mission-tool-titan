"""VALUE-level numeric invariants for the reference Earth-Saturn-Titan mission.

DO NOT MERGE THIS FILE WITH tests/test_display_format_v030.py.

The two files test different things and must stay separate:

- THIS file asserts on the raw floats returned by the scientific/business
  models (app_services.compute_mission_bundle, mission.gravity_assist),
  called directly with no Streamlit rendering involved. These are the
  audited physical invariants (see docs/audit_science_budget_v030.md): they
  must NEVER change silently. A red test here means either a real
  regression or a deliberate, documented physical/scientific decision - not
  a wording or formatting change. If you are here to fix a display string,
  you are in the wrong file: go to test_display_format_v030.py instead.

- test_display_format_v030.py asserts on RENDERED STRINGS (what a user
  actually sees). It is expected to evolve whenever display policy changes
  (rounding, thousands separators, wording) - every such change must still
  be justified in its own commit message, but it is not a sign of a
  regression the way a change here would be.

Merging these two files back together recreates the exact problem this
split fixes: a test that breaks on every presentation change without ever
being the thing that actually guards the physics.
"""

import math
import unittest

import pandas as pd
from datetime import date

import app_services
from mission.constants import F_RING_REFERENCE_RADIUS_M
from mission.gravity_assist import (
    compute_earth_flyby_demonstration,
    compute_jupiter_flyby_demonstration,
    compute_venus_flyby_demonstration,
)
from mission.ui_presentation import build_lambert_departure_presentation


def _instruments_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Instrument": "Science payload (aggregate)",
                "Cible": "Orbiter",
                "Masse (kg)": 143.5,
                "Puissance (W)": 323.0,
                "Débit (bps)": 0.0,
            }
        ]
    )


def _reference_inputs(**overrides) -> app_services.MissionSetupInputs:
    """The audited Earth -> Saturn -> Titan baseline (docs/audit_science_budget_v030.md).

    Real (unmocked) Lambert solve - deliberately not going through
    compute_cached_trajectory mocks, so these assertions exercise the exact
    same code path the running application uses.
    """
    fields = dict(
        destination="Saturn",
        selected_moon="Titan",
        departure_type="LEO",
        leo_altitude_km=250.0,
        saturn_periapsis_radius_km=62_330.0,
        saturn_staging_radius_km=600_000.0,
        titan_capture_altitude_km=1_500.0,
        launch_window_start=date(2026, 6, 1),
        launch_window_end=date(2027, 6, 1),
        isp_s=320.0,
        instruments_df=_instruments_df(),
    )
    fields.update(overrides)
    return app_services.MissionSetupInputs(**fields)


class TestConnectedBudgetInvariants(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bundle = app_services.compute_mission_bundle(_reference_inputs())
        cls.budget = cls.bundle.complete_dv_budget

    def test_earth_departure_injection(self) -> None:
        self.assertAlmostEqual(self.budget.earth_departure_m_s, 7_381.480, places=3)

    def test_dsm_flyby_is_zero_and_explicitly_modeled(self) -> None:
        # This is not a missing value: the connected architecture models no
        # DSM/fly-by maneuver, so the term is a real, present, exact zero -
        # not an absent/None field. See §2.1 of the wording-and-scope batch.
        self.assertIn("dsm_flyby_m_s", vars(self.budget))
        self.assertEqual(self.budget.dsm_flyby_m_s, 0.0)

    def test_saturn_capture_to_ellipse(self) -> None:
        self.assertAlmostEqual(self.budget.saturn_capture_to_ellipse_m_s, 2_182.991, places=3)

    def test_saturn_circularization(self) -> None:
        self.assertAlmostEqual(
            self.budget.saturn_staging_circularisation_m_s, 2_966.182, places=3
        )

    def test_saturn_subtotal(self) -> None:
        subtotal = (
            self.budget.saturn_capture_to_ellipse_m_s
            + self.budget.saturn_staging_circularisation_m_s
        )
        self.assertAlmostEqual(subtotal, 5_149.173, places=3)

    def test_sum_of_the_four_connected_terms_equals_the_connected_total(self) -> None:
        # The DSM/fly-by term is included in this sum as a real 0.0, not
        # skipped - the reader can redo this exact sum from the four rows
        # shown in the Budget/Mission-setup maneuver table.
        four_term_sum = (
            self.budget.earth_departure_m_s
            + self.budget.dsm_flyby_m_s
            + self.budget.saturn_capture_to_ellipse_m_s
            + self.budget.saturn_staging_circularisation_m_s
        )
        self.assertAlmostEqual(four_term_sum, 12_530.653, places=3)
        self.assertAlmostEqual(self.budget.total_m_s, 12_530.653, places=3)
        self.assertAlmostEqual(self.bundle.dv_total, 12_530.653, places=3)


class TestDepartureConditionInvariants(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bundle = app_services.compute_mission_bundle(_reference_inputs())
        cls.departure = build_lambert_departure_presentation(cls.bundle.earth_saturn_trajectory)

    def test_earth_c3(self) -> None:
        self.assertAlmostEqual(self.departure.c3_m2_s2 / 1_000_000.0, 108.83, places=2)

    def test_earth_v_infinity(self) -> None:
        self.assertAlmostEqual(self.departure.earth_v_infinity_m_s, 10_432.306, places=3)

    def test_saturn_arrival_v_infinity(self) -> None:
        self.assertAlmostEqual(
            self.bundle.connected_first_order.arrival_v_infinity_m_s, 6_490.745, places=3
        )


class TestSaturnHyperbolaAndCaptureInvariants(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bundle = app_services.compute_mission_bundle(_reference_inputs())
        cls.connected = cls.bundle.connected_first_order

    def test_hyperbola_eccentricity(self) -> None:
        self.assertAlmostEqual(self.connected.saturn_hyperbola.eccentricity, 1.167, places=3)

    def test_hyperbola_deflection_angle_degrees(self) -> None:
        angle_deg = math.degrees(self.connected.saturn_hyperbola.turn_angle_rad)
        self.assertAlmostEqual(angle_deg, 118.0, places=1)

    def test_f_ring_margin(self) -> None:
        margin_m = self.connected.saturn_hyperbola.periapsis_radius_m - F_RING_REFERENCE_RADIUS_M
        self.assertAlmostEqual(margin_m / 1_000.0, 9_820.0, places=0)

    def test_capture_ellipse_eccentricity(self) -> None:
        self.assertAlmostEqual(self.connected.saturn_capture.eccentricity, 0.781, places=3)

    def test_capture_ellipse_time_of_flight_days(self) -> None:
        self.assertAlmostEqual(
            self.connected.saturn_capture.time_of_flight_days, 3.354, places=3
        )


class TestDurationInvariants(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bundle = app_services.compute_mission_bundle(_reference_inputs())

    def test_interplanetary_leg_days(self) -> None:
        traj = self.bundle.earth_saturn_trajectory
        interplanetary_days = float(traj.arrival_mjd2000) - float(traj.departure_mjd2000)
        self.assertAlmostEqual(interplanetary_days, 2_856.0, places=1)

    def test_saturn_phase_days(self) -> None:
        self.assertAlmostEqual(
            self.bundle.connected_first_order.saturn_capture.time_of_flight_days,
            3.354,
            places=3,
        )

    def test_total_reference_scenario_duration_days(self) -> None:
        self.assertAlmostEqual(self.bundle.mission_duration_days, 2_859.354, places=3)


class TestMassInvariants(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bundle = app_services.compute_mission_bundle(_reference_inputs())

    def test_mass_ratio(self) -> None:
        self.assertAlmostEqual(self.bundle.mass_ratio, 54.22, places=2)

    def test_dry_mass_kg(self) -> None:
        self.assertAlmostEqual(self.bundle.mass["dry_mass_kg"], 223.86, places=1)

    def test_propellant_mass_kg(self) -> None:
        self.assertAlmostEqual(self.bundle.mass["propellant_mass_kg"], 11_913.64, places=1)

    def test_wet_mass_kg(self) -> None:
        self.assertAlmostEqual(self.bundle.mass["wet_mass_kg"], 12_137.50, places=1)


class TestSingleStageFeasibilityInvariants(unittest.TestCase):
    """Also proves criterion 4 of the wording-and-scope batch (§2.4): the
    calibrated single-stage study receives the CONNECTED total, never the
    Saturn-only subtotal - see app_services.py:551-553 (and the identical
    pattern at 582-584, 631-633) and mission/dv_budget.py:24-26."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.bundle = app_services.compute_mission_bundle(_reference_inputs())
        cls.feasibility = cls.bundle.single_stage_feasibility

    def test_required_delta_v_is_the_connected_total_not_the_saturn_subtotal(self) -> None:
        self.assertAlmostEqual(
            self.feasibility.required_delta_v_m_s, 12_530.653, places=3
        )
        self.assertNotAlmostEqual(
            self.feasibility.required_delta_v_m_s, 5_149.173, places=0
        )

    def test_maximum_feasible_delta_v(self) -> None:
        self.assertAlmostEqual(
            self.feasibility.maximum_feasible_delta_v_m_s, 3_833.463, places=3
        )

    def test_threshold_exceedance_factor(self) -> None:
        self.assertAlmostEqual(self.feasibility.threshold_exceedance_factor, 3.269, places=3)

    def test_allocation_bracket_launcher_bound_value(self) -> None:
        # The launcher-bound figure from §2.2 of the previous batch
        # (5,149.173 / 3,833.463): confined to the isolated study, this file
        # only proves the VALUE - test_display_format_v030.py proves it does
        # not leak onto Budget/Mission setup/Verdict.
        saturn_subtotal = (
            self.bundle.complete_dv_budget.saturn_capture_to_ellipse_m_s
            + self.bundle.complete_dv_budget.saturn_staging_circularisation_m_s
        )
        launcher_bound = saturn_subtotal / self.feasibility.maximum_feasible_delta_v_m_s
        self.assertAlmostEqual(launcher_bound, 1.343, places=3)


class TestLegacyStagingInvariants(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bundle = app_services.compute_mission_bundle(_reference_inputs())
        cls.staging = cls.bundle.staging_result

    def test_capture_to_ellipse_delta_v(self) -> None:
        self.assertAlmostEqual(self.staging.capture_to_ellipse_delta_v_m_s, 2_280.8, places=1)

    def test_staging_circularisation_delta_v(self) -> None:
        self.assertAlmostEqual(
            self.staging.staging_circularisation_delta_v_m_s, 4_501.6, places=1
        )

    def test_staging_total_delta_v(self) -> None:
        self.assertAlmostEqual(self.staging.total_delta_v_m_s, 6_782.4, places=1)

    def test_staging_time_of_flight_days(self) -> None:
        self.assertAlmostEqual(self.staging.time_of_flight_days, 1.125, places=3)


class TestSaturnToTitanInvariants(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bundle = app_services.compute_mission_bundle(_reference_inputs())
        cls.transfer = cls.bundle.titan_transfer

    def test_departure_delta_v(self) -> None:
        self.assertAlmostEqual(self.transfer.departure_delta_v_m_s, 1_257.5, places=1)

    def test_v_infinity_titan(self) -> None:
        self.assertAlmostEqual(self.transfer.v_infinity_titan_m_s, 1_049.8, places=1)

    def test_capture_delta_v(self) -> None:
        self.assertAlmostEqual(self.transfer.capture_delta_v_m_s, 862.7, places=1)

    def test_total_delta_v(self) -> None:
        self.assertAlmostEqual(self.transfer.total_delta_v_m_s, 2_120.3, places=1)

    def test_time_of_flight_days(self) -> None:
        self.assertAlmostEqual(self.transfer.time_of_flight_days, 5.133, places=3)


class TestTitanEdlInvariants(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bundle = app_services.compute_mission_bundle(_reference_inputs())
        cls.edl = cls.bundle.titan_edl

    def test_entry_interface_velocity(self) -> None:
        self.assertAlmostEqual(self.edl.entry_velocity_m_s, 2_402.6, places=1)

    def test_atmospheric_velocity_reduction(self) -> None:
        self.assertAlmostEqual(self.edl.atmospheric_velocity_reduction_m_s, 2_002.6, places=1)

    def test_estimated_deployment_altitude(self) -> None:
        self.assertAlmostEqual(
            self.edl.estimated_parachute_deployment_altitude_m / 1_000.0, 151.2, places=1
        )


class TestFlybyDemonstratorInvariants(unittest.TestCase):
    """Also covers the physical bound every unpowered flyby must respect:
    heliocentric_speed_change_m_s <= 2 * v_infinity * sin(turn_angle / 2)."""

    def _assert_within_physical_bound(self, result) -> None:
        bound = 2.0 * result.v_infinity_magnitude_m_s * math.sin(result.turn_angle_rad / 2.0)
        self.assertLessEqual(result.heliocentric_speed_change_m_s, bound + 1e-6)

    def test_venus_turn_angle_and_heliocentric_gain(self) -> None:
        result = compute_venus_flyby_demonstration()
        self.assertAlmostEqual(math.degrees(result.turn_angle_rad), 72.003, places=3)
        self.assertAlmostEqual(result.heliocentric_speed_change_m_s, 3_591.9, places=1)
        self._assert_within_physical_bound(result)

    def test_earth_turn_angle_and_heliocentric_gain(self) -> None:
        result = compute_earth_flyby_demonstration()
        self.assertAlmostEqual(math.degrees(result.turn_angle_rad), 19.677, places=3)
        self.assertAlmostEqual(result.heliocentric_speed_change_m_s, 4_181.3, places=1)
        self._assert_within_physical_bound(result)

    def test_jupiter_turn_angle_and_heliocentric_gain(self) -> None:
        result = compute_jupiter_flyby_demonstration()
        self.assertAlmostEqual(math.degrees(result.turn_angle_rad), 11.780, places=3)
        self.assertAlmostEqual(result.heliocentric_speed_change_m_s, 2_040.9, places=1)
        self._assert_within_physical_bound(result)


if __name__ == "__main__":
    unittest.main()
