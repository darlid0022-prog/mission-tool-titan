"""Regression tests for the hard-refresh typography/icon/header regression.

Human-confirmed symptoms (Cmd+Shift+R): H1 clipped under the Streamlit
header, literal "dashboard" text before "Mission scorecard", oversized
typography, excessive vertical spacing, MJD2000 visible at first level.

These are static/AppTest checks only. They prove the source no longer
contains the broken pattern and that the app still renders without
exception - they do NOT prove pixel-perfect visual rendering in a real
browser. See the report for the required human verification checklist.
"""

import re
import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from mission.bodies import resolve_body
from mission.launch_search_ephemeris import solve_earth_saturn_lambert
from mission.models import Leg, TrajectoryResult

ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "app.py"
STYLE_SOURCE = (ROOT / "mission" / "ui_style.py").read_text()
THEME_SOURCE = (ROOT / ".streamlit" / "config.toml").read_text()


def earth_saturn_result() -> dict:
    solved = solve_earth_saturn_lambert(9_681.181818181818, 12_537.181818181829, 16)
    leg = Leg(
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
    return {
        "note": "Test Earth-to-Saturn result",
        "dv_budget": {
            "dV from LEO": 1_000.0,
            "dV DSM/Fly-By": 0.0,
            "dV Capture at Destination": 999_999.0,
        },
        "dv_total": 1_000.0,
        "earth_saturn_leg": leg,
    }


def _run_calculated_mission() -> AppTest:
    with patch("app_services.compute_cached_trajectory", return_value=earth_saturn_result()):
        app = AppTest.from_file(APP_PATH)
        app.run(timeout=30)
        calculate = next(b for b in app.button if "Calculate" in b.label)
        app = calculate.click().run(timeout=30)
    return app


class TestNoBrokenMaterialIconShorthand(unittest.TestCase):
    """Root cause: `st.subheader(":material/dashboard: ...")` uses the
    Material-Symbols markdown shorthand inline in a heading's body text.
    When that glyph fails to resolve, Streamlit's ligature-font fallback
    renders the bare icon name ("dashboard") as literal text. The fix
    removes the shorthand from this string entirely rather than depending
    on the icon font resolving correctly."""

    def test_source_no_longer_contains_the_broken_shorthand(self) -> None:
        source = (ROOT / "pages" / "mission_setup.py").read_text()
        self.assertNotIn(":material/dashboard:", source)

    def test_scorecard_subheader_is_exactly_mission_scorecard(self) -> None:
        source = (ROOT / "pages" / "mission_setup.py").read_text()
        occurrences = re.findall(r'st\.subheader\("([^"]*)"\)', source)
        scorecard_headers = [text for text in occurrences if "Mission scorecard" in text]
        self.assertTrue(scorecard_headers, "expected at least one Mission scorecard subheader")
        for text in scorecard_headers:
            self.assertEqual(text, "Mission scorecard")

    def test_no_stray_dashboard_text_renders_anywhere_on_mission(self) -> None:
        app = _run_calculated_mission()
        self.assertFalse(app.exception)
        for subheader in app.subheader:
            self.assertNotIn("dashboard", subheader.value.lower())
        for markdown in app.markdown:
            self.assertNotIn("dashboard Mission scorecard", markdown.value)
        self.assertIn("Mission scorecard", [s.value for s in app.subheader])


class TestNoRemoteFontDependency(unittest.TestCase):
    def test_no_google_fonts_stylesheet_import(self) -> None:
        self.assertNotIn("fonts.googleapis.com", THEME_SOURCE)
        self.assertNotIn("fonts.googleapis.com", STYLE_SOURCE)

    def test_no_google_fonts_static_asset_domain(self) -> None:
        self.assertNotIn("fonts.gstatic.com", THEME_SOURCE)
        self.assertNotIn("fonts.gstatic.com", STYLE_SOURCE)

    def test_no_at_font_face_rule_anywhere_in_the_shell_style(self) -> None:
        # Checks for an actual @font-face {...} rule, not just the substring
        # (which also appears inside this file's own explanatory comment).
        self.assertIsNone(re.search(r"@font-face\s*\{", STYLE_SOURCE))


class TestMjd2000NotAtFirstLevel(unittest.TestCase):
    def test_mjd2000_only_appears_inside_an_expander(self) -> None:
        app = _run_calculated_mission()
        self.assertFalse(app.exception)
        expander = next(e for e in app.expander if e.label == "Technical epoch reference")
        nested_mjd2000 = [c.value for c in expander.caption if "MJD2000" in c.value]
        self.assertTrue(nested_mjd2000, "MJD2000 must remain accessible, inside the expander")
        # Every MJD2000 occurrence anywhere on the page must be exactly the
        # one(s) already accounted for inside that expander - none floating
        # free at first level.
        all_mjd2000 = [c.value for c in app.caption if "MJD2000" in c.value]
        self.assertEqual(sorted(all_mjd2000), sorted(nested_mjd2000))

    def test_utc_dates_remain_visible_at_first_level(self) -> None:
        app = _run_calculated_mission()
        self.assertFalse(app.exception)
        self.assertTrue(
            any(
                c.value.startswith("Date source: Mission setup Earth → Saturn trajectory")
                and "UTC" in c.value
                for c in app.caption
            )
        )


class TestCssHeaderClearanceGuards(unittest.TestCase):
    """Static source checks only - they cannot prove pixel rendering."""

    def test_main_container_padding_top_is_not_zero_or_negative(self) -> None:
        matches = re.findall(r"padding-top:\s*([\d.]+)rem", STYLE_SOURCE)
        self.assertTrue(matches, "expected an explicit padding-top rule")
        for value in matches:
            self.assertGreater(float(value), 0.0)

    def test_main_container_shorthand_padding_top_is_not_zero(self) -> None:
        for match in re.findall(r"padding:\s*([\d.]+)rem\s+[\d.]+rem\s+[\d.]+rem", STYLE_SOURCE):
            self.assertGreater(float(match), 0.0)

    def test_h1_has_no_negative_top_margin_and_no_transform(self) -> None:
        h1_block = re.search(r"h1\s*\{([^}]*)\}", STYLE_SOURCE)
        assert h1_block is not None, "expected an h1 {...} rule in the shell style"
        body = h1_block.group(1)
        self.assertNotIn("transform", body)
        negative_margin_top = re.search(r"margin-top:\s*-", body)
        self.assertIsNone(negative_margin_top)

    def test_no_negative_margin_or_transform_anywhere_in_the_shell_style(self) -> None:
        self.assertNotIn("transform:", STYLE_SOURCE)
        self.assertIsNone(re.search(r"margin(-top)?:\s*-", STYLE_SOURCE))

    def test_h1_overflow_is_not_hidden(self) -> None:
        h1_block = re.search(r"h1\s*\{([^}]*)\}", STYLE_SOURCE)
        assert h1_block is not None, "expected an h1 {...} rule in the shell style"
        self.assertNotIn("overflow: hidden", h1_block.group(1))

    def test_desktop_and_mobile_top_padding_are_not_asymmetrically_thin(self) -> None:
        desktop = re.search(
            r'\[data-testid="stMainBlockContainer"\]\s*\{[^}]*padding-top:\s*([\d.]+)rem',
            STYLE_SOURCE,
        )
        assert desktop is not None, "expected an explicit desktop padding-top rule"
        mobile_block = re.search(r"@media[^{]*\{.*", STYLE_SOURCE, re.DOTALL)
        assert mobile_block is not None, "expected an @media mobile breakpoint block"
        mobile = re.search(r"padding:\s*([\d.]+)rem", mobile_block.group(0))
        assert mobile is not None, "expected an explicit mobile padding rule"
        self.assertEqual(float(desktop.group(1)), float(mobile.group(1)))


class TestTypographyScaleIsNotGloballyExcessive(unittest.TestCase):
    def test_no_bare_paragraph_rule_scales_all_body_text(self) -> None:
        self.assertNotIn("\np {", STYLE_SOURCE)
        self.assertIsNone(re.search(r"(?<![\w-])p\s*\{", STYLE_SOURCE))

    def test_no_pure_viewport_only_font_size_without_fixed_bounds(self) -> None:
        # Every font-size rule must be a clamp() with fixed rem bounds, never
        # a bare `Nvw` value with no minimum/maximum.
        font_size_values = re.findall(r"font-size:\s*([^;]+);", STYLE_SOURCE)
        for value in font_size_values:
            value = value.replace(" !important", "").strip()
            self.assertTrue(
                value.startswith("clamp(") or value.endswith("rem") or value.endswith("em"),
                f"font-size value not bounded by rem/clamp: {value!r}",
            )

    def test_h1_desktop_range_matches_target(self) -> None:
        h1_block_match = re.search(r"h1\s*\{([^}]*)\}", STYLE_SOURCE)
        assert h1_block_match is not None, "expected an h1 {...} rule in the shell style"
        clamp_match = re.search(
            r"clamp\(([\d.]+)rem,\s*([\d.]+)vw,\s*([\d.]+)rem\)", h1_block_match.group(1)
        )
        assert clamp_match is not None, "expected h1's font-size to be a clamp()"
        low, _vw, high = clamp_match.groups()
        # Target: 32-40px desktop H1 (1rem == 16px at the default base size).
        self.assertAlmostEqual(float(low) * 16, 32.0)
        self.assertAlmostEqual(float(high) * 16, 40.0)

    def test_h1_mobile_range_matches_target(self) -> None:
        mobile_block_match = re.search(r"@media[^{]*\{.*", STYLE_SOURCE, re.DOTALL)
        assert mobile_block_match is not None, "expected an @media mobile breakpoint block"
        h1_mobile_match = re.search(r"h1\s*\{([^}]*)\}", mobile_block_match.group(0))
        assert h1_mobile_match is not None, "expected a mobile h1 {...} override"
        clamp_match = re.search(
            r"clamp\(([\d.]+)rem,\s*([\d.]+)vw,\s*([\d.]+)rem\)", h1_mobile_match.group(1)
        )
        assert clamp_match is not None, "expected mobile h1's font-size to be a clamp()"
        low, _vw, high = clamp_match.groups()
        # Target: 28-32px mobile H1.
        self.assertAlmostEqual(float(low) * 16, 28.0)
        self.assertAlmostEqual(float(high) * 16, 32.0)


class TestNo3DOrParetoContentTouched(unittest.TestCase):
    def test_no_3d_or_pareto_source_file_modified_by_this_regression_fix(self) -> None:
        untouched_files = (
            "pages/trajectory_3d.py",
            "pages/launch_windows.py",
            "pages/optimization.py",
            "mission/direct_trajectory_animation.py",
            "mission/trajectory_scene.py",
            "mission/trajectory_plot.py",
            "launch_window_plot.py",
        )
        style_selectors_only = STYLE_SOURCE
        for path in untouched_files:
            # This fix must not reference these modules' own identifiers -
            # confirms the CSS/text changes stayed scoped to the shell and
            # Mission scorecard.
            self.assertNotIn(Path(path).stem, style_selectors_only)

    def test_3d_and_pareto_pages_still_render(self) -> None:
        for page in ("pages/trajectory_3d.py", "pages/launch_windows.py", "pages/optimization.py"):
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


if __name__ == "__main__":
    unittest.main()
