import unittest
import unittest.mock
from datetime import date

import pandas as pd

import app_services
import trajectory
from tests.test_app_titan_ui import earth_saturn_leg, earth_saturn_result

DEFAULT_LAUNCH_WINDOW_START = date(2026, 6, 1)
DEFAULT_LAUNCH_WINDOW_END = date(2027, 6, 1)


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


def _connected_titan_inputs(**overrides) -> app_services.MissionSetupInputs:
    """The default, pre-existing Earth -> Saturn -> Titan setup this task must not change."""
    fields = dict(
        destination="Saturn",
        selected_moon="Titan",
        departure_type="LEO",
        leo_altitude_km=250.0,
        saturn_periapsis_radius_km=62_330.0,
        saturn_staging_radius_km=600_000.0,
        titan_capture_altitude_km=1_500.0,
        launch_window_start=DEFAULT_LAUNCH_WINDOW_START,
        launch_window_end=DEFAULT_LAUNCH_WINDOW_END,
        isp_s=320.0,
        instruments_df=_instruments_df(),
    )
    fields.update(overrides)
    return app_services.MissionSetupInputs(**fields)


class TestDirectTrajectoryTypeIsUnchanged(unittest.TestCase):
    """Non-regression: adding trajectory_type must not change the pre-existing
    Direct-mode bundle in any way - it is a new opt-in mode, not a replacement."""

    def setUp(self):
        app_services.compute_cached_trajectory.clear()
        self.patcher = unittest.mock.patch(
            "app_services.compute_cached_trajectory",
            return_value=earth_saturn_result(),
        )
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def test_omitting_trajectory_type_defaults_to_direct(self):
        inputs = _connected_titan_inputs()
        self.assertEqual(inputs.trajectory_type, app_services.TRAJECTORY_TYPE_DIRECT)

    def test_explicit_direct_matches_omitted_trajectory_type_exactly(self):
        implicit_bundle = app_services.compute_mission_bundle(_connected_titan_inputs())
        explicit_bundle = app_services.compute_mission_bundle(
            _connected_titan_inputs(trajectory_type=app_services.TRAJECTORY_TYPE_DIRECT)
        )

        self.assertEqual(implicit_bundle.dv_total, explicit_bundle.dv_total)
        self.assertEqual(
            implicit_bundle.mission_duration_days, explicit_bundle.mission_duration_days
        )
        self.assertEqual(implicit_bundle.complete_dv_budget, explicit_bundle.complete_dv_budget)
        self.assertIsNone(implicit_bundle.cassini_tour)
        self.assertIsNone(explicit_bundle.cassini_tour)

    def test_direct_mode_matches_the_consolidated_first_order_reference(self):
        """Pin the new non-redundant analytical chain and its duration."""
        bundle = app_services.compute_mission_bundle(_connected_titan_inputs())

        self.assertAlmostEqual(bundle.dv_total, 12_163.278277912983, delta=1e-3)
        self.assertAlmostEqual(bundle.mission_duration_days, 2_211.759761484366, delta=1e-3)
        self.assertIsNotNone(bundle.staging_result)
        self.assertIsNotNone(bundle.titan_transfer)
        self.assertIsNotNone(bundle.connected_first_order)
        self.assertIsNone(bundle.cassini_tour)


class TestCassiniHistoricalBundle(unittest.TestCase):
    def setUp(self):
        app_services.compute_cached_trajectory.clear()
        self.patcher = unittest.mock.patch(
            "app_services.compute_cached_trajectory",
            return_value=earth_saturn_result(),
        )
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def _historical_inputs(self, **overrides) -> app_services.MissionSetupInputs:
        return _connected_titan_inputs(
            trajectory_type=app_services.TRAJECTORY_TYPE_CASSINI_HISTORICAL,
            **overrides,
        )

    def test_available_regardless_of_moon_selection(self):
        for selected_moon in (None, "Titan"):
            with self.subTest(selected_moon=selected_moon):
                bundle = app_services.compute_mission_bundle(
                    self._historical_inputs(selected_moon=selected_moon)
                )
                self.assertEqual(len(bundle.cassini_tour), 5)

    def test_bundle_carries_the_real_tour_not_a_lambert_solve(self):
        bundle = app_services.compute_mission_bundle(self._historical_inputs())

        self.assertIsNotNone(bundle.cassini_tour)
        self.assertEqual(len(bundle.cassini_tour), 5)
        self.assertIsNone(bundle.staging_result)
        self.assertIsNone(bundle.titan_transfer)
        self.assertIsNone(bundle.titan_edl)

    def test_delta_v_is_departure_injection_plus_soi_only(self):
        bundle = app_services.compute_mission_bundle(self._historical_inputs())
        budget = bundle.complete_dv_budget

        soi_result = bundle.cassini_tour[-1].result
        self.assertGreater(budget.earth_departure_m_s, 0.0)
        self.assertAlmostEqual(
            budget.saturn_capture_to_ellipse_m_s, soi_result.delta_v_m_s, delta=1e-6
        )
        self.assertEqual(budget.dsm_flyby_m_s, 0.0)
        self.assertEqual(budget.saturn_staging_circularisation_m_s, 0.0)
        self.assertEqual(budget.saturn_titan_departure_m_s, 0.0)
        self.assertEqual(budget.titan_capture_m_s, 0.0)
        self.assertAlmostEqual(
            bundle.dv_total,
            budget.earth_departure_m_s + soi_result.delta_v_m_s,
            delta=1e-6,
        )

    def test_mission_duration_is_the_real_1997_2004_cruise(self):
        bundle = app_services.compute_mission_bundle(self._historical_inputs())

        # Independent of the (mocked, irrelevant-for-this-mode) launch window
        # the mocked earth_saturn_result() implies.
        self.assertAlmostEqual(bundle.mission_duration_days / 365.25, 6.7, delta=0.1)

    def test_ignores_the_departure_type_and_launch_window_inputs(self):
        with_leo = app_services.compute_mission_bundle(
            self._historical_inputs(departure_type="LEO", leo_altitude_km=250.0)
        )
        different_window = app_services.compute_mission_bundle(
            self._historical_inputs(
                launch_window_start=date(2030, 1, 1),
                launch_window_end=date(2031, 1, 1),
            )
        )
        self.assertEqual(with_leo.dv_total, different_window.dv_total)
        self.assertEqual(with_leo.mission_duration_days, different_window.mission_duration_days)


class TestCassiniHistoricalIsCheaperThanDirect(unittest.TestCase):
    """The whole physical point of the tour: unpowered flybys let Cassini reach
    Saturn for meaningfully less delta-v than a direct Earth -> Saturn transfer.
    Real (unmocked) computations on both sides - no mocks."""

    def test_historical_total_delta_v_is_significantly_lower_than_direct(self):
        historical_bundle = app_services.compute_mission_bundle(
            app_services.MissionSetupInputs(
                destination="Saturn",
                selected_moon=None,
                departure_type="LEO",
                leo_altitude_km=250.0,
                saturn_periapsis_radius_km=62_330.0,
                saturn_staging_radius_km=600_000.0,
                titan_capture_altitude_km=1_500.0,
                launch_window_start=DEFAULT_LAUNCH_WINDOW_START,
                launch_window_end=DEFAULT_LAUNCH_WINDOW_END,
                isp_s=320.0,
                instruments_df=_instruments_df(),
                trajectory_type=app_services.TRAJECTORY_TYPE_CASSINI_HISTORICAL,
            )
        )

        # Compared against trajectory.compute_trajectory()'s own dv_total
        # (departure injection + arrival capture) rather than
        # compute_mission_bundle()'s planet-only branch: that branch only
        # carries the departure/DSM terms of the raw Lambert budget over into
        # MissionBundle.complete_dv_budget today (a pre-existing gap, not
        # something this task touches) and would understate the real direct
        # total, making this comparison meaningless.
        direct_result = trajectory.compute_trajectory(
            "Saturn",
            "LEO",
            DEFAULT_LAUNCH_WINDOW_START,
            DEFAULT_LAUNCH_WINDOW_END,
            False,
            False,
            False,
            0.0,
            250.0,
            2_000.0,
        )
        direct_total_m_s = direct_result["dv_total"]

        self.assertGreater(historical_bundle.dv_total, 0.0)
        self.assertGreater(direct_total_m_s, 0.0)
        self.assertLess(historical_bundle.dv_total, 0.75 * direct_total_m_s)


if __name__ == "__main__":
    unittest.main()
