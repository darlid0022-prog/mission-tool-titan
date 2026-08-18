"""Streamlit multi-page entry point for the Mission Design Calculator.

Page content lives under pages/; each page is its own script run
independently by st.navigation, so shared results travel through
st.session_state via app_services (see app_services.MissionSetupInputs /
app_services.require_mission_bundle). No business logic lives in this file.
"""

import streamlit as st

import app_services
from mission.ui_text import UI_TEXT

st.set_page_config(
    page_title="Mission Design — Titan",
    page_icon=":material/satellite_alt:",
    layout="wide",
)
st.title(":material/satellite_alt: Mission Design Calculator")
st.caption(UI_TEXT["app_caption"])

# Shared URLs restore their validated, simple mission inputs before navigation
# selects and renders any page. Derived physics/results are intentionally rebuilt
# later by app_services.compute_mission_bundle().
try:
    app_services.restore_mission_setup_from_query_params(st.query_params)
except ValueError as exc:
    st.warning(f"The shared mission link could not be restored: {exc}")
if migration_warning := st.session_state.get(
    app_services.MISSION_QUERY_MIGRATION_WARNING_KEY
):
    st.warning(migration_warning)

pages = [
    st.Page(
        "pages/mission_setup.py",
        title="Mission setup",
        icon=":material/tune:",
        default=True,
    ),
    st.Page(
        "pages/launch_windows.py",
        title="Launch windows",
        icon=":material/search:",
    ),
    st.Page(
        "pages/trajectory_3d.py",
        title="3D trajectory",
        icon=":material/3d_rotation:",
    ),
    st.Page(
        "pages/saturn_system_studies.py",
        title="Saturn & Titan studies",
        icon=":material/public:",
    ),
    st.Page(
        "pages/feasibility.py",
        title="Feasibility",
        icon=":material/warning:",
    ),
    st.Page(
        "pages/optimization.py",
        title="Optimization",
        icon=":material/query_stats:",
    ),
    st.Page(
        "pages/gravity_assists.py",
        title="Gravity assists",
        icon=":material/rocket_launch:",
    ),
]

navigation = st.navigation(pages)
navigation.run()
