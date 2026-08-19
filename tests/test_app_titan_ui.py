import json
import unittest
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

import launch_window_service as lw
from app_services import (
    MISSION_SETUP_STATE_KEY,
    MissionSetupInputs,
    decode_mission_setup_query,
    encode_mission_setup_query,
)
from mission import physics
from mission.bodies import resolve_body
from mission.launch_search import evaluate_launch_scenario
from mission.launch_search_ephemeris import solve_earth_saturn_lambert
from mission.models import Leg, TrajectoryResult
from mission.pareto import compute_connected_pareto_front
from mission.pareto_plot import build_pareto_front_figure
from mission.ui_session_state import UI_MISSION_STATE_KEY, deserialize_ui_state
from mission.ui_state import CalculationStatus

APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


def earth_saturn_leg() -> Leg:
    solved = solve_earth_saturn_lambert(9_681.181818181818, 12_537.181818181829, 16)
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
            departure_position_m=solved.departure_position_m,
            arrival_position_m=solved.arrival_position_m,
            transfer_departure_velocity_m_s=solved.transfer_departure_velocity_m_s,
            central_mu_m3_s2=resolve_body("Earth").get_mu_central_body(),
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


def _plotly_marker_sizes(chart_element) -> dict[str, object]:
    """Read {trace name: marker size} off a rendered plotly_chart AppTest element.

    AppTest exposes no typed Plotly wrapper (it falls back to UnknownElement,
    whose .value tries the widget-state path and fails for a display-only
    chart), so this reads the figure straight out of the underlying proto's
    JSON spec instead.
    """
    spec = json.loads(chart_element.proto.spec)
    return {trace["name"]: trace["marker"]["size"] for trace in spec["data"] if "marker" in trace}


class TestMissionSetupPage(unittest.TestCase):
    def test_scientific_edit_marks_results_stale_without_recalculation(self):
        app = AppTest.from_file(APP_PATH)
        with patch(
            "app_services.compute_cached_trajectory", return_value=earth_saturn_result()
        ) as trajectory_mock:
            app.run(timeout=30)
            self.assertEqual(trajectory_mock.call_count, 1)
            self.assertEqual(
                deserialize_ui_state(app.session_state[UI_MISSION_STATE_KEY]).calculation_status,
                CalculationStatus.CURRENT,
            )

            isp = next(
                widget
                for widget in app.number_input
                if widget.label == "Main engine specific impulse (s)"
            )
            isp.set_value(321).run(timeout=30)

            self.assertEqual(trajectory_mock.call_count, 1)
            self.assertEqual(
                deserialize_ui_state(app.session_state[UI_MISSION_STATE_KEY]).calculation_status,
                CalculationStatus.STALE,
            )
            self.assertTrue(any("Inputs changed" in warning.value for warning in app.warning))
            self.assertEqual(
                {metric.label: metric.value for metric in app.metric}["Connected delta-v"],
                "12,531 m/s",
            )

    def test_returning_to_calculated_value_restores_current_without_calculation(self):
        app = AppTest.from_file(APP_PATH)
        with patch(
            "app_services.compute_cached_trajectory", return_value=earth_saturn_result()
        ) as trajectory_mock:
            app.run(timeout=30)
            isp = next(
                widget
                for widget in app.number_input
                if widget.label == "Main engine specific impulse (s)"
            )
            isp.set_value(321).run(timeout=30)
            isp = next(
                widget
                for widget in app.number_input
                if widget.label == "Main engine specific impulse (s)"
            )
            isp.set_value(320).run(timeout=30)

        self.assertEqual(trajectory_mock.call_count, 1)
        self.assertEqual(
            deserialize_ui_state(app.session_state[UI_MISSION_STATE_KEY]).calculation_status,
            CalculationStatus.CURRENT,
        )

    def test_calculate_promotes_visible_draft_and_returns_to_current(self):
        app = AppTest.from_file(APP_PATH)
        with patch(
            "app_services.compute_cached_trajectory", return_value=earth_saturn_result()
        ) as trajectory_mock:
            app.run(timeout=30)
            next(
                widget
                for widget in app.number_input
                if widget.label == "Main engine specific impulse (s)"
            ).set_value(321).run(timeout=30)
            next(button for button in app.button if "Calculate" in button.label).click().run(
                timeout=30
            )

        self.assertEqual(trajectory_mock.call_count, 2)
        self.assertEqual(app.session_state[MISSION_SETUP_STATE_KEY].isp_s, 321)
        self.assertEqual(
            deserialize_ui_state(app.session_state[UI_MISSION_STATE_KEY]).calculation_status,
            CalculationStatus.CURRENT,
        )

    def test_visual_session_change_does_not_mark_results_stale_or_recalculate(self):
        app = AppTest.from_file(APP_PATH)
        with patch(
            "app_services.compute_cached_trajectory", return_value=earth_saturn_result()
        ) as trajectory_mock:
            app.run(timeout=30)
            app.session_state["mission_visual_preference"] = "expanded"
            app.run(timeout=30)

        self.assertEqual(trajectory_mock.call_count, 1)
        self.assertEqual(
            deserialize_ui_state(app.session_state[UI_MISSION_STATE_KEY]).calculation_status,
            CalculationStatus.CURRENT,
        )

    def test_technical_failure_preserves_previous_results_and_status(self):
        app = AppTest.from_file(APP_PATH)
        with patch(
            "app_services.compute_cached_trajectory", return_value=earth_saturn_result()
        ) as trajectory_mock:
            app.run(timeout=30)
            next(
                widget
                for widget in app.number_input
                if widget.label == "Main engine specific impulse (s)"
            ).set_value(321).run(timeout=30)
            trajectory_mock.side_effect = RuntimeError("test engine failure")
            next(button for button in app.button if "Calculate" in button.label).click().run(
                timeout=30
            )

        self.assertFalse(app.exception)
        self.assertEqual(app.session_state[MISSION_SETUP_STATE_KEY].isp_s, 320)
        self.assertEqual(
            deserialize_ui_state(app.session_state[UI_MISSION_STATE_KEY]).calculation_status,
            CalculationStatus.TECHNICAL_ERROR,
        )
        self.assertEqual(
            {metric.label: metric.value for metric in app.metric}["Connected delta-v"],
            "12,531 m/s",
        )

    def test_no_solution_preserves_previous_results_and_has_distinct_status(self):
        app = AppTest.from_file(APP_PATH)
        with patch("app_services.compute_cached_trajectory", return_value=earth_saturn_result()):
            app.run(timeout=30)
            next(
                widget
                for widget in app.number_input
                if widget.label == "Main engine specific impulse (s)"
            ).set_value(321).run(timeout=30)
            with patch("app_services.require_mission_bundle", return_value=None):
                next(button for button in app.button if "Calculate" in button.label).click().run(
                    timeout=30
                )

        self.assertFalse(app.exception)
        self.assertEqual(app.session_state[MISSION_SETUP_STATE_KEY].isp_s, 320)
        self.assertEqual(
            deserialize_ui_state(app.session_state[UI_MISSION_STATE_KEY]).calculation_status,
            CalculationStatus.NO_SOLUTION,
        )
        self.assertEqual(
            {metric.label: metric.value for metric in app.metric}["Connected delta-v"],
            "12,531 m/s",
        )

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
        self.assertEqual(metrics["Sum of budgeted delta-v values"], "12,531 m/s")
        for label in (
            "Simplified dry mass",
            "Simplified propellant mass",
            "Simplified total wet mass",
        ):
            self.assertNotEqual(metrics[label], "0.0 kg", msg=label)
        self.assertFalse(
            any(widget.label == "Saturn capture altitude (km)" for widget in app.number_input)
        )
        number_input_labels = {widget.label for widget in app.number_input}
        self.assertIn("Connected Saturn capture periapsis radius (km)", number_input_labels)
        self.assertIn("Connected capture-ellipse apoapsis (km)", number_input_labels)
        self.assertNotIn("Saturn staging-orbit radius (km)", number_input_labels)
        self.assertNotIn("Titan capture altitude (km)", number_input_labels)
        self.assertTrue(
            any(
                "does not couple propulsion hardware mass to propellant mass" in warning.value
                for warning in app.warning
            )
        )

    def test_phase_color_key_lists_all_five_phases_in_chronological_order(self):
        app = run_app()

        self.assertFalse(app.exception)
        # Lunar transfer and Landing are marked "(not included)" - the
        # connected budget (mission.dv_budget.MissionDeltaVBudget) has no
        # field for either phase, so the key must not imply they contribute
        # to the delta-v total, while still using the same shared colors.
        self.assertEqual(
            badge_values(app),
            [
                ":orange-badge[Launch]",
                ":blue-badge[Interplanetary transfer]",
                ":green-badge[Arrival / orbit insertion]",
                ":violet-badge[Lunar transfer (not included)]",
                ":red-badge[Landing (not included)]",
            ],
        )
        self.assertTrue(
            any(
                "Lunar transfer and Landing are not modeled" in caption.value
                for caption in app.caption
            )
        )

    def test_scorecard_displays_live_connected_results(self):
        app = run_app()

        self.assertFalse(app.exception)
        metrics = {metric.label: metric.value for metric in app.metric}
        self.assertEqual(metrics["Connected delta-v"], "12,531 m/s")
        self.assertEqual(metrics["Wet mass (simplified)"], "12,138 kg")
        self.assertEqual(metrics["Earth → Saturn flight time"], "2,856.0 days")
        self.assertEqual(metrics["Total reference-scenario duration"], "2,859.4 days")
        self.assertEqual(metrics["Connected Saturn periapsis"], "150,000 km")
        self.assertEqual(metrics["Final Saturn-centred radius"], "1,221,870 km")
        # The isolated single-stage feasibility study no longer contributes a
        # numeric KPI to the connected scorecard (see docs/audit_science_budget_v030.md,
        # wording-and-scope batch §2.1) - only a non-numeric, explicitly isolated
        # reference remains.
        self.assertNotIn("Single-stage exceedance", metrics)
        self.assertTrue(
            any(
                "Single-stage feasibility: see the isolated study" in caption.value
                for caption in app.caption
            )
        )
        self.assertTrue(
            any(
                "Active scenario: Mission setup baseline" in caption.value
                for caption in app.caption
            )
        )
        # Removed from the scorecard: the isolated flyby demonstrators are not
        # directly additive as delta-v savings (see pages/gravity_assists.py).
        self.assertNotIn("Flyby gain coverage", metrics)

    def test_scorecard_delta_v_matches_the_provisional_budget_table_sum(self):
        app = run_app()

        self.assertFalse(app.exception)
        metrics = {metric.label: metric.value for metric in app.metric}
        # Same underlying bundle.dv_total value in both places, now with the
        # same thousands-separator formatting too (docs/audit_science_budget_v030.md
        # wording-and-scope batch, §2.2b - was "12531 m/s" without a separator).
        self.assertEqual(metrics["Connected delta-v"], "12,531 m/s")
        self.assertEqual(metrics["Sum of budgeted delta-v values"], "12,531 m/s")

    def test_planned_capabilities_section_is_absent_when_every_collection_is_empty(self):
        with (
            patch("app_services.compute_cached_trajectory", return_value=earth_saturn_result()),
            patch("mission.capabilities.MOON_DESTINATIONS", {}),
            patch("mission.capabilities.PLANNED_DESTINATIONS", ()),
            patch("mission.capabilities.PLANNED_MISSION_FEATURES", ()),
        ):
            app = AppTest.from_file(APP_PATH)
            app.run(timeout=30)

        self.assertFalse(app.exception)
        self.assertFalse(any(e.label == "Planned capabilities" for e in app.expander))
        # No leftover "-", "*", or blank placeholder anywhere on the page.
        self.assertFalse([m.value for m in app.markdown if m.value.strip() in ("-", "*", "")])

    def test_planned_capabilities_section_still_renders_when_non_empty(self):
        app = run_app()

        self.assertFalse(app.exception)
        self.assertTrue(any(e.label == "Planned capabilities" for e in app.expander))

    def test_titan_scope_text_points_to_the_dedicated_studies_page(self):
        app = run_app()

        self.assertFalse(app.exception)
        info_values = " ".join(i.value for i in app.info)
        self.assertIn(
            "Legacy Saturn staging, Titan-transfer, and Titan-entry studies remain "
            "available on Saturn & Titan studies. They are isolated from the "
            "connected budget.",
            info_values,
        )
        self.assertNotIn("legacy Saturn staging and moon-transfer studies below", info_values)

    def test_date_source_shows_a_calendar_date_with_mjd2000_as_a_technical_detail(self):
        app = run_app()

        self.assertFalse(app.exception)
        captions = [c.value for c in app.caption]
        self.assertTrue(
            any(
                "Date source: Mission setup Earth → Saturn trajectory solution "
                "(2026-07-04 → 2034-04-29 UTC)." == c
                for c in captions
            )
        )
        self.assertTrue(
            any(
                c.startswith("MJD2000 epoch reference (technical): 9681.182 → 12537.182")
                for c in captions
            )
        )

    def test_launch_windows_link_is_present_and_does_not_switch_the_active_scenario(self):
        app = run_app()

        self.assertFalse(app.exception)
        links = app.get("page_link")
        matching = [link for link in links if link.proto.label == "Find an optimized launch window"]
        self.assertEqual(len(matching), 1)
        self.assertIn("launch_windows", matching[0].proto.page)
        # Rendering the link must not itself change which scenario is active.
        self.assertTrue(
            any("Active scenario: Mission setup baseline" in c.value for c in app.caption)
        )

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
        expected_total = 12_530.653004975673
        self.assertAlmostEqual(mass_mock.call_args.args[0], expected_total, delta=1e-3)
        self.assertNotEqual(mass_mock.call_args.args[0], 1_000.0 + 999_999.0)

    def test_displayed_earth_departure_injection_equals_physics_output_exactly(self):
        v_inf_m_s = earth_saturn_leg().trajectory.v_inf_depart
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
    def test_trajectory_hub_makes_3d_and_launch_window_pareto_access_visible(self):
        app = run_app(page_path="pages/trajectory.py")

        self.assertFalse(app.exception)
        self.assertTrue(
            any(sub.value == "Direct trajectory in 3D" for sub in app.subheader)
        )
        self.assertTrue(
            any(sub.value == "Explore launch windows" for sub in app.subheader)
        )
        action_labels = {button.label for button in app.button}
        self.assertIn("Open 3D trajectory", action_labels)
        self.assertIn("Explore launch windows and Pareto front", action_labels)

    def test_trajectory_hub_3d_action_opens_the_existing_view(self):
        app = run_app(page_path="pages/trajectory.py")
        action = next(button for button in app.button if button.label == "Open 3D trajectory")
        app = action.click().run(timeout=30)

        self.assertFalse(app.exception)
        self.assertTrue(
            any(
                heading.value == "Complete mission trajectory — interactive 3D view"
                for heading in app.header
            )
        )

    def test_trajectory_hub_pareto_action_opens_launch_window_search(self):
        app = run_app(page_path="pages/trajectory.py")
        action = next(
            button
            for button in app.button
            if button.label == "Explore launch windows and Pareto front"
        )
        app = action.click().run(timeout=30)

        self.assertFalse(app.exception)
        self.assertTrue(
            any("Launch window search" in heading.value for heading in app.header)
        )

    def test_direct_mode_renders_animated_heliocentric_and_static_saturn_scenes(self):
        app = run_app(page_path="pages/trajectory_3d.py")

        self.assertFalse(app.exception)
        self.assertEqual(len(app.get("plotly_chart")), 2)
        display = next(
            control for control in app.segmented_control if control.label == "Trajectory display"
        )
        self.assertEqual(display.value, "Animated")
        self.assertFalse(app.slider)

    def test_direct_page_uses_connected_capture_and_rejects_titan_claims(self):
        app = run_app(page_path="pages/trajectory_3d.py")

        self.assertFalse(app.exception)
        self.assertTrue(
            any(
                "not a phased Titan encounter or Titan-centred insertion" in caption.value
                for caption in app.caption
            )
        )
        self.assertFalse(
            any("legacy Saturn arrival-to-staging" in warning.value for warning in app.warning)
        )

    def test_historical_mode_renders_five_leg_tour_without_direct_animation_controls(self):
        app = AppTest.from_file(APP_PATH)
        with patch("app_services.compute_cached_trajectory", return_value=earth_saturn_result()):
            app.run(timeout=30)
            trajectory_type = next(radio for radio in app.radio if radio.label == "Trajectory type")
            trajectory_type.set_value("Cassini historical gravity assist")
            next(button for button in app.button if "Calculate" in button.label).click().run(
                timeout=30
            )
            app.switch_page("pages/trajectory_3d.py").run(timeout=30)

        self.assertFalse(app.exception)
        # The static historical chart plus the new generic-segment scene chart.
        self.assertEqual(len(app.get("plotly_chart")), 2)
        self.assertTrue(
            any("Cassini historical VVEJGA tour" in caption.value for caption in app.caption)
        )
        self.assertFalse(app.segmented_control)
        self.assertFalse(app.slider)

    def test_chart_has_a_keyboard_accessible_data_table_alternative(self):
        app = run_app(page_path="pages/trajectory_3d.py")

        self.assertFalse(app.exception)
        expander = next(e for e in app.expander if e.label == "View segment data as a table")
        table = expander.dataframe[0].value
        self.assertEqual(
            list(table.columns),
            [
                "Segment",
                "Type",
                "Origin",
                "Destination",
                "Point index",
                "x",
                "y",
                "z",
                "Departure date",
                "Arrival date",
                "Duration (days)",
                "Delta-v (m/s)",
            ],
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
        self.assertEqual(len(app.get("plotly_chart")), 2)
        self.assertTrue(
            any(
                control.label == "Trajectory display" and control.value == "Animated"
                for control in app.segmented_control
            )
        )
        self.assertTrue(
            any(
                "graphical interpolation, not an independent dynamical propagation" in caption.value
                for caption in app.caption
            )
        )

    def test_static_fallback_keeps_the_direct_scene(self):
        app = run_app(page_path="pages/trajectory_3d.py")
        display = next(
            control for control in app.segmented_control if control.label == "Trajectory display"
        )
        display.set_value("Static").run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(len(app.get("plotly_chart")), 2)
        spec = json.loads(app.get("plotly_chart")[0].proto.spec)
        self.assertNotIn("frames", spec)

    def test_generic_scene_section_offers_all_four_camera_presets_in_direct_mode(self):
        app = run_app(page_path="pages/trajectory_3d.py")

        self.assertFalse(app.exception)
        view_preset = next(
            select
            for select in app.selectbox
            if select.label == "Camera view" and len(select.options) == 4
        )
        self.assertEqual(list(view_preset.options), ["Global", "Rings", "Periapsis", "Titan"])
        self.assertEqual(view_preset.value, "Global")

    def test_direct_animation_export_is_available(self):
        app = run_app(page_path="pages/trajectory_3d.py")
        self.assertFalse(app.exception)
        self.assertTrue(
            any(
                button.label == "Download standalone HTML (offline-capable)"
                for button in app.download_button
            )
        )

    def test_active_launch_candidate_drives_the_animated_scene(self):
        scenario = evaluate_launch_scenario(10_408.0, 12_428.0, sample_count=16)
        epoch = datetime(2000, 1, 1, tzinfo=UTC)
        candidate = lw.LaunchWindowCandidate(
            rank=1,
            departure_datetime=epoch + timedelta(days=scenario.launch_mjd2000),
            saturn_arrival_datetime=epoch + timedelta(days=scenario.saturn_arrival_mjd2000),
            scenario_end_datetime=epoch + timedelta(days=scenario.reference_phase_end_mjd2000),
            time_of_flight_days=scenario.interplanetary_duration_days,
            c3_km2_s2=scenario.c3_m2_s2 / 1_000_000.0,
            v_infinity_earth_m_s=scenario.earth_v_infinity_m_s,
            v_infinity_saturn_m_s=scenario.saturn_v_infinity_m_s,
            delta_v_departure_m_s=scenario.delta_v_by_manoeuvre_m_s[0][1],
            delta_v_capture_m_s=scenario.delta_v_by_manoeuvre_m_s[1][1],
            delta_v_titan_circularization_m_s=(scenario.delta_v_by_manoeuvre_m_s[2][1]),
            delta_v_total_m_s=scenario.total_delta_v_m_s,
            scenario_id=scenario.scenario_id,
            notes=scenario.assumptions,
            segments=scenario.segments,
        )
        app = AppTest.from_file(APP_PATH)
        with patch("app_services.compute_cached_trajectory", return_value=earth_saturn_result()):
            app.run(timeout=30)
            app.session_state[lw.ACTIVE_LAUNCH_WINDOW_CANDIDATE_STATE_KEY] = candidate
            app.switch_page("pages/trajectory_3d.py").run(timeout=30)

        self.assertFalse(app.exception)
        self.assertTrue(any(scenario.scenario_id in caption.value for caption in app.caption))
        self.assertTrue(
            any(
                control.label == "Trajectory display" and control.value == "Animated"
                for control in app.segmented_control
            )
        )

    def test_generic_scene_section_offers_a_table_and_html_download(self):
        app = run_app(page_path="pages/trajectory_3d.py")

        self.assertFalse(app.exception)
        expander = next(e for e in app.expander if e.label == "View segment data as a table")
        table = expander.dataframe[0].value
        self.assertEqual(
            list(table.columns),
            [
                "Segment",
                "Type",
                "Origin",
                "Destination",
                "Point index",
                "x",
                "y",
                "z",
                "Departure date",
                "Arrival date",
                "Duration (days)",
                "Delta-v (m/s)",
            ],
        )
        self.assertGreater(len(table), 0)
        self.assertTrue(
            any(
                button.label == "Download standalone HTML (offline-capable)"
                for button in app.download_button
            )
        )

    def test_generic_scene_section_offers_only_global_preset_in_historical_mode(self):
        app = AppTest.from_file(APP_PATH)
        with patch("app_services.compute_cached_trajectory", return_value=earth_saturn_result()):
            app.run(timeout=30)
            trajectory_type = next(radio for radio in app.radio if radio.label == "Trajectory type")
            trajectory_type.set_value("Cassini historical gravity assist")
            next(button for button in app.button if "Calculate" in button.label).click().run(
                timeout=30
            )
            app.switch_page("pages/trajectory_3d.py").run(timeout=30)

        self.assertFalse(app.exception)
        self.assertTrue(
            any(sub.value == "Generic segment view (gravity-assist tour)" for sub in app.subheader)
        )
        view_preset = next(select for select in app.selectbox if select.label == "Camera view")
        self.assertEqual(list(view_preset.options), ["Global"])


class TestSaturnSystemStudiesPage(unittest.TestCase):
    def test_each_section_carries_its_own_mission_phase_badge(self):
        app = run_app(page_path="pages/saturn_system_studies.py")

        self.assertFalse(app.exception)
        # The new authoritative model (top of page) and the legacy
        # arrival-to-staging study (below it) are both the Arrival phase.
        self.assertEqual(
            badge_values(app),
            [
                ":green-badge[Arrival / orbit insertion]",
                ":green-badge[Arrival / orbit insertion]",
                ":violet-badge[Lunar transfer]",
                ":red-badge[Landing]",
            ],
        )

    def test_authoritative_model_section_distinguishes_arrival_insertion_and_circularization(
        self,
    ):
        app = run_app(page_path="pages/saturn_system_studies.py")

        self.assertFalse(app.exception)
        self.assertTrue(
            any(
                heading.value == "Saturn hyperbolic arrival & capture — authoritative model"
                for heading in app.header
            )
        )
        subheaders = {sub.value for sub in app.subheader}
        # The four physically distinct phases the model separates.
        self.assertIn("Hyperbolic arrival", subheaders)
        self.assertIn("Propulsive capture-to-ellipse insertion", subheaders)
        self.assertIn("Capture ellipse", subheaders)
        self.assertIn("Circularization at Titan's orbital radius", subheaders)

        metrics = {metric.label: metric.value for metric in app.metric}
        self.assertEqual(metrics["Saturn arrival v∞"], "6,490.7 m/s")
        self.assertEqual(metrics["Hyperbola periapsis radius"], "150,000 km")
        self.assertEqual(metrics["Hyperbola eccentricity"], "1.167")
        self.assertEqual(metrics["Hyperbola deflection angle"], "118.0°")
        self.assertEqual(metrics["Margin outside F ring"], "9,820 km")
        # docs/audit_science_budget_v030.md wording-and-scope batch §2.6: the
        # scalar F-ring margin is not a 3D ring-plane clearance claim.
        self.assertTrue(
            any(
                "does not characterize the three-dimensional geometry" in c.value
                for c in app.caption
            )
        )
        self.assertEqual(metrics["Insertion delta-v"], "2,183.0 m/s")
        self.assertEqual(metrics["Ellipse periapsis radius"], "150,000 km")
        self.assertEqual(metrics["Ellipse apoapsis radius"], "1,221,870 km")
        self.assertEqual(metrics["Ellipse eccentricity"], "0.781")
        self.assertEqual(metrics["Periapsis → apoapsis time"], "3.354 days")
        self.assertEqual(metrics["Circularization delta-v"], "2,966.2 m/s")

        # No Titan encounter/capture claimed anywhere in this section.
        self.assertTrue(any("does not model a Titan encounter" in info.value for info in app.info))

        with self.subTest(check="assumptions_exclusions_render_as_one_list_per_call"):
            markdown_values = [markdown.value for markdown in app.markdown]
            multiline_lists = [
                value
                for value in markdown_values
                if value.count("\n- ") >= 1 or value.startswith("- ")
                if value.count("\n") >= 1
            ]
            self.assertTrue(multiline_lists, "expected at least one multi-item bullet list")

    def test_arrival_to_staging_section_displays_nominal_results_and_ring_status(self):
        app = run_app(page_path="pages/saturn_system_studies.py")

        self.assertFalse(app.exception)
        self.assertTrue(
            any(
                heading.value == "Legacy internal ring-corridor arrival → staging study"
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
        self.assertEqual(metrics["Required connected delta-v"], "12,530.653 m/s")
        self.assertEqual(metrics["Maximum feasible single-stage delta-v"], "3,833.463 m/s")
        self.assertEqual(metrics["Required / feasible threshold"], "3.269×")
        self.assertTrue(
            any(
                "This is a model finding, not an application error" in info.value
                for info in app.info
            )
        )
        # docs/audit_science_budget_v030.md wording-and-scope batch §2.2: the
        # allocation bracket is a bare division of two already-displayed
        # values (5,149.173 / 3,833.463), confined to this isolated study.
        captions = " ".join(c.value for c in app.caption)
        self.assertIn("3.269×", captions)
        self.assertIn("12,530.653 m/s", captions)
        self.assertIn("1.343×", captions)
        self.assertIn("5,149.173 m/s", captions)
        self.assertIn("not determine the allocation", captions)


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

    def test_baseline_coinciding_with_sampled_minimum_avoids_a_zero_comparison(self):
        # docs/audit_science_budget_v030.md wording-and-scope batch §2.5: the
        # reference baseline is the sampled minimum-delta-v point, so the old
        # "requires 0.000 m/s more (+0.00%)" comparison read as a bug.
        app = run_app(page_path="pages/optimization.py")

        self.assertFalse(app.exception)
        captions = " ".join(c.value for c in app.caption)
        self.assertIn("coincides with the sampled minimum-delta-v point", captions)
        self.assertIn("1,176 points evaluated, 38 non-dominated", captions)
        self.assertNotIn("0.000 m/s more", captions)

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

    def test_caption_discloses_isolation_from_a_connected_vvejga_trajectory(self):
        app = run_app(page_path="pages/gravity_assists.py")

        self.assertFalse(app.exception)
        captions = " ".join(caption.value for caption in app.caption)
        self.assertIn("not form a connected VVEJGA trajectory", captions)
        self.assertIn("not directly additive as delta-v savings", captions)
        self.assertIn("Unpowered flyby", captions)


class TestBudgetAndVerdictV030(unittest.TestCase):
    def test_budget_displays_audited_baseline_values_and_scope(self):
        app = run_app(page_path="pages/budget.py")

        self.assertFalse(app.exception)
        metrics = {metric.label: metric.value for metric in app.metric}
        self.assertEqual(metrics["Earth C3"], "≈108.83 km²/s²")
        self.assertEqual(metrics["Earth v∞"], "≈10.432 km/s")
        self.assertEqual(metrics["Modeled Earth injection"], "7,381.480 m/s")
        self.assertEqual(metrics["Saturn capture"], "2,182.991 m/s")
        self.assertEqual(metrics["Saturn-centered circularization"], "2,966.182 m/s")
        self.assertEqual(
            metrics["Subtotal of modeled Saturn maneuvers"], "5,149.173 m/s"
        )
        self.assertEqual(metrics["Connected total"], "12,530.653 m/s")
        captions = " ".join(item.value for item in app.caption)
        self.assertIn("They are not additional delta-v contributions", captions)
        self.assertIn("No real launch vehicle is currently modeled", captions)
        self.assertIn("not a Titan encounter", captions)

    def test_verdict_is_cautious_and_uses_the_complete_total(self):
        app = run_app(page_path="pages/verdict.py")

        self.assertFalse(app.exception)
        metrics = {metric.label: metric.value for metric in app.metric}
        self.assertEqual(metrics["Connected total"], "12,530.653 m/s")
        visible = " ".join(
            element.value
            for collection in (
                app.header,
                app.markdown,
                app.caption,
                app.info,
                app.warning,
            )
            for element in collection
        )
        # "Model conclusion" (with its former tautological sentence) is no longer
        # rendered for the connected Earth-Saturn-Titan case: the two lists below
        # are the verdict (docs/audit_science_budget_v030.md, wording-and-scope
        # batch §2.4). The header is retained only for the historical/non-Saturn
        # branches, which this default connected scenario does not exercise.
        self.assertNotIn("Model conclusion", visible)
        self.assertIn("This result does not demonstrate a Titan encounter", visible)
        self.assertIn("What the model calculates", visible)
        self.assertIn("What the model does not demonstrate", visible)
        self.assertNotIn("Launchable", visible)
        self.assertNotIn("Supported by a launch vehicle", visible)

    def test_budget_and_verdict_render_without_recomputing_the_bundle(self):
        app = AppTest.from_file(APP_PATH)
        with patch(
            "app_services.compute_cached_trajectory", return_value=earth_saturn_result()
        ) as trajectory_mock:
            app.run(timeout=30)
            self.assertEqual(trajectory_mock.call_count, 1)
            app.switch_page("pages/budget.py").run(timeout=30)
            app.switch_page("pages/verdict.py").run(timeout=30)
        self.assertEqual(trajectory_mock.call_count, 1)

    def test_stale_budget_and_verdict_identify_previous_results(self):
        app = run_app()
        isp = next(
            widget
            for widget in app.number_input
            if widget.label == "Main engine specific impulse (s)"
        )
        isp.set_value(321).run(timeout=30)

        app.switch_page("pages/budget.py").run(timeout=30)
        self.assertTrue(
            any("previous calculation" in warning.value for warning in app.warning)
        )
        app.switch_page("pages/verdict.py").run(timeout=30)
        self.assertTrue(
            any("previous calculation" in warning.value for warning in app.warning)
        )


class TestNavigationAcrossAllPages(unittest.TestCase):
    def test_every_page_renders_without_exception(self):
        for page_path in (
            "pages/budget.py",
            "pages/verdict.py",
            "pages/launch_windows.py",
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
