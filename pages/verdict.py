"""Transition destination for the v0.3 Verdict step."""

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
    title_key="verdict_title", introduction_key="verdict_introduction", scope_key="badge_connected"
)
render_mission_progress(UI_V030_TEXT["verdict_title"])
render_calculation_status(state)
render_scenario_summary(state)
st.info(UI_V030_TEXT["verdict_transition_note"])
render_navigation_actions(
    previous=("pages/budget.py", UI_V030_TEXT["budget_title"]),
    next_=("pages/technical_details.py", UI_V030_TEXT["verdict_details"]),
)
