"""Shared, presentation-only Streamlit components for the v0.3 workflow."""

from __future__ import annotations

from collections.abc import Iterable

import streamlit as st

from mission.ui_format import (
    format_approximate_c3_km2_s2,
    format_approximate_speed_km_s,
    format_delta_v_m_s,
    format_mass_kg,
    format_short_date_utc,
)
from mission.ui_presentation import MissionBudgetPresentation
from mission.ui_state import CalculationStatus, MissionUiState
from mission.ui_text import UI_V030_TEXT, UI_V030_TOOLTIPS

PRIMARY_STEPS = ("Mission", "Trajectory", "Budget", "Verdict")


def render_scope_badge(text_key: str) -> None:
    """Render a textual scope badge whose meaning never depends on color.

    Defines its scope at first encounter via a hover tooltip when one is
    catalogued for this badge (see UI_V030_TOOLTIPS) - e.g. "connected" is
    jargon-adjacent enough that it should not rely on the reader having
    already seen it defined elsewhere on a different page.
    """
    st.badge(UI_V030_TEXT[text_key], help=UI_V030_TOOLTIPS.get(text_key))


def render_step_header(*, title_key: str, introduction_key: str, scope_key: str) -> None:
    st.title(UI_V030_TEXT[title_key])
    st.caption(UI_V030_TEXT[introduction_key])
    render_scope_badge(scope_key)


def render_mission_progress(active_step: str) -> None:
    labels = [
        f"**{index}. {step}**" if step == active_step else f"{index}. {step}"
        for index, step in enumerate(PRIMARY_STEPS, start=1)
    ]
    st.caption(f"{UI_V030_TEXT['progress_label']} · " + " → ".join(labels))


def render_scenario_summary(state: MissionUiState) -> None:
    """Compact, first-level scenario identity: name and a short date only.

    Calculation status (current/stale) is rendered separately by
    render_calculation_status(), called immediately before this on every
    page that uses it - this function does not repeat it. The scenario ID
    and full ISO timestamp are technical serialization details, not part of
    the first-level summary: they remain fully accessible, unmodified, in a
    collapsed (but keyboard-operable) expander below it.
    """
    summary = f"{UI_V030_TEXT['active_scenario']} · {state.active_scenario.source_label}"
    if state.calculated_at is not None:
        summary += f" · {format_short_date_utc(state.calculated_at)}"
    st.caption(summary)
    with st.expander(UI_V030_TEXT["scenario_technical_metadata"]):
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
        st.caption(f"{UI_V030_TEXT['calculation_status_label']} · {message}")
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


def render_departure_energy(values: MissionBudgetPresentation) -> None:
    st.header(UI_V030_TEXT["budget_departure_heading"])
    st.caption(UI_V030_TEXT["budget_energy_note"])
    with st.container(horizontal=True):
        if values.c3_m2_s2 is None:
            st.info(UI_V030_TEXT["budget_c3_unavailable"])
        else:
            st.metric(
                UI_V030_TEXT["budget_c3_label"],
                format_approximate_c3_km2_s2(values.c3_m2_s2),
                help=UI_V030_TOOLTIPS["earth_c3"],
                border=True,
            )
        if values.earth_v_infinity_m_s is not None:
            st.metric(
                UI_V030_TEXT["budget_v_infinity_label"],
                format_approximate_speed_km_s(values.earth_v_infinity_m_s),
                help=UI_V030_TOOLTIPS["earth_v_infinity"],
                border=True,
            )


def render_connected_budget(values: MissionBudgetPresentation) -> None:
    st.header(UI_V030_TEXT["budget_injection_heading"])
    st.metric(
        UI_V030_TEXT["budget_injection_heading"],
        format_delta_v_m_s(values.earth_injection_m_s),
        help=UI_V030_TOOLTIPS["modeled_earth_injection"],
        border=True,
    )
    st.caption(UI_V030_TEXT["budget_allocation_explanation"])

    if values.saturn_capture_m_s is not None or values.saturn_circularization_m_s is not None:
        st.header(UI_V030_TEXT["budget_saturn_heading"])
        with st.container(horizontal=True):
            if values.saturn_capture_m_s is not None:
                st.metric(
                    UI_V030_TEXT["budget_capture_label"],
                    format_delta_v_m_s(values.saturn_capture_m_s),
                    help=UI_V030_TOOLTIPS["saturn_capture"],
                    border=True,
                )
            if values.saturn_circularization_m_s is not None:
                st.metric(
                    UI_V030_TEXT["budget_circularization_label"],
                    format_delta_v_m_s(values.saturn_circularization_m_s),
                    help=UI_V030_TOOLTIPS["saturn_circularization"],
                    border=True,
                )
        if values.saturn_circularization_m_s is not None:
            st.caption(UI_V030_TEXT["mission_titan_warning"])
        subtotal = values.saturn_subtotal_m_s
        if subtotal is not None:
            st.metric(
                UI_V030_TEXT["budget_saturn_subtotal"],
                format_delta_v_m_s(subtotal),
                help=UI_V030_TOOLTIPS["saturn_subtotal"],
            )
            st.caption(UI_V030_TEXT["budget_saturn_subtotal_explanation"])

    with st.container(border=True):
        st.subheader(UI_V030_TEXT["budget_total_heading"])
        st.metric(
            UI_V030_TEXT["budget_total_heading"],
            format_delta_v_m_s(values.connected_total_m_s),
            help=UI_V030_TOOLTIPS["connected_total"],
        )
        st.write(UI_V030_TEXT["budget_total_explanation"])


def render_simplified_mass(values: MissionBudgetPresentation) -> None:
    st.header(UI_V030_TEXT["budget_mass_heading"])
    st.caption(UI_V030_TEXT["budget_mass_note"])
    if (
        values.dry_mass_kg is None
        or values.propellant_mass_kg is None
        or values.wet_mass_kg is None
    ):
        st.info(UI_V030_TEXT["budget_candidate_mass_unavailable"])
        return
    with st.container(horizontal=True):
        st.metric(
            UI_V030_TEXT["budget_dry_mass"],
            format_mass_kg(values.dry_mass_kg),
            border=True,
        )
        st.metric(
            UI_V030_TEXT["budget_propellant_mass"],
            format_mass_kg(values.propellant_mass_kg),
            border=True,
        )
        st.metric(
            UI_V030_TEXT["budget_wet_mass"],
            format_mass_kg(values.wet_mass_kg),
            help=UI_V030_TOOLTIPS["simplified_wet_mass"],
            border=True,
        )


def render_bulleted_text(text_keys: Iterable[str]) -> None:
    st.markdown("\n".join(f"- {UI_V030_TEXT[key]}" for key in text_keys))


def render_navigation_actions(
    *, previous: tuple[str, str] | None = None, next_: tuple[str, str] | None = None
) -> None:
    with st.container(horizontal=True):
        if previous is not None:
            st.page_link(previous[0], label=previous[1], icon=":material/arrow_back:")
        if next_ is not None:
            st.page_link(next_[0], label=next_[1], icon=":material/arrow_forward:")
