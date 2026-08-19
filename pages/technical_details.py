"""Index of existing scientific-detail pages."""

import streamlit as st

from mission.ui_components import render_scope_badge
from mission.ui_text import UI_V030_TEXT

st.title(UI_V030_TEXT["technical_details_title"])
render_scope_badge("badge_technical")
st.caption(UI_V030_TEXT["technical_details_introduction"])
st.page_link(
    "pages/saturn_system_studies.py",
    label=UI_V030_TEXT["technical_saturn"],
    icon=":material/public:",
    query_params={"section": "technical"},
)
st.page_link(
    "pages/optimization.py", label=UI_V030_TEXT["technical_pareto"], icon=":material/query_stats:"
)
