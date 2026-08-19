"""Transition hub for the v0.3 Trajectory step."""

import streamlit as st

import app_services
import launch_window_service as lw
from mission.ui_components import (
    render_calculation_status,
    render_mission_progress,
    render_navigation_actions,
    render_step_header,
)
from mission.ui_format import build_duration_breakdown, format_duration_days
from mission.ui_presentation import LAST_VALID_MISSION_BUNDLE_STATE_KEY
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

active_candidate = st.session_state.get(lw.ACTIVE_LAUNCH_WINDOW_CANDIDATE_STATE_KEY)
bundle = st.session_state.get(LAST_VALID_MISSION_BUNDLE_STATE_KEY)
reference_duration_days: float | None = None
duration_breakdown = None
if isinstance(active_candidate, lw.LaunchWindowCandidate):
    reference_duration_days = active_candidate.total_duration_days
    try:
        duration_breakdown = build_duration_breakdown(
            total_days=active_candidate.total_duration_days,
            interplanetary_days=active_candidate.time_of_flight_days,
            saturn_phase_days=(
                active_candidate.total_duration_days - active_candidate.time_of_flight_days
            ),
        )
    except ValueError:
        duration_breakdown = None
elif isinstance(bundle, app_services.MissionBundle):
    reference_duration_days = bundle.mission_duration_days
    connected_first_order = bundle.connected_first_order
    earth_saturn_trajectory = bundle.earth_saturn_trajectory
    if (
        connected_first_order is not None
        and earth_saturn_trajectory.departure_mjd2000 is not None
        and earth_saturn_trajectory.arrival_mjd2000 is not None
    ):
        try:
            duration_breakdown = build_duration_breakdown(
                total_days=bundle.mission_duration_days,
                interplanetary_days=(
                    float(earth_saturn_trajectory.arrival_mjd2000)
                    - float(earth_saturn_trajectory.departure_mjd2000)
                ),
                saturn_phase_days=connected_first_order.saturn_capture.time_of_flight_days,
            )
        except ValueError:
            duration_breakdown = None

last_search = st.session_state.get("launch_window_result")
if isinstance(last_search, lw.LaunchWindowSearchResult):
    search_status = f"{len(last_search.candidates)} {UI_V030_TEXT['trajectory_search_candidates']}"
else:
    search_status = UI_V030_TEXT["trajectory_no_search"]

direct_card_column, launch_card_column = st.columns(2, gap="medium")
with direct_card_column:
    with st.container(
        border=True,
        key="trajectory_direct_card",
        width="stretch",
        height="stretch",
    ):
        st.subheader(UI_V030_TEXT["trajectory_direct_3d_section"])
        st.caption(UI_V030_TEXT["trajectory_direct_3d_description"])
        st.write(f"**{UI_V030_TEXT['active_scenario']}** · {state.active_scenario.source_label}")
        if duration_breakdown is not None:
            st.write(
                f"**{UI_V030_TEXT['trajectory_duration_complete']}** · "
                f"{duration_breakdown.synthesis_text}"
            )
            with st.expander(UI_V030_TEXT["trajectory_duration_complete"]):
                st.caption(
                    f"{UI_V030_TEXT['trajectory_duration_complete']} = "
                    f"{UI_V030_TEXT['trajectory_duration_interplanetary']} + "
                    f"{UI_V030_TEXT['trajectory_duration_saturn_phase']}"
                )
                st.write(duration_breakdown.detail_text)
        elif reference_duration_days is not None:
            st.caption(
                f"{UI_V030_TEXT['trajectory_reference_duration']} · "
                f"{format_duration_days(reference_duration_days)}"
            )
            st.caption(UI_V030_TEXT["trajectory_duration_unavailable"])
        if st.button(
            UI_V030_TEXT["trajectory_open_3d"],
            icon=":material/3d_rotation:",
            type="primary",
        ):
            st.switch_page("pages/trajectory_3d.py")

with launch_card_column:
    with st.container(
        border=True,
        key="trajectory_launch_card",
        width="stretch",
        height="stretch",
    ):
        st.subheader(UI_V030_TEXT["trajectory_launch_windows_section"])
        st.caption(UI_V030_TEXT["trajectory_launch_windows_description"])
        st.write(f"**{UI_V030_TEXT['trajectory_last_search']}** · {search_status}")
        if st.button(
            UI_V030_TEXT["trajectory_launch_windows"],
            icon=":material/search:",
        ):
            st.switch_page("pages/launch_windows.py")
render_navigation_actions(
    previous=("pages/mission_setup.py", UI_V030_TEXT["return_to_mission"]),
    next_=("pages/budget.py", UI_V030_TEXT["trajectory_continue"]),
)
