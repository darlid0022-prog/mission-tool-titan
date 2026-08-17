"""Streamlit multi-page entry point for the Mission Design Calculator.

Page content lives under pages/; each page is its own script run
independently by st.navigation, so shared results travel through
st.session_state via app_services (see app_services.MissionSetupInputs /
app_services.require_mission_bundle). No business logic lives in this file.
"""

import streamlit as st

from mission.ui_text import UI_TEXT

st.set_page_config(
    page_title="Mission Design — Titan",
    page_icon=":material/satellite_alt:",
    layout="wide",
)
st.title(":material/satellite_alt: Mission Design Calculator")
st.caption(UI_TEXT["app_caption"])

pages = [
    st.Page(
        "pages/mission_setup.py",
        title="Mission setup",
        icon=":material/tune:",
        default=True,
    ),
]

navigation = st.navigation(pages)
navigation.run()
