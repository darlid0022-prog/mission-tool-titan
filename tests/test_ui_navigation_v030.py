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


def test_trajectory_hub_exposes_3d_and_real_launch_window_pareto_routes() -> None:
    source = (ROOT / "pages/trajectory.py").read_text()
    assert '"trajectory_direct_3d_section"' in source
    assert '"trajectory_launch_windows_section"' in source
    assert '"pages/trajectory_3d.py"' in source
    assert '"pages/launch_windows.py"' in source
    assert UI_V030_TEXT["trajectory_open_3d"] == "Open 3D trajectory"
    assert (
        UI_V030_TEXT["trajectory_launch_windows"]
        == "Explore launch windows and Pareto front"
    )


def test_trajectory_routes_keep_existing_capabilities_connected() -> None:
    trajectory_3d_source = (ROOT / "pages/trajectory_3d.py").read_text()
    launch_windows_source = (ROOT / "pages/launch_windows.py").read_text()
    for capability in (
        '"Animated"',
        '"Static"',
        "build_direct_animation_figure",
        "scene_figure_to_standalone_html",
        "build_scene_table",
    ):
        assert capability in trajectory_3d_source
    for capability in (
        "build_candidates_chart",
        "pareto_candidate_ranks=result.pareto_candidate_ranks",
        '"Use selected candidate as active scenario"',
    ):
        assert capability in launch_windows_source


def test_shell_style_is_centralized_and_cache_independent() -> None:
    app_source = (ROOT / "app.py").read_text()
    component_source = (ROOT / "mission/ui_components.py").read_text()
    style_source = (ROOT / "mission/ui_style.py").read_text()
    theme_source = (ROOT / ".streamlit/config.toml").read_text()

    assert "apply_ui_shell_style()" in app_source
    assert "st.title(" not in app_source
    assert "<style>" not in component_source
    assert "UI_SHELL_STYLE" in style_source
    assert "data-testid" in style_source
    assert "fonts.googleapis.com" not in theme_source


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


def test_budget_and_verdict_are_read_only_presentations() -> None:
    for path in ("pages/budget.py", "pages/verdict.py"):
        source = (ROOT / path).read_text()
        assert "compute_mission_bundle(" not in source
        assert "require_mission_bundle(" not in source
        assert "LAST_VALID_MISSION_BUNDLE_STATE_KEY" in source
        assert "render_calculation_status(state)" in source


def test_lot4_visible_copy_is_centralized() -> None:
    required = (
        "budget_energy_note",
        "budget_allocation_explanation",
        "budget_saturn_subtotal",
        "budget_total_explanation",
        "budget_mass_note",
        "verdict_final_state",
        "verdict_titan_exclusion",
        "verdict_allocation_limitation",
        "verdict_demonstrated_heading",
        "verdict_excluded_heading",
    )
    assert all(UI_V030_TEXT[key] for key in required)
