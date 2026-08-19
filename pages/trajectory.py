"""Transition hub for the v0.3 Trajectory step."""

import streamlit as st

from mission.ui_components import (
    render_calculation_status,
    render_mission_progress,
    render_navigation_actions,
    render_scenario_summary,
    render_step_header,
)
from mission.ui_session_state import load_ui_state
from mission.ui_text import UI_V030_TEXT

state = load_ui_state(st.session_state)
render_step_header(
    title_key="trajectory_title",
    introduction_key="trajectory_introduction",
    scope_key="badge_connected",
)
render_mission_progress(UI_V030_TEXT["trajectory_title"])
render_calculation_status(state)
render_scenario_summary(state)
st.info(UI_V030_TEXT["trajectory_transition_note"])
with st.container(horizontal=True):
    st.page_link(
        "pages/launch_windows.py",
        label=UI_V030_TEXT["trajectory_launch_windows"],
        icon=":material/search:",
    )
    st.page_link(
        "pages/trajectory_3d.py",
        label=UI_V030_TEXT["trajectory_open_3d"],
        icon=":material/3d_rotation:",
    )
render_navigation_actions(
    previous=("pages/mission_setup.py", UI_V030_TEXT["return_to_mission"]),
    next_=("pages/budget.py", UI_V030_TEXT["trajectory_continue"]),
)
