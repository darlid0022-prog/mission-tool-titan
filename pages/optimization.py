"""Connected mission trade-space Pareto front.

This fixed 1,176-point study is independent of the live Mission setup
inputs (locked launch window, fixed default payload) - see
mission/pareto.py - so this page needs no session_state from other pages.
"""

import streamlit as st

from app_services import PARETO_MODEL_VERSION, compute_cached_pareto_front
from mission.pareto_plot import (
    build_pareto_front_figure,
    build_pareto_table,
    select_pareto_highlights,
)
from mission.ui_text import UI_TEXT

st.header(UI_TEXT["pareto_header"])
st.caption(UI_TEXT["pareto_caption"])
with st.container(border=True):
    with st.spinner(UI_TEXT["pareto_spinner"]):
        pareto_result = compute_cached_pareto_front(PARETO_MODEL_VERSION)
    pareto_highlights = select_pareto_highlights(pareto_result)
    pareto_figure = build_pareto_front_figure(pareto_result)
    st.plotly_chart(
        pareto_figure,
        width="stretch",
        height=540,
        key="connected_mission_pareto_front",
        config={"displaylogo": False, "scrollZoom": True},
    )
    # Accessible alternative to the chart above: every plotted point (regular
    # Pareto front plus the two highlighted references) as a keyboard- and
    # screen-reader-navigable table, for anyone who cannot read the chart and
    # for exporting/verifying the exact numbers. Built from the figure itself,
    # so it can never drift from what is actually plotted.
    with st.expander("View Pareto front data as a table"):
        st.dataframe(build_pareto_table(pareto_figure), width="stretch")
    baseline = pareto_highlights.baseline
    optimum = pareto_highlights.delta_v_optimum
    delta_v_percent = 100.0 * (baseline.total_delta_v_m_s / optimum.total_delta_v_m_s - 1.0)
    duration_percent = 100.0 * (baseline.total_duration_days / optimum.total_duration_days - 1.0)
    mass_percent = 100.0 * (baseline.wet_mass_kg / optimum.wet_mass_kg - 1.0)
    st.caption(
        UI_TEXT["pareto_comparison"].format(
            delta_v_difference=baseline.total_delta_v_m_s - optimum.total_delta_v_m_s,
            delta_v_percent=delta_v_percent,
            duration_difference=baseline.total_duration_days - optimum.total_duration_days,
            duration_percent=duration_percent,
            mass_difference=baseline.wet_mass_kg - optimum.wet_mass_kg,
            mass_percent=mass_percent,
        )
    )
