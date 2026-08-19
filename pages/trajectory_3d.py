"""Interactive 3D view of the active direct or historical trajectory."""

import streamlit as st

import app_services
import launch_window_service as lw
from mission.direct_trajectory_animation import (
    DirectTrajectoryTimeline3D,
    build_baseline_lambert_segment,
    build_connected_capture_segment,
    build_direct_trajectory_timeline,
)
from mission.gravity_assist import compute_cassini_historical_tour
from mission.trajectory_plot import (
    CAMERA_PRESETS,
    DEFAULT_VIEW_PRESET,
    build_cassini_historical_figure,
    build_direct_animation_figure,
    build_scene_figure,
    build_scene_table,
    scene_figure_to_standalone_html,
)
from mission.trajectory_scene import (
    TrajectorySegment,
    segments_from_cassini_tour,
    segments_from_launch_search,
)
from mission.ui_text import UI_TEXT, UI_V030_TEXT

# Camera presets scoped to Saturn-centred geometry (Rings/Periapsis/Titan) are
# only offered once the segments themselves are Saturn-centred; a heliocentric
# tour only ever gets the frame-agnostic "Global" default.
SATURN_CENTRED_VIEW_PRESETS = tuple(CAMERA_PRESETS)
HELIOCENTRIC_VIEW_PRESETS = (DEFAULT_VIEW_PRESET,)


def render_generic_scene_section(
    segments: tuple[TrajectorySegment, ...],
    *,
    unit_label: str,
    key_prefix: str,
    available_presets: tuple[str, ...],
    file_name: str,
    animation_timeline: DirectTrajectoryTimeline3D | None = None,
) -> None:
    """Render one generic-segment 3D scene: view preset, scale toggle, chart,
    accessible table, and a standalone HTML export - identical code path for
    a direct Saturn-system scene or a gravity-assist tour, since both are
    already the same TrajectorySegment shape by the time they reach here.
    """
    with st.container(border=True):
        control_columns = st.columns(3 if animation_timeline is not None else 2)
        view_preset = control_columns[0].selectbox(
            "Camera view",
            available_presets,
            key=f"{key_prefix}_view_preset",
            help="Global is a wide default view; Rings/Periapsis/Titan are close-in "
            "presets on the Saturn-centred geometry.",
        )
        scale_choice = control_columns[1].radio(
            "Body marker scale",
            ("Enlarged (readable)", "Real scale"),
            key=f"{key_prefix}_scale_choice",
            horizontal=True,
            help="Real scale sizes body landmark markers proportionally to their actual "
            "radius (relative to the largest body shown) - small bodies may become hard "
            "to see, which is expected, honest behavior, not a rendering bug.",
        )
        real_scale = scale_choice == "Real scale"
        display_mode = "Static"
        if animation_timeline is not None:
            display_mode = control_columns[2].segmented_control(
                "Trajectory display",
                ("Animated", "Static"),
                default="Animated",
                key=f"{key_prefix}_display_mode",
                width="stretch",
            )
            st.caption(animation_timeline.interpolation_notice)
        if display_mode == "Animated" and animation_timeline is not None:
            # The trajectory type, UTC date range, and total elapsed time
            # used to be redrawn into the Plotly figure's own title on every
            # frame, which could get clipped at narrow widths. They are
            # rendered once here instead; the figure itself keeps only the
            # per-frame date/elapsed pair, inside its slider (see
            # mission/trajectory_plot.py::build_direct_animation_figure).
            first_frame = animation_timeline.frames[0]
            last_frame = animation_timeline.frames[-1]
            st.markdown(f"**{UI_V030_TEXT['trajectory_3d_animated_transfer_label']}**")
            st.caption(
                f"{first_frame.date_utc} → {last_frame.date_utc} · "
                f"elapsed {last_frame.elapsed_days:,.1f} days total"
            )
            figure = build_direct_animation_figure(segments, animation_timeline)
        else:
            figure = build_scene_figure(
                segments,
                unit_label=unit_label,
                view_preset=view_preset,
                real_scale=real_scale,
            )
        st.plotly_chart(
            figure,
            width="stretch",
            height=720,
            key=f"{key_prefix}_plotly_chart",
            config={"displaylogo": False, "scrollZoom": True},
        )

        with st.expander("View segment data as a table"):
            st.dataframe(build_scene_table(segments), width="stretch")

        st.download_button(
            "Download standalone HTML (offline-capable)",
            data=scene_figure_to_standalone_html(figure),
            file_name=file_name,
            mime="text/html",
            icon=":material/download:",
            key=f"{key_prefix}_html_download",
            on_click="ignore",
        )


bundle = app_services.require_mission_bundle()
if bundle is None:
    st.stop()

mission_inputs = app_services.load_mission_setup_inputs()
active_launch_candidate = st.session_state.get(lw.ACTIVE_LAUNCH_WINDOW_CANDIDATE_STATE_KEY)
selected_launch_candidate = st.session_state.get(lw.SELECTED_LAUNCH_WINDOW_CANDIDATE_STATE_KEY)
display_launch_candidate = (
    active_launch_candidate
    if isinstance(active_launch_candidate, lw.LaunchWindowCandidate)
    else selected_launch_candidate
)
if (
    isinstance(display_launch_candidate, lw.LaunchWindowCandidate)
    and display_launch_candidate.segments
    and mission_inputs is not None
    and mission_inputs.trajectory_type == app_services.TRAJECTORY_TYPE_DIRECT
):
    heliocentric_source = display_launch_candidate.segments_for_scene(
        reference_frame="heliocentric",
        distance_unit="AU",
    )
    saturn_source = display_launch_candidate.segments_for_scene(
        reference_frame="saturn_centred",
        distance_unit="km",
    )
    st.header(UI_TEXT["trajectory_3d_header"])
    scenario_status = (
        "Active launch-window candidate"
        if display_launch_candidate is active_launch_candidate
        else "Selected launch-window candidate"
    )
    st.caption(
        f"{scenario_status} · {display_launch_candidate.scenario_id} · scientific engine segments."
    )
    if heliocentric_source:
        heliocentric_timeline = build_direct_trajectory_timeline(
            heliocentric_source[0],
            scenario_id=display_launch_candidate.scenario_id,
        )
        st.subheader("Earth → Saturn (heliocentric)")
        render_generic_scene_section(
            segments_from_launch_search(
                heliocentric_source,
                reference_frame="heliocentric",
                distance_unit="AU",
            ),
            unit_label="AU",
            key_prefix="launch_window_heliocentric_scene",
            available_presets=HELIOCENTRIC_VIEW_PRESETS,
            file_name="launch_window_heliocentric_scene.html",
            animation_timeline=heliocentric_timeline,
        )
    if saturn_source:
        st.subheader("Saturn capture (Saturn-centred)")
        render_generic_scene_section(
            segments_from_launch_search(
                saturn_source,
                reference_frame="saturn_centred",
                distance_unit="km",
            ),
            unit_label="km",
            key_prefix="launch_window_saturn_scene",
            available_presets=SATURN_CENTRED_VIEW_PRESETS,
            file_name="launch_window_saturn_scene.html",
        )
    st.stop()

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

    st.subheader("Generic segment view (gravity-assist tour)")
    st.caption(
        "Same VVEJGA tour, rendered through the generic segment schema shared with "
        "direct-transfer missions - a preview of what will later host either a direct "
        "trajectory or a gravity-assist trajectory through one code path."
    )
    render_generic_scene_section(
        segments_from_cassini_tour(compute_cassini_historical_tour()),
        unit_label="m",
        key_prefix="cassini_tour_scene",
        available_presets=HELIOCENTRIC_VIEW_PRESETS,
        file_name="cassini_historical_tour_scene.html",
    )
    st.stop()

st.header(UI_TEXT["trajectory_3d_header"])
st.caption("Mission setup baseline · direct Lambert trajectory and connected capture.")
try:
    baseline_source = build_baseline_lambert_segment(bundle.earth_saturn_trajectory)
except ValueError as error:
    st.warning(
        "The cached baseline predates retained Lambert states, so animation is unavailable. "
        "Recalculate Mission setup to restore it. The static mission results are unchanged."
    )
    st.caption(str(error))
    st.stop()

baseline_timeline = build_direct_trajectory_timeline(
    baseline_source,
    scenario_id=(
        "mission-setup-"
        f"{baseline_source.departure_mjd2000:.6f}-{baseline_source.arrival_mjd2000:.6f}"
    ),
)
st.subheader("Earth → Saturn (heliocentric)")
render_generic_scene_section(
    segments_from_launch_search(
        (baseline_source,),
        reference_frame="heliocentric",
        distance_unit="AU",
    ),
    unit_label="AU",
    key_prefix="mission_setup_heliocentric_scene",
    available_presets=HELIOCENTRIC_VIEW_PRESETS,
    file_name="mission_setup_heliocentric_scene.html",
    animation_timeline=baseline_timeline,
)

if bundle.connected_first_order is not None:
    capture = bundle.connected_first_order.saturn_capture
    capture_start = baseline_source.arrival_mjd2000
    capture_source = build_connected_capture_segment(
        capture_start,
        capture_start + capture.time_of_flight_days,
        capture.periapsis_radius_m,
        capture.apoapsis_radius_m,
        64,
    )
    st.subheader("Saturn capture (Saturn-centred)")
    st.caption(
        "Static connected capture ellipse ending at Titan’s mean orbital radius; "
        "this is not a phased Titan encounter or Titan-centred insertion."
    )
    render_generic_scene_section(
        segments_from_launch_search(
            (capture_source,),
            reference_frame="saturn_centred",
            distance_unit="km",
        ),
        unit_label="km",
        key_prefix="mission_setup_saturn_scene",
        available_presets=SATURN_CENTRED_VIEW_PRESETS,
        file_name="mission_setup_saturn_scene.html",
    )
