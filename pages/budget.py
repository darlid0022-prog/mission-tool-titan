"""v0.3 Budget step: presentation of already-calculated active results."""

from collections.abc import MutableMapping
from typing import cast

import streamlit as st

import app_services
import launch_window_service as lw
from mission.ui_components import (
    render_assumptions_and_limitations,
    render_calculation_status,
    render_connected_budget,
    render_departure_energy,
    render_mission_progress,
    render_navigation_actions,
    render_scenario_summary,
    render_simplified_mass,
    render_step_header,
)
from mission.ui_presentation import (
    LAST_VALID_MISSION_BUNDLE_STATE_KEY,
    MissionBudgetPresentation,
    build_candidate_budget_presentation,
    build_mission_budget_presentation,
)
from mission.ui_session_state import load_ui_state
from mission.ui_state import ActiveScenarioKind, CalculationStatus
from mission.ui_text import UI_V030_TEXT


def _budget_from_bundle(bundle: app_services.MissionBundle) -> MissionBudgetPresentation:
    connected = bundle.connected_first_order
    return build_mission_budget_presentation(
        trajectory=bundle.earth_saturn_trajectory,
        earth_injection_m_s=bundle.complete_dv_budget.earth_departure_m_s,
        saturn_capture_m_s=(
            bundle.complete_dv_budget.saturn_capture_to_ellipse_m_s
            if connected is not None or bundle.cassini_tour is not None
            else None
        ),
        saturn_circularization_m_s=(
            bundle.complete_dv_budget.saturn_staging_circularisation_m_s
            if connected is not None
            else None
        ),
        connected_total_m_s=bundle.dv_total,
        dry_mass_kg=bundle.mass["dry_mass_kg"],
        propellant_mass_kg=bundle.mass["propellant_mass_kg"],
        wet_mass_kg=bundle.mass["wet_mass_kg"],
    )


state = load_ui_state(cast(MutableMapping[str, object], st.session_state))
render_step_header(
    title_key="budget_title", introduction_key="budget_introduction", scope_key="badge_connected"
)
render_mission_progress(UI_V030_TEXT["budget_title"])
render_calculation_status(state)
render_scenario_summary(state)

if state.calculation_status is CalculationStatus.STALE:
    st.warning(UI_V030_TEXT["budget_previous_result_note"])

active_candidate = st.session_state.get(lw.ACTIVE_LAUNCH_WINDOW_CANDIDATE_STATE_KEY)
bundle = st.session_state.get(LAST_VALID_MISSION_BUNDLE_STATE_KEY)
values: MissionBudgetPresentation | None = None
assumptions: tuple[str, ...] = ()
if (
    state.active_scenario.kind is ActiveScenarioKind.LAUNCH_WINDOW_CANDIDATE
    and isinstance(active_candidate, lw.LaunchWindowCandidate)
):
    values = build_candidate_budget_presentation(
        earth_v_infinity_m_s=active_candidate.v_infinity_earth_m_s,
        c3_km2_s2=active_candidate.c3_km2_s2,
        earth_injection_m_s=active_candidate.delta_v_departure_m_s,
        saturn_capture_m_s=active_candidate.delta_v_capture_m_s,
        saturn_circularization_m_s=active_candidate.delta_v_titan_circularization_m_s,
        connected_total_m_s=active_candidate.delta_v_total_m_s,
    )
    assumptions = active_candidate.notes
elif isinstance(bundle, app_services.MissionBundle):
    values = _budget_from_bundle(bundle)
    if state.active_scenario.kind is ActiveScenarioKind.CASSINI_HISTORICAL_REFERENCE:
        st.info(UI_V030_TEXT["budget_historical_scope"])
    elif bundle.connected_first_order is None:
        st.info(UI_V030_TEXT["budget_non_saturn_scope"])
    else:
        assumptions = (
            bundle.connected_first_order.assumptions + bundle.connected_first_order.exclusions
        )

if values is None:
    st.info(UI_V030_TEXT["budget_no_result_note"])
else:
    render_departure_energy(values)
    render_connected_budget(values)
    render_simplified_mass(values)
    if assumptions:
        render_assumptions_and_limitations(assumptions)

render_navigation_actions(
    previous=("pages/trajectory.py", UI_V030_TEXT["trajectory_title"]),
    next_=("pages/verdict.py", UI_V030_TEXT["budget_continue"]),
)
