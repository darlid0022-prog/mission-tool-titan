"""Shared, presentation-only Streamlit components for the v0.3 workflow."""

from __future__ import annotations

from collections.abc import Iterable

import streamlit as st

from mission.ui_state import CalculationStatus, MissionUiState
from mission.ui_text import UI_V030_TEXT

PRIMARY_STEPS = ("Mission", "Trajectory", "Budget", "Verdict")


def render_scope_badge(text_key: str) -> None:
    """Render a textual scope badge whose meaning never depends on color."""
    st.badge(UI_V030_TEXT[text_key])


def render_step_header(*, title_key: str, introduction_key: str, scope_key: str) -> None:
    st.title(UI_V030_TEXT[title_key])
    render_scope_badge(scope_key)
    st.caption(UI_V030_TEXT[introduction_key])


def render_mission_progress(active_step: str) -> None:
    labels = [f"{index}. {step}" for index, step in enumerate(PRIMARY_STEPS, start=1)]
    st.caption(f"{UI_V030_TEXT['progress_label']}: " + " → ".join(labels))
    st.caption(f"{UI_V030_TEXT['current_step']}: {active_step}")


def render_scenario_summary(state: MissionUiState) -> None:
    with st.container(border=True):
        st.subheader(UI_V030_TEXT["active_scenario"])
        st.write(state.active_scenario.source_label)
        st.caption(f"{UI_V030_TEXT['scenario_id']}: {state.active_scenario.scenario_id}")
        if state.calculated_at is not None:
            st.caption(f"{UI_V030_TEXT['calculated_at']}: {state.calculated_at.isoformat()}")


def render_calculation_status(state: MissionUiState) -> None:
    keys = {
        CalculationStatus.NO_RESULT: "status_empty",
        CalculationStatus.RUNNING: "status_running",
        CalculationStatus.CURRENT: "status_current",
        CalculationStatus.STALE: "status_stale",
        CalculationStatus.INPUT_ERROR: "status_input_error",
        CalculationStatus.NO_SOLUTION: "status_no_solution",
        CalculationStatus.TECHNICAL_ERROR: "status_technical_error",
    }
    message = UI_V030_TEXT[keys[state.calculation_status]]
    if state.calculation_status in {
        CalculationStatus.INPUT_ERROR,
        CalculationStatus.TECHNICAL_ERROR,
    }:
        st.error(message)
    elif state.calculation_status in {CalculationStatus.STALE, CalculationStatus.NO_SOLUTION}:
        st.warning(message)
    else:
        st.info(message)
    if state.last_error is not None:
        st.caption(state.last_error.message)


def render_model_scope_notice(message: str, *, titan_specific: bool = False) -> None:
    st.subheader(UI_V030_TEXT["model_scope"])
    st.info(message)
    if titan_specific:
        st.warning(UI_V030_TEXT["mission_titan_warning"])


def render_technical_details(lines: Iterable[str]) -> None:
    with st.expander(UI_V030_TEXT["technical_details_disclosure"]):
        for line in lines:
            st.write(line)


def render_assumptions_and_limitations(lines: Iterable[str]) -> None:
    with st.expander(UI_V030_TEXT["assumptions_and_limitations"]):
        for line in lines:
            st.write(line)


def render_navigation_actions(
    *, previous: tuple[str, str] | None = None, next_: tuple[str, str] | None = None
) -> None:
    with st.container(horizontal=True):
        if previous is not None:
            st.page_link(previous[0], label=previous[1], icon=":material/arrow_back:")
        if next_ is not None:
            st.page_link(next_[0], label=next_[1], icon=":material/arrow_forward:")
