"""RENDERED-STRING checks for the reference Earth-Saturn-Titan mission.

DO NOT MERGE THIS FILE WITH tests/test_numeric_invariants_v030.py.

This file asserts on what a user actually SEES (exact rendered strings,
via Streamlit's AppTest), not on the underlying floats. It is EXPECTED to
change whenever display policy changes - rounding, thousands separators,
wording - and that is fine: this file's whole job is to pin down the
current display contract, not to guard the physics. Every change here must
still be justified in its own commit message (before/after + reason), but
a red test here is not by itself evidence of a scientific regression.

tests/test_numeric_invariants_v030.py is the file that guards the
underlying values (compute_mission_bundle called directly, no rendering).
If you are here to fix a physics/model regression, you are in the wrong
file - go there instead.
"""

import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from mission.bodies import resolve_body
from mission.launch_search_ephemeris import solve_earth_saturn_lambert
from mission.models import Leg, TrajectoryResult

APP_PATH = Path(__file__).resolve().parents[1] / "app.py"

# The current display contract for the audited reference scenario (see
# docs/audit_science_budget_v030.md). Every entry is a literal substring the
# application renders today - not a re-derivation of the underlying value.
REQUIRED_STRINGS = (
    "7,381.480 m/s",
    "2,182.991 m/s",
    "2,966.182 m/s",
    "12,530.653 m/s",
    "5,149.173 m/s",
    "≈108.83 km²/s²",
    "≈10.432 km/s",
    "6,490.7 m/s",
    "1.167",
    "118.0°",
    "9,820 km",
    "2,183.0 m/s",
    "0.781",
    "3.354 days",
    "2,856.0 days",
    "2,859.354",
    "54.22",
    "224 kg",
    "11,914 kg",
    "12,138 kg",
    "3,833.463 m/s",
    "3.269×",
    "2,280.8 m/s",
    "4,501.6 m/s",
    "6,782.4 m/s",
    "1.125 days",
    "4,570 km",
    "1,257.5 m/s",
    "1,049.8 m/s",
    "862.7 m/s",
    "2,120.3 m/s",
    "5.133 days",
    "2,402.6 m/s",
    "2,002.6 m/s",
    "151.2 km",
    "72.003°",
    "19.677°",
    "11.780°",
    "3,591.9 m/s",
    "4,181.3 m/s",
    "2,040.9 m/s",
)


def _earth_saturn_leg() -> Leg:
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


def _earth_saturn_result() -> dict:
    return {
        "note": "Test Earth-to-Saturn result",
        "dv_budget": {
            "dV from LEO": 1_000.0,
            "dV DSM/Fly-By": 0.0,
            "dV Capture at Destination": 999_999.0,
        },
        "dv_total": 1_000.0,
        "earth_saturn_leg": _earth_saturn_leg(),
    }


def _rendered_text(app: AppTest) -> str:
    """Concatenate every text-bearing element's value into one search string."""
    collections = (
        app.header,
        app.subheader,
        app.markdown,
        app.caption,
        app.metric,
        app.info,
        app.warning,
        app.success,
    )
    parts = []
    for collection in collections:
        for element in collection:
            value = getattr(element, "value", None)
            if isinstance(value, str):
                parts.append(value)
            label = getattr(element, "label", None)
            if isinstance(label, str):
                parts.append(label)
    return " | ".join(parts)


class TestAuditedDisplayStringsAreCurrent(unittest.TestCase):
    """One combined baseline run per page group, not per assertion, to keep
    this test's own runtime bounded even though it visits every relevant
    page for the reference scenario."""

    @classmethod
    def setUpClass(cls) -> None:
        with patch(
            "app_services.compute_cached_trajectory", return_value=_earth_saturn_result()
        ):
            app = AppTest.from_file(str(APP_PATH))
            app.run(timeout=30)
            calculate = next(b for b in app.button if "Calculate" in b.label)
            app = calculate.click().run(timeout=30)
            cls.mission_setup_text = _rendered_text(app)

            budget = app.switch_page("pages/budget.py").run(timeout=30)
            cls.budget_text = _rendered_text(budget)

            saturn_studies = app.switch_page("pages/saturn_system_studies.py").run(timeout=30)
            cls.saturn_studies_text = _rendered_text(saturn_studies)

            feasibility = app.switch_page("pages/feasibility.py").run(timeout=30)
            cls.feasibility_text = _rendered_text(feasibility)

            gravity_assists = app.switch_page("pages/gravity_assists.py").run(timeout=30)
            cls.gravity_assists_text = _rendered_text(gravity_assists)

            trajectory = app.switch_page("pages/trajectory.py").run(timeout=30)
            cls.trajectory_text = _rendered_text(trajectory)

            verdict = app.switch_page("pages/verdict.py").run(timeout=30)
            cls.verdict_text = _rendered_text(verdict)

        cls.combined_text = "\n".join(
            (
                cls.mission_setup_text,
                cls.budget_text,
                cls.saturn_studies_text,
                cls.feasibility_text,
                cls.gravity_assists_text,
                cls.trajectory_text,
                cls.verdict_text,
            )
        )

    def test_every_audited_display_string_is_current(self) -> None:
        missing = [value for value in REQUIRED_STRINGS if value not in self.combined_text]
        self.assertEqual(
            missing,
            [],
            f"Display string(s) no longer found verbatim in the rendered output: {missing}",
        )

    def test_mission_setup_mass_block_matches_budget_precision_and_separator(self) -> None:
        # docs/audit_science_budget_v030.md wording-and-scope batch, §2.2a.
        # Before: "223.9 kg" / "11913.6 kg" / "12137.5 kg" (one extra decimal,
        # no thousands separator - inverted relative to the Budget detail
        # view). After: matches Budget's own format_mass_kg() output exactly.
        for wrong in ("223.9 kg", "11913.6 kg", "12137.5 kg"):
            self.assertNotIn(wrong, self.mission_setup_text)
        for correct in ("224 kg", "11,914 kg", "12,138 kg"):
            self.assertIn(correct, self.mission_setup_text)

    def test_mission_setup_dv_sum_matches_connected_delta_v_formatting(self) -> None:
        # docs/audit_science_budget_v030.md wording-and-scope batch, §2.2b.
        # Before: "12531 m/s" (no separator, inconsistent with "Connected
        # delta-v" on the same page). After: "12,531 m/s", same as its
        # neighbor. Both metrics stay - only the format changed.
        self.assertNotIn("12531 m/s", self.mission_setup_text)
        self.assertIn("12,531 m/s", self.mission_setup_text)

    def test_isp_and_ballistic_coefficient_use_the_shared_formatter(self) -> None:
        # docs/audit_science_budget_v030.md wording-and-scope batch, §2.2d.
        self.assertIn("320 s", self.mission_setup_text)
        self.assertIn("38 kg/m²", self.saturn_studies_text)

    def test_the_earth_saturn_delta_v_sum_check_is_readable_in_the_interface(self) -> None:
        # This is a display-contract check (the three addend strings and the
        # total string are all on screen) - the actual sum is proved against
        # the real floats in test_numeric_invariants_v030.py.
        self.assertIn("7,381.480 m/s", self.combined_text)
        self.assertIn("2,182.991 m/s", self.combined_text)
        self.assertIn("2,966.182 m/s", self.combined_text)
        self.assertIn("12,530.653 m/s", self.combined_text)

    def test_no_isolated_study_value_appears_on_mission_setup_budget_or_verdict(self) -> None:
        # docs/audit_science_budget_v030.md wording-and-scope batch, acceptance
        # criterion 5: nothing from an isolated study reaches the connected
        # scorecard/Budget/Verdict. Covers both the single-stage exceedance
        # factor and the §2.2 allocation-bracket launcher bound (1.343x).
        for page_name, page_text in (
            ("Mission setup", self.mission_setup_text),
            ("Budget", self.budget_text),
            ("Verdict", self.verdict_text),
        ):
            with self.subTest(page=page_name):
                self.assertNotIn("3.269×", page_text)
                self.assertNotIn("1.343×", page_text)


if __name__ == "__main__":
    unittest.main()
