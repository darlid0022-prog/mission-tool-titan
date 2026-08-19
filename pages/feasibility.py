"""Isolated single-stage chemical feasibility study, rebuilt from the
mission-setup inputs stored in session_state.
"""

import streamlit as st

import app_services
from mission.ui_text import UI_TEXT

bundle = app_services.require_mission_bundle()
if bundle is None:
    st.stop()

single_stage_feasibility = bundle.single_stage_feasibility
saturn_subtotal_m_s = (
    bundle.complete_dv_budget.saturn_capture_to_ellipse_m_s
    + bundle.complete_dv_budget.saturn_staging_circularisation_m_s
)

st.header(UI_TEXT["single_stage_feasibility_header"])
st.caption(UI_TEXT["single_stage_feasibility_caption"])
with st.container(border=True):
    f1, f2, f3 = st.columns(3)
    f1.metric(
        UI_TEXT["single_stage_required_delta_v"],
        f"{single_stage_feasibility.required_delta_v_m_s:,.3f} m/s",
    )
    f2.metric(
        UI_TEXT["single_stage_maximum_delta_v"],
        f"{single_stage_feasibility.maximum_feasible_delta_v_m_s:,.3f} m/s",
    )
    f3.metric(
        UI_TEXT["single_stage_threshold_factor"],
        f"{single_stage_feasibility.threshold_exceedance_factor:.3f}×",
    )
    if single_stage_feasibility.is_feasible:
        st.success(UI_TEXT["single_stage_feasible"])
    else:
        st.info(UI_TEXT["single_stage_infeasible_finding"])
    st.caption(
        UI_TEXT["single_stage_model_source"].format(
            model_version=single_stage_feasibility.model_version
        )
    )
    if single_stage_feasibility.maximum_feasible_delta_v_m_s > 0.0:
        vehicle_bound = single_stage_feasibility.threshold_exceedance_factor
        launcher_bound = (
            saturn_subtotal_m_s / single_stage_feasibility.maximum_feasible_delta_v_m_s
        )
        st.caption(
            UI_TEXT["single_stage_allocation_bracket"].format(
                vehicle_bound=vehicle_bound,
                required_delta_v_m_s=single_stage_feasibility.required_delta_v_m_s,
                launcher_bound=launcher_bound,
                saturn_subtotal_m_s=saturn_subtotal_m_s,
            )
        )
