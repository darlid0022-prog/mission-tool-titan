from pathlib import Path

from mission.ui_components import PRIMARY_STEPS
from mission.ui_text import UI_V030_TEXT

ROOT = Path(__file__).resolve().parents[1]


def test_primary_steps_have_required_order() -> None:
    assert PRIMARY_STEPS == ("Mission", "Trajectory", "Budget", "Verdict")


def test_navigation_registers_primary_secondary_and_legacy_destinations() -> None:
    source = (ROOT / "app.py").read_text()
    required = (
        "pages/mission_setup.py",
        "pages/trajectory.py",
        "pages/budget.py",
        "pages/verdict.py",
        "pages/technical_details.py",
        "pages/isolated_studies.py",
        "pages/launch_windows.py",
        "pages/trajectory_3d.py",
        "pages/saturn_system_studies.py",
        "pages/feasibility.py",
        "pages/optimization.py",
        "pages/gravity_assists.py",
    )
    assert all(path in source for path in required)
    assert source.index('"pages/mission_setup.py"') < source.index('"pages/trajectory.py"')
    assert source.index('"pages/trajectory.py"') < source.index('"pages/budget.py"')
    assert source.index('"pages/budget.py"') < source.index('"pages/verdict.py"')


def test_transitional_destinations_have_title_and_explanation() -> None:
    for path, title_key, introduction_key in (
        ("pages/trajectory.py", "trajectory_title", "trajectory_introduction"),
        ("pages/budget.py", "budget_title", "budget_introduction"),
        ("pages/verdict.py", "verdict_title", "verdict_introduction"),
        (
            "pages/technical_details.py",
            "technical_details_title",
            "technical_details_introduction",
        ),
        (
            "pages/isolated_studies.py",
            "isolated_studies_title",
            "isolated_studies_introduction",
        ),
    ):
        source = (ROOT / path).read_text()
        assert title_key in source
        assert introduction_key in source
        assert UI_V030_TEXT[title_key]
        assert UI_V030_TEXT[introduction_key]


def test_status_copy_is_not_color_only() -> None:
    for key in (
        "status_current",
        "status_stale",
        "status_running",
        "status_empty",
        "status_input_error",
        "status_no_solution",
        "status_technical_error",
    ):
        assert len(UI_V030_TEXT[key].split()) >= 3
