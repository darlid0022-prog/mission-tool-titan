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
