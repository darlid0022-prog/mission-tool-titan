"""Interactive 3D view of the complete connected Earth -> Saturn -> Titan
trajectory, rebuilt from the mission-setup inputs stored in session_state.
"""

import math

import streamlit as st

import app_services
from mission import colors
from mission.gravity_assist import compute_cassini_historical_tour
from mission.trajectory_plot import (
    build_cassini_historical_figure,
    build_complete_mission_figure,
    build_complete_mission_table,
)
from mission.trajectory_visualization import (
    CompleteMissionScene3D,
    MissionAnimationTimeline3D,
    build_complete_mission_scene,
    build_mission_animation_timeline,
    interpolate_spacecraft_position,
)
from mission.ui_text import UI_TEXT

ANIMATION_PHASE_OPTIONS = (
    "Earth → Saturn cruise",
    "Saturn arrival → staging",
    "Saturn → Titan",
)
ANIMATION_PHASE_SELECTOR_KEY = "mission_animation_phase"
ANIMATION_PHASE_ELAPSED_KEY = "mission_phase_elapsed_days"


def _reset_animation_phase_elapsed() -> None:
    """Return the marker to the start whenever the selected phase changes."""
    st.session_state[ANIMATION_PHASE_ELAPSED_KEY] = 0.0


def _animation_phase_timing(
    timeline: MissionAnimationTimeline3D,
    selected_phase: str,
) -> tuple[float, float]:
    """Return the absolute start and duration of one UI animation phase."""
    earth_duration = timeline.earth_saturn_duration_days
    staging_duration = timeline.saturn_staging_duration_days
    timings = {
        ANIMATION_PHASE_OPTIONS[0]: (0.0, earth_duration),
        ANIMATION_PHASE_OPTIONS[1]: (earth_duration, staging_duration),
        ANIMATION_PHASE_OPTIONS[2]: (
            earth_duration + staging_duration,
            timeline.saturn_titan_duration_days,
        ),
    }
    return timings[selected_phase]


def _absolute_animation_elapsed_days(
    selected_phase: str,
    phase_start_days: float,
    phase_duration_days: float,
    phase_elapsed_days: float,
) -> float:
    """Map phase-local UI time to the existing absolute animation timeline."""
    phase_end_days = phase_start_days + phase_duration_days
    if selected_phase != ANIMATION_PHASE_OPTIONS[-1] and phase_elapsed_days >= phase_duration_days:
        return math.nextafter(phase_end_days, phase_start_days)
    return phase_start_days + phase_elapsed_days


@st.fragment
def render_trajectory_animation(
    scene: CompleteMissionScene3D,
    timeline: MissionAnimationTimeline3D,
) -> None:
    """Rerun only the phase controls, marker, and chart when time changes."""
    st.session_state.setdefault(ANIMATION_PHASE_SELECTOR_KEY, ANIMATION_PHASE_OPTIONS[0])
    st.session_state.setdefault(ANIMATION_PHASE_ELAPSED_KEY, 0.0)
    selected_phase = st.segmented_control(
        UI_TEXT["mission_phase_selector"],
        ANIMATION_PHASE_OPTIONS,
        required=True,
        key=ANIMATION_PHASE_SELECTOR_KEY,
        help=UI_TEXT["mission_phase_selector_help"],
        on_change=_reset_animation_phase_elapsed,
        width="stretch",
    )
    assert isinstance(selected_phase, str)
    phase_start_days, phase_duration_days = _animation_phase_timing(timeline, selected_phase)
    saved_phase_elapsed = float(st.session_state[ANIMATION_PHASE_ELAPSED_KEY])
    if not 0.0 <= saved_phase_elapsed <= phase_duration_days:
        st.session_state[ANIMATION_PHASE_ELAPSED_KEY] = 0.0

    phase_elapsed_days = st.slider(
        UI_TEXT["phase_elapsed_time"],
        min_value=0.0,
        max_value=float(phase_duration_days),
        step=float(phase_duration_days / 20_000.0),
        format="%.2f days" if phase_duration_days >= 100.0 else "%.4f days",
        key=ANIMATION_PHASE_ELAPSED_KEY,
        help=UI_TEXT["phase_elapsed_time_help"],
    )
    elapsed_days = _absolute_animation_elapsed_days(
        selected_phase,
        phase_start_days,
        phase_duration_days,
        phase_elapsed_days,
    )
    spacecraft_position = interpolate_spacecraft_position(timeline, elapsed_days)
    with st.container(horizontal=True):
        st.metric(
            UI_TEXT["current_elapsed_time"],
            f"{spacecraft_position.elapsed_days:,.2f} days",
            border=True,
        )
        st.metric(
            UI_TEXT["current_mission_phase"],
            selected_phase,
            border=True,
        )
    # Same phase, same color as the moving 3D marker (see
    # colors.ANIMATION_PHASE_COLORS) and as the Saturn & Titan studies page.
    current_phase_color = colors.ANIMATION_PHASE_COLORS.get(selected_phase, colors.LAUNCH)
    st.badge(
        current_phase_color.label,
        color=colors.BADGE_COLOR[current_phase_color.label],
    )
    trajectory_figure = build_complete_mission_figure(scene, spacecraft_position)
    st.plotly_chart(
        trajectory_figure,
        width="stretch",
        height=720,
        key="complete_mission_trajectory_3d",
        config={"displaylogo": False, "scrollZoom": True},
    )
    # Accessible alternative to the chart above: every curve and marker point
    # (both panels), as a keyboard- and screen-reader-navigable table, for
    # anyone who cannot read the 3D chart and for exporting/verifying the
    # exact coordinates. Built from the figure itself, so it can never drift
    # from what is actually plotted.
    with st.expander("View trajectory data as a table"):
        st.dataframe(build_complete_mission_table(trajectory_figure), width="stretch")


bundle = app_services.require_mission_bundle()
if bundle is None:
    st.stop()

mission_inputs = app_services.load_mission_setup_inputs()
if (
    mission_inputs is not None
    and mission_inputs.trajectory_type == app_services.TRAJECTORY_TYPE_CASSINI_HISTORICAL
):
    st.header(UI_TEXT["trajectory_3d_header"])
    st.caption("Cassini historical VVEJGA tour — exact documented encounter states.")
    historical_figure = build_cassini_historical_figure(compute_cassini_historical_tour())
    st.plotly_chart(
        historical_figure,
        width="stretch",
        height=720,
        key="cassini_historical_trajectory_3d",
        config={"displaylogo": False, "scrollZoom": True},
    )
    st.stop()

# Only connected Saturn->Titan missions include staging and Titan-transfer studies
# required to build the full 3D scene. For planet-only arrivals show an informative
# message and stop early instead of failing with attribute errors.
if bundle.staging_result is None or bundle.titan_transfer is None:
    st.info("3D animation is available only for connected Saturn->Titan missions. Select Titan to view the full scene.")
    st.stop()

st.header(UI_TEXT["trajectory_3d_header"])
st.caption(UI_TEXT["trajectory_3d_caption"])
st.warning(
    "This animated scene renders the legacy Saturn arrival-to-staging and "
    "Saturn → Titan transfer studies (Saturn & Titan studies page), not the "
    "authoritative hyperbolic-arrival-and-capture model the connected delta-v budget "
    "on Mission setup is computed from. Its 'Titan orbit'/'Titan encounter' labels "
    "refer to that legacy model's simplified Titan-centered capture, which is not "
    "included in the connected budget."
)
with st.container(border=True):
    trajectory_scene_key = (
        bundle.earth_saturn_trajectory.departure_mjd2000,
        bundle.earth_saturn_trajectory.arrival_mjd2000,
        bundle.staging_result.periapsis_radius_m,
        bundle.staging_result.staging_radius_m,
        bundle.titan_transfer.titan_orbit_radius_m,
    )
    cached_scene = st.session_state.get("trajectory_scene")
    cached_timeline = st.session_state.get("trajectory_timeline")
    if (
        st.session_state.get("trajectory_scene_key") != trajectory_scene_key
        or not isinstance(cached_scene, CompleteMissionScene3D)
        or not isinstance(cached_timeline, MissionAnimationTimeline3D)
    ):
        trajectory_scene = build_complete_mission_scene(bundle.complete_mission)
        trajectory_timeline = build_mission_animation_timeline(
            trajectory_scene,
            bundle.complete_mission,
        )
        st.session_state["trajectory_scene_key"] = trajectory_scene_key
        st.session_state["trajectory_scene"] = trajectory_scene
        st.session_state["trajectory_timeline"] = trajectory_timeline
    render_trajectory_animation(
        st.session_state["trajectory_scene"],
        st.session_state["trajectory_timeline"],
    )
