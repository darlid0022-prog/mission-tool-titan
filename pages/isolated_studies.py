"""Index of legacy and isolated scientific studies."""

import streamlit as st

from mission.ui_components import render_scope_badge
from mission.ui_text import UI_V030_TEXT

st.title(UI_V030_TEXT["isolated_studies_title"])
render_scope_badge("badge_isolated")
render_scope_badge("badge_excluded")
st.caption(UI_V030_TEXT["isolated_studies_introduction"])
st.page_link(
    "pages/gravity_assists.py",
    label=UI_V030_TEXT["isolated_gravity"],
    icon=":material/rocket_launch:",
)
st.page_link(
    "pages/feasibility.py", label=UI_V030_TEXT["isolated_feasibility"], icon=":material/warning:"
)
st.page_link(
    "pages/saturn_system_studies.py",
    label=UI_V030_TEXT["isolated_saturn"],
    icon=":material/public:",
)
