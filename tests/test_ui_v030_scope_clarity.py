"""Tests for the "clarify durations, mass scope, and scenario metadata" fix.

Covers: the Trajectory duration breakdown, the Mission-setup mass-ratio
relabeling, the compacted Budget/Verdict scenario summary, the single
LAST_VALID_MISSION_BUNDLE_STATE_KEY definition, the Saturn & Titan studies
section context, and cross-page non-regression.
"""

import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

import mission.ui_keys as ui_keys
import mission.ui_presentation as ui_presentation
import pages.mission_setup as mission_setup_page
from mission.bodies import resolve_body
from mission.launch_search_ephemeris import solve_earth_saturn_lambert
from mission.models import Leg, TrajectoryResult

APP_PATH = Path(__file__).resolve().parents[1] / "app.py"
ROOT = Path(__file__).resolve().parents[1]


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


def _run_calculated_app() -> AppTest:
    with patch("app_services.compute_cached_trajectory", return_value=earth_saturn_result()):
        app = AppTest.from_file(APP_PATH)
        app.run(timeout=30)
        calculate = next(b for b in app.button if "Calculate" in b.label)
        app = calculate.click().run(timeout=30)
    return app


class TestSingleStateKeyDefinition(unittest.TestCase):
    def test_only_mission_ui_keys_defines_the_literal(self) -> None:
        offenders = []
        for path in ROOT.rglob("*.py"):
            if "/tests/" in str(path) or path.name.startswith("test_"):
                continue
            if "__pycache__" in str(path):
                continue
            text = path.read_text()
            if (
                '"mission_last_valid_bundle_v030"' in text
                and path != ROOT / "mission" / "ui_keys.py"
            ):
                offenders.append(str(path.relative_to(ROOT)))
        self.assertEqual(offenders, [], f"Duplicate key literal found in: {offenders}")

    def test_value_is_unchanged_from_before_the_fix(self) -> None:
        self.assertEqual(
            ui_keys.LAST_VALID_MISSION_BUNDLE_STATE_KEY, "mission_last_valid_bundle_v030"
        )

    def test_ui_presentation_reexports_the_same_object_not_a_copy(self) -> None:
        self.assertIs(
            ui_presentation.LAST_VALID_MISSION_BUNDLE_STATE_KEY,
            ui_keys.LAST_VALID_MISSION_BUNDLE_STATE_KEY,
        )

    def test_mission_setup_page_imports_rather_than_redefines(self) -> None:
        self.assertIs(
            mission_setup_page.LAST_VALID_MISSION_BUNDLE_STATE_KEY,
            ui_keys.LAST_VALID_MISSION_BUNDLE_STATE_KEY,
        )

    def test_key_is_not_defined_inside_a_visual_component_module(self) -> None:
        text = (ROOT / "mission" / "ui_components.py").read_text()
        self.assertNotIn('"mission_last_valid_bundle_v030"', text)

    def test_existing_session_state_written_under_the_old_key_stays_readable(self) -> None:
        """A session_state dict populated before this fix (using the literal
        key string, exactly as either old definition would have produced)
        must still be the same key the app reads today - no migration, no
        rename."""
        session_state = {ui_keys.LAST_VALID_MISSION_BUNDLE_STATE_KEY: "sentinel-bundle"}
        self.assertEqual(
            session_state.get(ui_presentation.LAST_VALID_MISSION_BUNDLE_STATE_KEY),
            "sentinel-bundle",
        )


class TestMassRatioScopeAndLabel(unittest.TestCase):
    def test_full_connected_total_is_passed_to_compute_mass_budget(self) -> None:
        with (
            patch("app_services.compute_cached_trajectory", return_value=earth_saturn_result()),
            patch("app_services.compute_mass_budget") as mass_mock,
        ):
            mass_mock.return_value = {
                "instrument_mass_kg": 1.0,
                "dry_mass_kg": 1.0,
                "propellant_mass_kg": 0.0,
                "wet_mass_kg": 1.0,
            }
            app = AppTest.from_file(APP_PATH)
            app.run(timeout=30)
        self.assertFalse(app.exception)
        self.assertEqual(mass_mock.call_count, 1)
        passed_dv_total = mass_mock.call_args.args[0]
        # The full connected total (Earth injection + Saturn capture +
        # circularization), never the Saturn-only subtotal (5,149.173 m/s).
        self.assertNotAlmostEqual(passed_dv_total, 5_149.173, places=1)
        self.assertAlmostEqual(passed_dv_total, 12_530.653, delta=1.0)

    def test_mass_ratio_metric_uses_the_new_label_and_allocation_help_text(self) -> None:
        app = _run_calculated_app()
        self.assertFalse(app.exception)
        ratio_metric = next(
            m for m in app.metric if m.label == "Simplified mass ratio using the full connected Δv"
        )
        self.assertIn("full connected total", ratio_metric.help)
        self.assertIn("not modeled", ratio_metric.help)
        self.assertIn("not a vehicle feasibility verdict", ratio_metric.help)
        # The displayed ratio matches the full-total mass ratio (~54.2), not
        # the Saturn-only-subtotal figure (~5.16).
        self.assertNotIn("5.16", ratio_metric.value)
        self.assertNotIn("5.15", ratio_metric.value)

    def test_single_stage_exceedance_is_scoped_as_conditional_not_a_verdict(self) -> None:
        app = _run_calculated_app()
        self.assertFalse(app.exception)
        exceedance_metric = next(m for m in app.metric if m.label == "Single-stage exceedance")
        self.assertIn("conditional result", exceedance_metric.help)
        self.assertIn("not a verdict", exceedance_metric.help)

    def test_no_metric_anywhere_on_mission_setup_presents_5_16_as_the_mission_ratio(self) -> None:
        app = _run_calculated_app()
        self.assertFalse(app.exception)
        for metric in app.metric:
            if "ratio" in metric.label.lower() or "exceedance" in metric.label.lower():
                self.assertNotIn("5.16", metric.value)


class TestDurationBreakdownWiring(unittest.TestCase):
    def test_trajectory_shows_the_exact_required_breakdown_for_the_baseline(self) -> None:
        with patch("app_services.compute_cached_trajectory", return_value=earth_saturn_result()):
            app = AppTest.from_file(APP_PATH)
            app.run(timeout=30)
            calculate = next(b for b in app.button if "Calculate" in b.label)
            app = calculate.click().run(timeout=30)
            app = app.switch_page("pages/trajectory.py").run(timeout=30)
        self.assertFalse(app.exception)
        self.assertTrue(
            any(
                "2,859.4 days complete" in m.value
                for m in app.markdown
                if "Complete reference scenario duration" in m.value
            )
        )
        breakdown_expander = next(
            e for e in app.expander if e.label == "Complete reference scenario duration"
        )
        detail_values = [w.value for w in breakdown_expander.markdown]
        self.assertIn("2,859.354 = 2,856.000 + approximately 3.354 days", detail_values)


class TestScenarioMetadataCompaction(unittest.TestCase):
    def _budget_app(self) -> AppTest:
        with patch("app_services.compute_cached_trajectory", return_value=earth_saturn_result()):
            app = AppTest.from_file(APP_PATH)
            app.run(timeout=30)
            calculate = next(b for b in app.button if "Calculate" in b.label)
            app = calculate.click().run(timeout=30)
            app = app.switch_page("pages/budget.py").run(timeout=30)
        return app

    def test_first_level_summary_omits_scenario_id_and_full_timestamp(self) -> None:
        app = self._budget_app()
        self.assertFalse(app.exception)
        summary_caption = next(
            c for c in app.caption if "Active scenario" in c.value and "·" in c.value
        )
        self.assertNotIn("Scenario ID", summary_caption.value)
        self.assertNotIn("T", summary_caption.value.split("·")[-1])  # no ISO 'T' separator

    def test_scenario_id_and_full_timestamp_remain_accessible_and_unchanged(self) -> None:
        app = self._budget_app()
        self.assertFalse(app.exception)
        expander = next(e for e in app.expander if e.label == "Scenario technical metadata")
        captions = [c.value for c in expander.caption]
        self.assertTrue(any(c.startswith("Scenario ID: mission-setup-baseline") for c in captions))
        timestamp_caption = next(c for c in captions if c.startswith("Calculated at: "))
        iso_value = timestamp_caption.removeprefix("Calculated at: ")
        # Must remain a full, parseable ISO 8601 timestamp - unchanged format.
        from datetime import datetime

        datetime.fromisoformat(iso_value)

    def test_calculation_status_still_renders_at_first_level(self) -> None:
        app = self._budget_app()
        self.assertFalse(app.exception)
        self.assertTrue(any(c.value.startswith("Calculation status ·") for c in app.caption))


class TestSaturnStudiesSectionContext(unittest.TestCase):
    def test_technical_details_link_carries_a_technical_section_param(self) -> None:
        source = (ROOT / "pages" / "technical_details.py").read_text()
        self.assertIn('query_params={"section": "technical"}', source)

    def test_isolated_studies_link_carries_an_isolated_section_param(self) -> None:
        source = (ROOT / "pages" / "isolated_studies.py").read_text()
        self.assertIn('query_params={"section": "isolated"}', source)

    def test_saturn_studies_shows_distinct_context_per_entry_point(self) -> None:
        with patch("app_services.compute_cached_trajectory", return_value=earth_saturn_result()):
            app = AppTest.from_file(APP_PATH)
            app.run(timeout=30)
            calculate = next(b for b in app.button if "Calculate" in b.label)
            app = calculate.click().run(timeout=30)

            app.query_params["section"] = "technical"
            technical_app = app.switch_page("pages/saturn_system_studies.py").run(timeout=30)
        self.assertFalse(technical_app.exception)
        self.assertTrue(
            any("Arrived from Technical details" in c.value for c in technical_app.caption)
        )

        with patch("app_services.compute_cached_trajectory", return_value=earth_saturn_result()):
            app2 = AppTest.from_file(APP_PATH)
            app2.run(timeout=30)
            calculate2 = next(b for b in app2.button if "Calculate" in b.label)
            app2 = calculate2.click().run(timeout=30)
            app2.query_params["section"] = "isolated"
            isolated_app = app2.switch_page("pages/saturn_system_studies.py").run(timeout=30)
        self.assertFalse(isolated_app.exception)
        self.assertTrue(
            any("Arrived from Isolated studies" in c.value for c in isolated_app.caption)
        )

    def test_no_study_is_removed_or_merged(self) -> None:
        source = (ROOT / "pages" / "saturn_system_studies.py").read_text()
        for required in (
            "connected_first_order_header",
            "staging_result",
            "titan_transfer",
            "titan_edl",
        ):
            self.assertIn(required, source)


class TestCrossPageNonRegression(unittest.TestCase):
    """Every page this fix must not break, reached the same way a user would,
    with no unnecessary calculation re-triggered."""

    def test_all_named_pages_render_without_exception(self) -> None:
        pages = (
            "pages/trajectory.py",
            "pages/budget.py",
            "pages/verdict.py",
            "pages/technical_details.py",
            "pages/isolated_studies.py",
            "pages/saturn_system_studies.py",
            "pages/trajectory_3d.py",
            "pages/launch_windows.py",
            "pages/optimization.py",
            "pages/gravity_assists.py",
            "pages/feasibility.py",
        )
        for page in pages:
            with self.subTest(page=page):
                with patch(
                    "app_services.compute_cached_trajectory", return_value=earth_saturn_result()
                ):
                    app = AppTest.from_file(APP_PATH)
                    app.run(timeout=30)
                    calculate = next(b for b in app.button if "Calculate" in b.label)
                    app = calculate.click().run(timeout=30)
                    app = app.switch_page(page).run(timeout=30)
                self.assertFalse(app.exception)

    def test_direct_animation_controls_remain_on_trajectory_3d(self) -> None:
        with patch("app_services.compute_cached_trajectory", return_value=earth_saturn_result()):
            app = AppTest.from_file(APP_PATH)
            app.run(timeout=30)
            calculate = next(b for b in app.button if "Calculate" in b.label)
            app = calculate.click().run(timeout=30)
            app = app.switch_page("pages/trajectory_3d.py").run(timeout=30)
        self.assertFalse(app.exception)
        display_mode_controls = [
            c for c in app.segmented_control if c.label == "Trajectory display"
        ]
        self.assertTrue(
            display_mode_controls, "expected an Animated/Static mode control on 3D trajectory"
        )
        self.assertEqual(tuple(display_mode_controls[0].options), ("Animated", "Static"))

    def test_baseline_connected_total_is_numerically_unchanged(self) -> None:
        app = _run_calculated_app()
        self.assertFalse(app.exception)
        metrics = {m.label: m.value for m in app.metric}
        self.assertEqual(metrics["Connected delta-v"], "12,531 m/s")


if __name__ == "__main__":
    unittest.main()
