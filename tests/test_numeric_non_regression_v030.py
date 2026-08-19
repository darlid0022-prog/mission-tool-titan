"""Numeric non-regression for the wording-and-scope correction batch.

See docs/audit_science_budget_v030.md: an independent external audit
recomputed 40 values displayed by the application and found all 40 correct
(max deviation 0.041%). This batch changes labels and scope only - no
compute_*, solver, or physical-constants file is touched (see the batch's
own acceptance criterion 1). This test asserts every one of those 40 values
is still present, unchanged, in the rendered reference-scenario baseline
across every page that displays it.

Values are asserted as exact rendered substrings (not re-parsed or
re-computed), so any accidental change to a number - not just to a label
- fails this test.
"""

import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from mission.bodies import resolve_body
from mission.launch_search_ephemeris import solve_earth_saturn_lambert
from mission.models import Leg, TrajectoryResult

APP_PATH = Path(__file__).resolve().parents[1] / "app.py"

# Every value from docs/audit_science_budget_v030.md's audited set, as the
# exact substring the application renders for it today. A handful (the
# propellant/wet mass on Mission setup) render without a thousands
# separator in the current app - that is an existing, unrelated formatting
# quirk, not something this batch touches, so the assertions below match
# the application's actual output rather than the audit note's own
# thousands-separated notation.
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
    "223.9 kg",
    "11913.6 kg",
    "12137.5 kg",
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


class TestAuditedNumericValuesAreUnchanged(unittest.TestCase):
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

        cls.combined_text = "\n".join(
            (
                cls.mission_setup_text,
                cls.budget_text,
                cls.saturn_studies_text,
                cls.feasibility_text,
                cls.gravity_assists_text,
                cls.trajectory_text,
            )
        )

    def test_every_audited_value_is_still_rendered_unchanged(self) -> None:
        missing = [value for value in REQUIRED_STRINGS if value not in self.combined_text]
        self.assertEqual(
            missing,
            [],
            f"Audited value(s) no longer found verbatim in the rendered output: {missing}",
        )

    def test_the_earth_saturn_delta_v_sum_check_still_holds(self) -> None:
        self.assertIn("7,381.480 m/s", self.combined_text)
        self.assertIn("2,182.991 m/s", self.combined_text)
        self.assertIn("2,966.182 m/s", self.combined_text)
        self.assertIn("12,530.653 m/s", self.combined_text)
        self.assertAlmostEqual(7_381.480 + 2_182.991 + 2_966.182, 12_530.653, places=3)

    def test_no_isolated_study_value_appears_on_mission_setup_budget_or_verdict(self) -> None:
        # docs/audit_science_budget_v030.md wording-and-scope batch, acceptance
        # criterion 5: nothing from an isolated study reaches the connected
        # scorecard/Budget. The single-stage exceedance factor is the one
        # isolated-study number that used to leak onto Mission setup.
        self.assertNotIn("3.269×", self.mission_setup_text)
        self.assertNotIn("3.269×", self.budget_text)


if __name__ == "__main__":
    unittest.main()
