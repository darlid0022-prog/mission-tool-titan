import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from app_services import DEFAULT_LAUNCH_WINDOW_END, DEFAULT_LAUNCH_WINDOW_START
from mission import physics
from mission.bodies import resolve_body
from mission.models import Leg, TrajectoryResult
from mission.pareto import compute_connected_pareto_front
from mission.pareto_plot import build_pareto_front_figure
from mission.ui_text import UI_TEXT

APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


class TestSaturnTitanUi(unittest.TestCase):
    @staticmethod
    def _earth_saturn_leg():
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

    @staticmethod
    def _earth_saturn_result():
        return {
            "note": "Test Earth-to-Saturn result",
            "dv_budget": {
                "dV from LEO": 1_000.0,
                "dV DSM/Fly-By": 0.0,
                "dV Capture at Destination": 999_999.0,
            },
            "dv_total": 1_000.0,
            "earth_saturn_leg": TestSaturnTitanUi._earth_saturn_leg(),
        }

    @staticmethod
    def _run_app(animation_phase=None):
        app = AppTest.from_file(APP_PATH)
        if animation_phase is not None:
            app.session_state["mission_animation_phase"] = animation_phase
            app.session_state["mission_phase_elapsed_days"] = 0.0
        with patch(
            "app_services.compute_cached_trajectory",
            return_value=TestSaturnTitanUi._earth_saturn_result(),
        ):
            return app.run(timeout=30)

    def test_preliminary_section_displays_nominal_results_and_source(self):
        app = self._run_app()

        self.assertFalse(app.exception)
        self.assertTrue(
            any(heading.value == "Saturn → Titan — preliminary model" for heading in app.header)
        )
        metrics = {metric.label: metric.value for metric in app.metric}
        self.assertEqual(metrics["Departure delta-v from staging orbit"], "1,257.6 m/s")
        self.assertEqual(metrics["Titan-relative v∞ (non-propulsive)"], "1,049.8 m/s")
        self.assertEqual(metrics["Titan capture delta-v"], "862.7 m/s")
        self.assertEqual(metrics["Saturn → Titan modeled delta-v"], "2,120.3 m/s")
        self.assertEqual(metrics["Saturn → Titan time of flight"], "5.133 days")
        self.assertTrue(any("JPL SAT441" in caption.value for caption in app.caption))

    def test_isolated_titan_edl_section_displays_direct_entry_without_budget_change(self):
        app = self._run_app()

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
        self.assertEqual(metrics["Sum of budgeted delta-v values"], "9903 m/s")
        self.assertTrue(
            any(
                "not included in the connected delta-v or mass budget" in warning.value
                for warning in app.warning
            )
        )

    def test_connected_total_and_default_mass_outputs_are_non_zero(self):
        app = self._run_app()

        self.assertFalse(app.exception)
        metrics = {metric.label: metric.value for metric in app.metric}
        self.assertEqual(metrics["Sum of budgeted delta-v values"], "9903 m/s")
        for label in ("Dry mass", "Propellant mass", "Total wet mass"):
            self.assertNotEqual(metrics[label], "0.0 kg", msg=label)
        self.assertFalse(
            any(widget.label == "Saturn capture altitude (km)" for widget in app.number_input)
        )
        self.assertTrue(
            any(
                "does not yet represent a complete spacecraft bus" in warning.value
                for warning in app.warning
            )
        )

    def test_arrival_to_staging_section_displays_nominal_results_and_ring_status(self):
        app = self._run_app()

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

    def test_complete_trajectory_3d_view_is_rendered(self):
        app = self._run_app()

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
        date_inputs = {date_input.label: date_input.value for date_input in app.date_input}
        self.assertEqual(date_inputs[UI_TEXT["launch_start"]], DEFAULT_LAUNCH_WINDOW_START)
        self.assertEqual(date_inputs[UI_TEXT["launch_end"]], DEFAULT_LAUNCH_WINDOW_END)

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
                return_value=self._earth_saturn_result(),
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
            app = AppTest.from_file(APP_PATH).run(timeout=30)

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
            38,
        )
        self.assertEqual(len(traces["Current mission baseline"].x), 1)
        self.assertAlmostEqual(
            traces["Current mission baseline"].customdata[0][1],
            2_856.0,
            delta=1e-9,
        )
        self.assertAlmostEqual(
            traces["Minimum connected delta-v"].customdata[0][1],
            2_826.0,
            delta=1e-9,
        )

    def test_animation_slider_uses_selected_phase_duration(self):
        phase_duration_attributes = {
            "Earth → Saturn cruise": "earth_saturn_duration_days",
            "Saturn arrival → staging": "saturn_staging_duration_days",
            "Saturn → Titan": "saturn_titan_duration_days",
        }

        for phase, duration_attribute in phase_duration_attributes.items():
            with self.subTest(phase=phase):
                app = self._run_app(phase)
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
            return_value=self._earth_saturn_result(),
        ):
            app.run(timeout=30)
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

    def test_complete_budget_is_connected_to_mass_sizing_without_legacy_capture(self):
        mass_result = {
            "instrument_mass_kg": 0.0,
            "dry_mass_kg": 1.0,
            "propellant_mass_kg": 0.0,
            "wet_mass_kg": 1.0,
        }
        with patch("app_services.compute_cached_trajectory") as trajectory_mock:
            trajectory_mock.return_value = {
                "note": "Test Earth-to-Saturn result",
                "dv_budget": {
                    "dV from LEO": 1_000.0,
                    "dV DSM/Fly-By": 0.0,
                    "dV Capture at Destination": 999_999.0,
                },
                "dv_total": 1_000.0,
                "earth_saturn_leg": self._earth_saturn_leg(),
            }
            with patch("mission.sizing.compute_mass_budget", return_value=mass_result) as mass_mock:
                app = AppTest.from_file(APP_PATH).run(timeout=30)

        self.assertFalse(app.exception)
        self.assertEqual(trajectory_mock.call_count, 1)
        self.assertEqual(mass_mock.call_count, 1)
        expected_total = 1_000.0 + 6_782.353909 + 2_120.301028
        self.assertAlmostEqual(mass_mock.call_args.args[0], expected_total, delta=1e-3)
        self.assertNotEqual(mass_mock.call_args.args[0], 1_000.0 + 999_999.0)

    def test_displayed_earth_departure_injection_equals_physics_output_exactly(self):
        v_inf_m_s = self._earth_saturn_leg().trajectory.v_inf_depart
        leo_altitude_m = 250_000.0
        earth = resolve_body("Earth")
        expected_injection_m_s = physics.delta_v_injection(
            v_inf_m_s,
            earth.get_mu_self(),
            earth.pykep_body.get_radius() + leo_altitude_m,
        )
        earth_saturn_result = {
            "note": "Test Earth-to-Saturn result",
            "dv_budget": {
                "dV from LEO": expected_injection_m_s,
                "dV DSM/Fly-By": 0.0,
                "dV Capture at Destination": 999_999.0,
            },
            "dv_total": expected_injection_m_s,
            "earth_saturn_leg": self._earth_saturn_leg(),
        }

        with patch(
            "app_services.compute_cached_trajectory", return_value=earth_saturn_result
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


if __name__ == "__main__":
    unittest.main()
