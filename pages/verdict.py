"""v0.3 Verdict step: cautious conclusions over the active stored result."""

from collections.abc import MutableMapping
from typing import cast

import streamlit as st

import app_services
import launch_window_service as lw
from mission.ui_components import (
    render_assumptions_and_limitations,
    render_bulleted_text,
    render_calculation_status,
    render_connected_budget,
    render_departure_energy,
    render_mission_progress,
    render_scenario_summary,
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
    )


state = load_ui_state(cast(MutableMapping[str, object], st.session_state))
render_step_header(
    title_key="verdict_title",
    introduction_key="verdict_introduction",
    scope_key="badge_connected",
)
render_mission_progress(UI_V030_TEXT["verdict_title"])
render_calculation_status(state)
render_scenario_summary(state)
if state.calculation_status is CalculationStatus.STALE:
    st.warning(UI_V030_TEXT["verdict_previous_result_note"])

active_candidate = st.session_state.get(lw.ACTIVE_LAUNCH_WINDOW_CANDIDATE_STATE_KEY)
bundle = st.session_state.get(LAST_VALID_MISSION_BUNDLE_STATE_KEY)
values: MissionBudgetPresentation | None = None
has_saturn_endpoint = False

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
    has_saturn_endpoint = True
elif isinstance(bundle, app_services.MissionBundle):
    values = _budget_from_bundle(bundle)
    has_saturn_endpoint = bundle.connected_first_order is not None

if values is None:
    st.info(UI_V030_TEXT["verdict_no_result_note"])
else:
    # The two lists below are the verdict: precise, honest statements of what
    # the model does and does not establish. They sit immediately under the
    # page title, ahead of every conclusion, final-state, and budget block,
    # so a reader hits them before anything else (see the docs/audit_science
    # _budget_v030.md wording-and-scope batch, §2.4: the previous "Model
    # conclusion" tautology added no information beyond these lists).
    st.header(UI_V030_TEXT["verdict_demonstrated_heading"])
    calculated_keys = [
        "verdict_calculates_departure",
        "verdict_calculates_dates",
        "verdict_calculates_injection",
        "verdict_calculates_total",
    ]
    if has_saturn_endpoint:
        calculated_keys.extend(
            ("verdict_calculates_saturn", "verdict_calculates_final_state")
        )
    if isinstance(bundle, app_services.MissionBundle):
        calculated_keys.append("verdict_calculates_mass")
    render_bulleted_text(calculated_keys)

    st.header(UI_V030_TEXT["verdict_excluded_heading"])
    render_bulleted_text(
        (
            "verdict_not_launcher",
            "verdict_not_allocation",
            "verdict_not_titan_encounter",
            "verdict_not_titan_capture",
            "verdict_not_gravity_assist",
            "verdict_not_propagation",
            "verdict_not_vehicle_design",
        )
    )

    # "Model conclusion" is retained only for scenarios where it states real
    # information (which historical model, or which non-Saturn scope
    # applies). The connected Earth-Saturn-Titan case previously repeated
    # only the scope already established above, so it is not rendered here.
    if state.active_scenario.kind is ActiveScenarioKind.CASSINI_HISTORICAL_REFERENCE:
        st.header(UI_V030_TEXT["verdict_conclusion_heading"])
        st.write(UI_V030_TEXT["verdict_historical_conclusion"])
    elif not has_saturn_endpoint:
        st.header(UI_V030_TEXT["verdict_conclusion_heading"])
        st.write(UI_V030_TEXT["verdict_non_saturn_conclusion"])

    st.header(UI_V030_TEXT["verdict_final_state_heading"])
    if state.active_scenario.kind is ActiveScenarioKind.CASSINI_HISTORICAL_REFERENCE:
        st.write(UI_V030_TEXT["verdict_historical_final_state"])
    elif has_saturn_endpoint:
        st.write(UI_V030_TEXT["verdict_final_state"])
        st.warning(UI_V030_TEXT["verdict_titan_exclusion"])
    else:
        st.write(UI_V030_TEXT["verdict_non_saturn_final_state"])

    render_departure_energy(values)
    render_connected_budget(values)
    st.caption(UI_V030_TEXT["verdict_allocation_limitation"])

    render_assumptions_and_limitations(
        (
            UI_V030_TEXT["verdict_assumption_dynamics"],
            UI_V030_TEXT["verdict_assumption_endpoint"],
            UI_V030_TEXT["verdict_assumption_isolated"],
        )
    )

with st.container(horizontal=True):
    st.page_link(
        "pages/mission_setup.py",
        label=UI_V030_TEXT["verdict_return_mission"],
        icon=":material/edit:",
    )
    st.page_link(
        "pages/technical_details.py",
        label=UI_V030_TEXT["verdict_details"],
        icon=":material/science:",
    )
    st.page_link(
        "pages/isolated_studies.py",
        label=UI_V030_TEXT["verdict_open_isolated"],
        icon=":material/experiment:",
    )
