import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

from app_services import (
    MISSION_SETUP_STATE_KEY,
    MissionSetupInputs,
    decode_mission_setup_query,
    encode_mission_setup_query,
)
from mission import physics
from mission.bodies import resolve_body
from mission.models import Leg, TrajectoryResult
from mission.pareto import compute_connected_pareto_front
from mission.pareto_plot import build_pareto_front_figure
from mission.trajectory_visualization import (
    CompleteMissionScene3D,
    MissionAnimationTimeline3D,
)

APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


def earth_saturn_leg() -> Leg:
    return Leg(
        origin="Earth",
        destination="Saturn",
        trajectory=TrajectoryResult(
            departure_mjd2000=9_681.181818181818,
            arrival_mjd2000=12_537.181818181829,
            tof_years=7.82,
            v_inf_depart=10_432.306468285773,
            v_inf_arrival=6_490.744714263188,
            method="lambert",
        ),
    )


def earth_saturn_result() -> dict:
    return {
        "note": "Test Earth-to-Saturn result",
        "dv_budget": {
            "dV from LEO": 1_000.0,
            "dV DSM/Fly-By": 0.0,
            "dV Capture at Destination": 999_999.0,
        },
        "dv_total": 1_000.0,
        "earth_saturn_leg": earth_saturn_leg(),
    }


def run_app(page_path: str | None = None, animation_phase: str | None = None) -> AppTest:
    """Run app.py (its default Mission setup page), optionally switching pages after.

    Every page rebuilds its results from the mission-setup inputs stored in
    st.session_state during the initial run, so the trajectory mock only needs
    to be active while that first run executes the form.
    """
    app = AppTest.from_file(APP_PATH)
    if animation_phase is not None:
        app.session_state["mission_animation_phase"] = animation_phase
        app.session_state["mission_phase_elapsed_days"] = 0.0
    with patch(
        "app_services.compute_cached_trajectory",
        return_value=earth_saturn_result(),
    ):
        app.run(timeout=30)
        if page_path is not None:
            app.switch_page(page_path).run(timeout=30)
    return app


def badge_values(app: AppTest) -> list[str]:
    """Read back rendered st.badge() elements as `:{color}-badge[{label}]` strings.

    st.badge isn't yet queryable via AppTest's typed accessors in this
    Streamlit version - it renders as this markdown directive under the hood,
    so this reads it back off the plain markdown elements instead.
    """
    return [markdown.value for markdown in app.markdown if "-badge[" in markdown.value]


class TestMissionSetupPage(unittest.TestCase):
    def test_trajectory_type_choice_defaults_to_direct_for_saturn(self):
        app = run_app()

        self.assertFalse(app.exception)
        trajectory_type_radio = next(
            radio for radio in app.radio if radio.label == "Trajectory type"
        )
        self.assertEqual(
            list(trajectory_type_radio.options),
            ["Direct", "Cassini historical gravity assist"],
        )
        self.assertEqual(trajectory_type_radio.value, "Direct")

    def test_selecting_the_historical_trajectory_type_updates_the_scorecard(self):
        app = AppTest.from_file(APP_PATH)
        with patch(
            "app_services.compute_cached_trajectory",
            return_value=earth_saturn_result(),
        ):
            app.run(timeout=30)
            trajectory_type_radio = next(
                radio for radio in app.radio if radio.label == "Trajectory type"
            )
            trajectory_type_radio.set_value("Cassini historical gravity assist")
            next(button for button in app.button if "Calculate" in button.label).click().run(
                timeout=30
            )

        self.assertFalse(app.exception)
        metrics = {metric.label: metric.value for metric in app.metric}
        # Real historical total (Earth-departure injection + SOI capture only),
        # not the mocked earth_saturn_result()'s connected-chain total.
        self.assertNotEqual(metrics["Connected delta-v"], "9,903 m/s")
        self.assertTrue(
            any(
                "Historical Cassini-style gravity-assist trajectory" in info.value
                for info in app.info
            )
        )

    @staticmethod
    def shared_inputs() -> MissionSetupInputs:
        return MissionSetupInputs(
            destination="Saturn",
            selected_moon="Titan",
            departure_type="LEO",
            leo_altitude_km=300.0,
            saturn_periapsis_radius_km=62_500.0,
            saturn_staging_radius_km=610_000.0,
            titan_capture_altitude_km=1_600.0,
            launch_window_start=date(2026, 7, 1),
            launch_window_end=date(2027, 5, 1),
            isp_s=340.0,
            instruments_df=pd.DataFrame(
                [
                    {
                        "Instrument": "Shared payload",
                        "Cible": "Orbiter",
                        "Masse (kg)": 150.0,
                        "Puissance (W)": 350.0,
                        "Débit (bps)": 1_024.0,
                    }
                ]
            ),
        )

    def test_connected_total_and_default_mass_outputs_are_non_zero(self):
        app = run_app()

        self.assertFalse(app.exception)
        metrics = {metric.label: metric.value for metric in app.metric}
        self.assertEqual(metrics["Sum of budgeted delta-v values"], "12163 m/s")
        for label in (
            "Simplified dry mass",
            "Simplified propellant mass",
            "Simplified total wet mass",
        ):
            self.assertNotEqual(metrics[label], "0.0 kg", msg=label)
        self.assertFalse(
            any(widget.label == "Saturn capture altitude (km)" for widget in app.number_input)
        )
        self.assertTrue(
            any(
                "does not couple propulsion hardware mass to propellant mass" in warning.value
                for warning in app.warning
            )
        )

    def test_phase_color_key_lists_all_five_phases_in_chronological_order(self):
        app = run_app()

        self.assertFalse(app.exception)
        self.assertEqual(
            badge_values(app),
            [
                ":orange-badge[Launch]",
                ":blue-badge[Interplanetary transfer]",
                ":green-badge[Arrival / orbit insertion]",
                ":violet-badge[Lunar transfer]",
                ":red-badge[Landing]",
            ],
        )

    def test_scorecard_displays_live_connected_results(self):
        app = run_app()

        self.assertFalse(app.exception)
        metrics = {metric.label: metric.value for metric in app.metric}
        self.assertEqual(metrics["Connected delta-v"], "12,163 m/s")
        self.assertEqual(metrics["Wet mass (simplified)"], "10,797 kg")
        self.assertEqual(metrics["Duration to Titan"], "2,211.8 days")
        self.assertEqual(metrics["Single-stage exceedance"], "3.17×")
        self.assertEqual(metrics["Flyby gain coverage"], "117.8%")

    def test_summary_exposes_share_and_pdf_actions(self):
        app = run_app()

        self.assertFalse(app.exception)
        self.assertTrue(any(button.label == "Copy share link" for button in app.button))
        self.assertTrue(
            any(button.label == "Download mission summary PDF" for button in app.download_button)
        )

    def test_shared_query_restores_inputs_before_the_default_page_renders(self):
        expected = self.shared_inputs()
        app = AppTest.from_file(APP_PATH)
        app.query_params.update(encode_mission_setup_query(expected))

        with patch("app_services.compute_cached_trajectory", return_value=earth_saturn_result()):
            app.run(timeout=30)

        self.assertFalse(app.exception)
        restored = app.session_state[MISSION_SETUP_STATE_KEY]
        self.assertEqual(restored.destination, expected.destination)
        self.assertEqual(restored.leo_altitude_km, expected.leo_altitude_km)
        self.assertEqual(restored.launch_window_start, expected.launch_window_start)
        self.assertEqual(restored.isp_s, expected.isp_s)
        self.assertEqual(restored.instruments_df.iloc[0]["Instrument"], "Shared payload")

    def test_copy_share_link_populates_a_decodable_query_parameter(self):
        app = AppTest.from_file(APP_PATH)
        with patch("app_services.compute_cached_trajectory", return_value=earth_saturn_result()):
            app.run(timeout=30)
            next(button for button in app.button if button.label == "Copy share link").click().run(
                timeout=30
            )

        self.assertFalse(app.exception)
        restored = decode_mission_setup_query(app.query_params)
        self.assertEqual(restored.destination, "Saturn")
        self.assertEqual(restored.selected_moon, "Titan")
        self.assertTrue(any("?mission=" in code.value for code in app.code))

    def test_complete_budget_is_connected_to_mass_sizing_without_legacy_capture(self):
        mass_result = {
            "instrument_mass_kg": 0.0,
            "dry_mass_kg": 1.0,
            "propellant_mass_kg": 0.0,
            "wet_mass_kg": 1.0,
        }
        with patch("app_services.compute_cached_trajectory") as trajectory_mock:
            trajectory_mock.return_value = earth_saturn_result()
            # Patched on app_services (where compute_mass_budget is imported and
            # called from compute_mission_bundle), not mission.sizing: Streamlit
            # only re-execs the active page script fresh each run, not regular
            # imported modules such as app_services, so a mission.sizing-level
            # patch would never be observed by the already-bound module global.
            with patch("app_services.compute_mass_budget", return_value=mass_result) as mass_mock:
                app = AppTest.from_file(APP_PATH).run(timeout=30)

        self.assertFalse(app.exception)
        self.assertEqual(trajectory_mock.call_count, 1)
        self.assertEqual(mass_mock.call_count, 1)
        instruments = mass_mock.call_args.args[2]
        self.assertEqual(len(instruments), 1)
        self.assertEqual(instruments.iloc[0]["Instrument"], "Science payload (aggregate)")
        self.assertEqual(instruments.iloc[0]["Masse (kg)"], 143.5)
        self.assertEqual(instruments.iloc[0]["Puissance (W)"], 323.0)
        expected_total = 12_163.278277912983
        self.assertAlmostEqual(mass_mock.call_args.args[0], expected_total, delta=1e-3)
        self.assertNotEqual(mass_mock.call_args.args[0], 1_000.0 + 999_999.0)

    def test_displayed_earth_departure_injection_equals_physics_output_exactly(self):
        from mission.connected_physics import compute_earth_saturn_hohmann

        v_inf_m_s = compute_earth_saturn_hohmann().departure_v_infinity_m_s
        leo_altitude_m = 250_000.0
        earth = resolve_body("Earth")
        expected_injection_m_s = physics.delta_v_injection(
            v_inf_m_s,
            earth.get_mu_self(),
            earth.pykep_body.get_radius() + leo_altitude_m,
        )
        result = {
            "note": "Test Earth-to-Saturn result",
            "dv_budget": {
                "dV from LEO": expected_injection_m_s,
                "dV DSM/Fly-By": 0.0,
                "dV Capture at Destination": 999_999.0,
            },
            "dv_total": expected_injection_m_s,
            "earth_saturn_leg": earth_saturn_leg(),
        }

        with patch(
            "app_services.compute_cached_trajectory", return_value=result
        ) as trajectory_mock:
            app = AppTest.from_file(APP_PATH).run(timeout=30)

        self.assertFalse(app.exception)
        departure_type = next(radio for radio in app.radio if radio.label == "Departure type")
        self.assertEqual(departure_type.value, "LEO")
        self.assertEqual(trajectory_mock.call_args.args[2], "LEO")
        budget_table = next(
            dataframe.value for dataframe in app.dataframe if "Maneuver" in dataframe.value.columns
        )
        displayed_injection_m_s = budget_table.loc[
            budget_table["Maneuver"] == "Earth departure injection",
            "Value (m/s)",
        ].iloc[0]
        self.assertEqual(displayed_injection_m_s, expected_injection_m_s)


class TestTrajectory3DPage(unittest.TestCase):
    def test_current_phase_badge_matches_the_default_selected_phase(self):
        app = run_app(page_path="pages/trajectory_3d.py")

        self.assertFalse(app.exception)
        # Default selected phase is "Earth → Saturn cruise" (interplanetary
        # transfer) - same color as its badge on every other page.
        self.assertEqual(badge_values(app), [":blue-badge[Interplanetary transfer]"])

    def test_chart_has_a_keyboard_accessible_data_table_alternative(self):
        app = run_app(page_path="pages/trajectory_3d.py")

        self.assertFalse(app.exception)
        expander = next(e for e in app.expander if e.label == "View trajectory data as a table")
        # st.expander is a native, keyboard-operable disclosure widget (no
        # mouse-only affordance) and its content, a plain st.dataframe, is
        # present in the tree regardless of the (collapsed-by-default) open
        # state - both are queryable here without simulating a click.
        table = expander.dataframe[0].value
        self.assertEqual(
            list(table.columns),
            ["Element", "Type", "Panel", "Point index", "x", "y", "z", "Unit"],
        )
        self.assertGreater(len(table), 0)

    def test_complete_trajectory_3d_view_is_rendered(self):
        app = run_app(page_path="pages/trajectory_3d.py")

        self.assertFalse(app.exception)
        self.assertTrue(
            any(
                heading.value == "Complete mission trajectory — interactive 3D view"
                for heading in app.header
            )
        )
        # Only this page's own chart is present now: other pages (e.g. the
        # Pareto front on Optimization) are separate script runs and no
        # longer share this run's element tree the way tabs used to.
        self.assertEqual(len(app.get("plotly_chart")), 1)
        self.assertTrue(
            any(
                control.label == "Mission phase" and control.value == "Earth → Saturn cruise"
                for control in app.segmented_control
            )
        )
        self.assertTrue(
            any(slider.label == "Elapsed time within selected phase" for slider in app.slider)
        )
        metrics = {metric.label: metric.value for metric in app.metric}
        self.assertEqual(metrics["Current mission-elapsed time"], "0.00 days")
        self.assertEqual(metrics["Current mission phase"], "Earth → Saturn cruise")

    def test_animation_slider_uses_selected_phase_duration(self):
        phase_duration_attributes = {
            "Earth → Saturn cruise": "earth_saturn_duration_days",
            "Saturn arrival → staging": "saturn_staging_duration_days",
            "Saturn → Titan": "saturn_titan_duration_days",
        }

        for phase, duration_attribute in phase_duration_attributes.items():
            with self.subTest(phase=phase):
                app = run_app(page_path="pages/trajectory_3d.py", animation_phase=phase)
                self.assertFalse(app.exception)
                timeline = app.session_state["trajectory_timeline"]
                slider = next(
                    slider
                    for slider in app.slider
                    if slider.label == "Elapsed time within selected phase"
                )
                self.assertEqual(slider.min, 0.0)
                self.assertEqual(slider.max, getattr(timeline, duration_attribute))
                metrics = {metric.label: metric.value for metric in app.metric}
                self.assertEqual(metrics["Current mission phase"], phase)

                expected_absolute_start = {
                    "Earth → Saturn cruise": 0.0,
                    "Saturn arrival → staging": timeline.earth_saturn_duration_days,
                    "Saturn → Titan": (
                        timeline.earth_saturn_duration_days + timeline.saturn_staging_duration_days
                    ),
                }[phase]
                self.assertEqual(
                    metrics["Current mission-elapsed time"],
                    f"{expected_absolute_start:,.2f} days",
                )

    def test_switching_animation_phase_resets_local_slider(self):
        app = AppTest.from_file(APP_PATH)
        with patch(
            "app_services.compute_cached_trajectory",
            return_value=earth_saturn_result(),
        ):
            app.run(timeout=30)
            app.switch_page("pages/trajectory_3d.py").run(timeout=30)
            phase_slider = next(
                slider
                for slider in app.slider
                if slider.label == "Elapsed time within selected phase"
            )
            phase_slider.set_value(100.0).run(timeout=30)
            self.assertEqual(phase_slider.value, 100.0)

            phase_selector = next(
                control for control in app.segmented_control if control.label == "Mission phase"
            )
            phase_selector.set_value("Saturn arrival → staging").run(timeout=30)

        phase_slider = next(
            slider for slider in app.slider if slider.label == "Elapsed time within selected phase"
        )
        self.assertEqual(phase_slider.value, 0.0)
        metrics = {metric.label: metric.value for metric in app.metric}
        timeline = app.session_state["trajectory_timeline"]
        self.assertEqual(metrics["Current mission phase"], "Saturn arrival → staging")
        self.assertEqual(
            metrics["Current mission-elapsed time"],
            f"{timeline.earth_saturn_duration_days:,.2f} days",
        )

    def test_stale_animation_objects_are_rebuilt_after_module_reload(self):
        app = AppTest.from_file(APP_PATH)
        with patch(
            "app_services.compute_cached_trajectory",
            return_value=earth_saturn_result(),
        ):
            app.run(timeout=30)
            app.switch_page("pages/trajectory_3d.py").run(timeout=30)
            app.session_state["trajectory_scene"] = object()
            app.session_state["trajectory_timeline"] = object()
            app.run(timeout=30)

        self.assertFalse(app.exception)
        self.assertIsInstance(
            app.session_state["trajectory_scene"],
            CompleteMissionScene3D,
        )
        self.assertIsInstance(
            app.session_state["trajectory_timeline"],
            MissionAnimationTimeline3D,
        )


class TestSaturnSystemStudiesPage(unittest.TestCase):
    def test_each_section_carries_its_own_mission_phase_badge(self):
        app = run_app(page_path="pages/saturn_system_studies.py")

        self.assertFalse(app.exception)
        self.assertEqual(
            badge_values(app),
            [
                ":green-badge[Arrival / orbit insertion]",
                ":violet-badge[Lunar transfer]",
                ":red-badge[Landing]",
            ],
        )

    def test_arrival_to_staging_section_displays_nominal_results_and_ring_status(self):
        app = run_app(page_path="pages/saturn_system_studies.py")

        self.assertFalse(app.exception)
        self.assertTrue(
            any(
                heading.value == "Saturn arrival → staging orbit — preliminary model"
                for heading in app.header
            )
        )
        metrics = {metric.label: metric.value for metric in app.metric}
        self.assertEqual(metrics["Capture-to-ellipse delta-v"], "2,280.8 m/s")
        self.assertEqual(metrics["Staging circularization delta-v"], "4,501.6 m/s")
        self.assertEqual(metrics["Arrival-to-staging total delta-v"], "6,782.4 m/s")
        self.assertEqual(metrics["Periapsis-to-apoapsis time"], "1.125 days")
        self.assertEqual(metrics["Periapsis below D-ring inner edge"], "4,570 km")
        self.assertEqual(metrics["Staging orbit beyond E-ring edge"], "+118,000 km")
        self.assertTrue(
            any(
                "Planet–ring corridor at periapsis" in warning.value
                and "Cassini's 2017 Grand Finale" in warning.value
                and "three-dimensional ring-plane geometry" in warning.value
                for warning in app.warning
            )
        )

    def test_preliminary_section_displays_nominal_results_and_source(self):
        app = run_app(page_path="pages/saturn_system_studies.py")

        self.assertFalse(app.exception)
        self.assertTrue(
            any(heading.value == "Saturn → Titan — preliminary model" for heading in app.header)
        )
        metrics = {metric.label: metric.value for metric in app.metric}
        self.assertEqual(metrics["Departure delta-v from staging orbit"], "1,257.5 m/s")
        self.assertEqual(metrics["Titan-relative v∞ (non-propulsive)"], "1,049.8 m/s")
        self.assertEqual(metrics["Titan capture delta-v"], "862.7 m/s")
        self.assertEqual(metrics["Saturn → Titan modeled delta-v"], "2,120.3 m/s")
        self.assertEqual(metrics["Saturn → Titan time of flight"], "5.133 days")
        self.assertTrue(any("JPL SAT441" in caption.value for caption in app.caption))

    def test_isolated_titan_edl_section_displays_direct_entry_without_budget_change(self):
        app = run_app(page_path="pages/saturn_system_studies.py")

        self.assertFalse(app.exception)
        self.assertTrue(
            any(
                heading.value == "Titan EDL — preliminary ballistic-entry model"
                for heading in app.header
            )
        )
        metrics = {metric.label: metric.value for metric in app.metric}
        self.assertEqual(metrics["Atmospheric-interface entry velocity"], "2,402.6 m/s")
        self.assertEqual(metrics["Estimated deployment altitude"], "151.2 km")
        self.assertEqual(metrics["Avoided circular-capture burn"], "862.7 m/s")
        self.assertTrue(
            any(
                "not included in the connected delta-v or mass budget" in warning.value
                for warning in app.warning
            )
        )


class TestFeasibilityPage(unittest.TestCase):
    def test_single_stage_feasibility_is_displayed_as_a_finding_without_crashing(self):
        app = run_app(page_path="pages/feasibility.py")

        self.assertFalse(app.exception)
        self.assertTrue(
            any(
                heading.value == "Single-stage chemical feasibility — preliminary model"
                for heading in app.header
            )
        )
        metrics = {metric.label: metric.value for metric in app.metric}
        self.assertEqual(metrics["Required connected delta-v"], "12,163.278 m/s")
        self.assertEqual(metrics["Maximum feasible single-stage delta-v"], "3,833.463 m/s")
        self.assertEqual(metrics["Required / feasible threshold"], "3.173×")
        self.assertTrue(
            any(
                "This is a model finding, not an application error" in info.value
                for info in app.info
            )
        )


class TestOptimizationPage(unittest.TestCase):
    def test_chart_has_a_keyboard_accessible_data_table_alternative(self):
        app = run_app(page_path="pages/optimization.py")

        self.assertFalse(app.exception)
        expander = next(e for e in app.expander if e.label == "View Pareto front data as a table")
        table = expander.dataframe[0].value
        self.assertEqual(
            list(table.columns),
            [
                "Role",
                "Total delta-v (m/s)",
                "Total duration (days)",
                "Wet mass (kg)",
                "Earth → Saturn TOF (days)",
                "Earth departure date",
                "Departure MJD2000",
            ],
        )
        self.assertEqual(len(table), 35)

    def test_pareto_chart_renders_38_front_points_and_highlights_references(self):
        pareto_result = compute_connected_pareto_front()
        captured = {}

        def capture_figure(result):
            figure = build_pareto_front_figure(result)
            captured["figure"] = figure
            return figure

        with (
            patch(
                "app_services.compute_cached_trajectory",
                return_value=earth_saturn_result(),
            ),
            patch(
                "app_services.compute_cached_pareto_front",
                return_value=pareto_result,
            ),
            patch(
                "mission.pareto_plot.build_pareto_front_figure",
                side_effect=capture_figure,
            ),
        ):
            app = AppTest.from_file(APP_PATH)
            app.run(timeout=30)
            app.switch_page("pages/optimization.py").run(timeout=30)

        self.assertFalse(app.exception)
        self.assertTrue(
            any(
                heading.value == "Connected mission trade space — Pareto front"
                for heading in app.header
            )
        )
        figure = captured["figure"]
        traces = {trace.meta["role"]: trace for trace in figure.data}
        self.assertEqual(
            len(traces["pareto_front"].x) + len(traces["Minimum connected delta-v"].x),
            34,
        )
        self.assertEqual(len(traces["Current mission baseline"].x), 1)
        self.assertAlmostEqual(
            traces["Current mission baseline"].customdata[0][1],
            2_856.0,
            delta=1e-9,
        )
        self.assertAlmostEqual(
            traces["Minimum connected delta-v"].customdata[0][1],
            2_856.0,
            delta=1e-9,
        )


class TestGravityAssistsPage(unittest.TestCase):
    def test_flyby_demonstrators_render_for_all_three_bodies(self):
        app = run_app(page_path="pages/gravity_assists.py")

        self.assertFalse(app.exception)
        subheaders = {sub.value for sub in app.subheader}
        self.assertEqual(
            subheaders,
            {"Venus flyby", "Earth flyby", "Jupiter flyby"},
        )
        self.assertTrue(any("Incoming v∞" == metric.label for metric in app.metric))


class TestNavigationAcrossAllPages(unittest.TestCase):
    def test_every_page_renders_without_exception(self):
        for page_path in (
            "pages/trajectory_3d.py",
            "pages/saturn_system_studies.py",
            "pages/feasibility.py",
            "pages/optimization.py",
            "pages/gravity_assists.py",
        ):
            with self.subTest(page=page_path):
                app = run_app(page_path=page_path)
                self.assertFalse(app.exception)


if __name__ == "__main__":
    unittest.main()
