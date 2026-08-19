"""Streamlit multi-page entry point for the Mission Design Calculator.

Page content lives under pages/; each page is its own script run
independently by st.navigation, so shared results travel through
st.session_state via app_services (see app_services.MissionSetupInputs /
app_services.require_mission_bundle). No business logic lives in this file.
"""

import streamlit as st

import app_services
from mission.ui_session_state import store_ui_state
from mission.ui_state import initial_ui_state
from mission.ui_state_migration import UiStateMigrationError, initialize_or_migrate_ui_state
from mission.ui_text import UI_TEXT, UI_V030_TEXT

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
if migration_warning := st.session_state.get(app_services.MISSION_QUERY_MIGRATION_WARNING_KEY):
    st.warning(migration_warning)

try:
    initialize_or_migrate_ui_state(st.session_state)
except UiStateMigrationError as exc:
    st.error(str(exc))
    store_ui_state(st.session_state, initial_ui_state())

pages = {
    UI_V030_TEXT["navigation_primary"]: [
        st.Page(
            "pages/mission_setup.py",
            title=UI_V030_TEXT["mission_title"],
            icon=":material/tune:",
            default=True,
        ),
        st.Page(
            "pages/trajectory.py",
            title=UI_V030_TEXT["trajectory_title"],
            icon=":material/route:",
        ),
        st.Page(
            "pages/budget.py",
            title=UI_V030_TEXT["budget_title"],
            icon=":material/calculate:",
        ),
        st.Page(
            "pages/verdict.py",
            title=UI_V030_TEXT["verdict_title"],
            icon=":material/fact_check:",
        ),
    ],
    UI_V030_TEXT["navigation_secondary"]: [
        st.Page(
            "pages/technical_details.py",
            title=UI_V030_TEXT["technical_details_title"],
            icon=":material/science:",
        ),
        st.Page(
            "pages/isolated_studies.py",
            title=UI_V030_TEXT["isolated_studies_title"],
            icon=":material/experiment:",
        ),
        st.Page("pages/launch_windows.py", title="Launch windows", visibility="hidden"),
        st.Page("pages/trajectory_3d.py", title="3D trajectory", visibility="hidden"),
        st.Page(
            "pages/saturn_system_studies.py", title="Saturn & Titan studies", visibility="hidden"
        ),
        st.Page("pages/feasibility.py", title="Feasibility", visibility="hidden"),
        st.Page("pages/optimization.py", title="Optimization", visibility="hidden"),
        st.Page("pages/gravity_assists.py", title="Gravity assists", visibility="hidden"),
    ],
}

navigation = st.navigation(pages)
navigation.run()
