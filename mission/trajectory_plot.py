"""Plotly rendering for the pure complete-mission trajectory scene."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pandas as pd
import plotly.graph_objects as go
import pykep as pk
from plotly.subplots import make_subplots

from . import colors
from .direct_trajectory_animation import DirectTrajectoryFrame3D, DirectTrajectoryTimeline3D
from .gravity_assist import GravityAssistResult, MissionSegment, OrbitInsertionResult
from .trajectory_scene import TrajectorySegment
from .trajectory_visualization import (
    CompleteMissionScene3D,
    SpacecraftPosition3D,
    TrajectoryCurve3D,
)

# scene -> (panel label, unit) for the two 3D subplots build_complete_mission_figure
# always creates (see its make_subplots call below). Used only by
# build_complete_mission_table to label the accessible data-table alternative.
_SCENE_PANEL: dict[str, tuple[str, str]] = {
    "scene": ("Heliocentric transfer — Sun-centred J2000 ecliptic", "AU"),
    "scene2": ("Saturn system — Saturn-centred coplanar model", "km"),
}

# Default styling per curve `role`. The 3D scene always renders on a fixed
# dark background (see colors.SCENE_BACKGROUND) regardless of the Streamlit
# page theme, so every phase color below uses its `.dark` step.
ROLE_STYLE: dict[str, tuple[str, int, str]] = {
    "planet_orbit": (colors.REFERENCE_ORBIT, 3, "dot"),
    "moon_orbit": (colors.REFERENCE_ORBIT_WARM, 3, "dot"),
    "capture_orbit": (colors.ARRIVAL.dark, 5, "solid"),
    "staging_orbit": (colors.ARRIVAL.dark, 4, "dash"),
    "spacecraft_transfer": (colors.INTERPLANETARY_TRANSFER.dark, 7, "solid"),
}

# Two curves share the "spacecraft_transfer" role (interplanetary vs. lunar
# transfer) but are different mission phases and so must render in
# different colors - see mission/colors.py's "one color = one phase" rule.
# Looked up by name first; role-based ROLE_STYLE above is the default for
# every other curve.
CURVE_NAME_STYLE_OVERRIDE: dict[str, tuple[str, int, str]] = {
    "Saturn → Titan transfer": (colors.LUNAR_TRANSFER.dark, 7, "solid"),
}

CASSINI_LEG_NAMES = (
    "Venus 1",
    "Venus 2",
    "Earth",
    "Jupiter",
    "Saturn insertion",
)
CASSINI_LEG_DASHES = ("solid", "dot", "dash", "longdash", "dashdot")


def _format_mjd2000(epoch_mjd2000: float) -> str:
    """Format a supplied MJD2000 epoch without recomputing an ephemeris."""
    epoch = datetime(2000, 1, 1, tzinfo=UTC) + timedelta(days=epoch_mjd2000)
    return epoch.strftime("%Y-%m-%d %H:%M UTC")


def build_cassini_historical_figure(
    tour: tuple[MissionSegment, ...],
) -> go.Figure:
    """Render the exact positions, dates, and encounters supplied by the tour.

    Each leg is deliberately a two-point trace: the historical tour is the
    authoritative source of states, and this renderer does not introduce
    independently propagated or interpolated positions between them.
    """
    if len(tour) != len(CASSINI_LEG_NAMES) or not all(
        isinstance(segment, MissionSegment) for segment in tour
    ):
        raise ValueError("tour must contain the five Cassini historical MissionSegments.")

    figure = go.Figure()
    for index, (segment, display_name, dash) in enumerate(
        zip(tour, CASSINI_LEG_NAMES, CASSINI_LEG_DASHES, strict=True)
    ):
        is_insertion = isinstance(segment.result, OrbitInsertionResult)
        if not is_insertion and not isinstance(segment.result, GravityAssistResult):
            raise TypeError("Each historical leg must end in a flyby or orbit insertion.")
        event = "insertion" if is_insertion else segment.arrival_body
        altitude_km = segment.result.periapsis_altitude_m / 1_000.0
        positions = (segment.departure_position_m, segment.arrival_position_m)
        dates = (
            _format_mjd2000(segment.departure_epoch_mjd2000),
            _format_mjd2000(segment.arrival_epoch_mjd2000),
        )
        customdata = tuple((date, event, altitude_km) for date in dates)
        phase_color = colors.ARRIVAL if is_insertion else colors.INTERPLANETARY_TRANSFER
        figure.add_trace(
            go.Scatter3d(
                x=[position[0] / pk.AU for position in positions],
                y=[position[1] / pk.AU for position in positions],
                z=[position[2] / pk.AU for position in positions],
                mode="lines+markers",
                name=display_name,
                line={"color": phase_color.dark, "width": 7, "dash": dash},
                marker={
                    "color": (
                        colors.LAUNCH.dark if index == 0 else colors.ARRIVAL.dark,
                        colors.ARRIVAL.dark,
                    ),
                    "size": (5, 7),
                },
                customdata=customdata,
                hovertemplate=(
                    "<b>%{fullData.name}</b><br>"
                    "Date: %{customdata[0]}<br>"
                    "Flyby body / event: %{customdata[1]}<br>"
                    "Flyby altitude: %{customdata[2]:,.0f} km"
                    "<extra></extra>"
                ),
            )
        )

    figure.update_layout(
        height=720,
        margin={"l": 0, "r": 0, "t": 40, "b": 0},
        showlegend=len(figure.data) > 1,
        legend={"orientation": "h", "y": -0.08, "x": 0.5, "xanchor": "center"},
        scene={
            "xaxis": _axis("x (AU)"),
            "yaxis": _axis("y (AU)"),
            "zaxis": _axis("z (AU)"),
            "aspectmode": "data",
        },
        uirevision="cassini-historical-tour-v1",
    )
    return figure


def _add_curve(figure: go.Figure, curve: TrajectoryCurve3D, scene_index: int) -> None:
    color, width, dash = CURVE_NAME_STYLE_OVERRIDE.get(curve.name) or ROLE_STYLE[curve.role]
    figure.add_trace(
        go.Scatter3d(
            x=curve.x,
            y=curve.y,
            z=curve.z,
            mode="lines",
            name=curve.name,
            legendgroup=curve.frame,
            line={"color": color, "width": width, "dash": dash},
            hovertemplate=(
                f"<b>{curve.name}</b><br>"
                f"x=%{{x:,.3f}} {curve.unit}<br>"
                f"y=%{{y:,.3f}} {curve.unit}<br>"
                f"z=%{{z:,.3f}} {curve.unit}<extra></extra>"
            ),
        ),
        row=1,
        col=scene_index,
    )


def _axis(title: str) -> dict[str, object]:
    return {
        "title": title,
        "showbackground": True,
        "backgroundcolor": colors.SCENE_BACKGROUND,
        "gridcolor": colors.GRIDLINE,
        "zerolinecolor": colors.AXIS_ZERO_LINE,
    }


def _add_marker(
    figure: go.Figure,
    *,
    name: str,
    x: float,
    y: float,
    z: float,
    color: str,
    size: int,
    scene_index: int,
) -> None:
    figure.add_trace(
        go.Scatter3d(
            x=[x],
            y=[y],
            z=[z],
            mode="markers+text",
            name=name,
            text=[name],
            textposition="top center",
            marker={"color": color, "size": size},
            hovertemplate=f"<b>{name}</b><extra></extra>",
        ),
        row=1,
        col=scene_index,
    )


def build_complete_mission_figure(
    scene: CompleteMissionScene3D,
    spacecraft_position: SpacecraftPosition3D | None = None,
) -> go.Figure:
    """Render the two reference frames in one interactive Plotly figure."""
    if not isinstance(scene, CompleteMissionScene3D):
        raise TypeError("scene must be a CompleteMissionScene3D.")
    figure = make_subplots(
        rows=1,
        cols=2,
        specs=[[{"type": "scene"}, {"type": "scene"}]],
        subplot_titles=("Heliocentric transfer", "Saturn system"),
        horizontal_spacing=0.04,
    )
    for curve in scene.heliocentric_curves:
        _add_curve(figure, curve, 1)
    for curve in scene.saturn_curves:
        _add_curve(figure, curve, 2)

    lambert = scene.heliocentric_curves[1]
    titan_transfer = scene.saturn_curves[2]
    _add_marker(
        figure,
        name="Sun",
        x=0.0,
        y=0.0,
        z=0.0,
        color=colors.LANDMARK_SUN,
        size=9,
        scene_index=1,
    )
    _add_marker(
        figure,
        name="Earth departure",
        x=lambert.x[0],
        y=lambert.y[0],
        z=lambert.z[0],
        color=colors.LAUNCH.dark,
        size=6,
        scene_index=1,
    )
    _add_marker(
        figure,
        name="Saturn arrival",
        x=lambert.x[-1],
        y=lambert.y[-1],
        z=lambert.z[-1],
        color=colors.LANDMARK_BODY,
        size=8,
        scene_index=1,
    )
    _add_marker(
        figure,
        name="Saturn",
        x=0.0,
        y=0.0,
        z=0.0,
        color=colors.LANDMARK_BODY,
        size=10,
        scene_index=2,
    )
    _add_marker(
        figure,
        name="Titan encounter",
        x=titan_transfer.x[-1],
        y=titan_transfer.y[-1],
        z=titan_transfer.z[-1],
        color=colors.LANDMARK_MOON,
        size=7,
        scene_index=2,
    )
    if spacecraft_position is not None:
        if not isinstance(spacecraft_position, SpacecraftPosition3D):
            raise TypeError("spacecraft_position must be a SpacecraftPosition3D.")
        scene_index = 1 if spacecraft_position.frame == "heliocentric" else 2
        # Same phase, same color as everywhere else in the app: the moving
        # marker's color follows its current animation phase (see
        # colors.ANIMATION_PHASE_COLORS), falling back to the launch color
        # for any (currently unused) unmapped phase name.
        phase_color = colors.ANIMATION_PHASE_COLORS.get(
            spacecraft_position.phase_name, colors.LAUNCH
        )
        figure.add_trace(
            go.Scatter3d(
                x=[spacecraft_position.x],
                y=[spacecraft_position.y],
                z=[spacecraft_position.z],
                mode="markers",
                name="Spacecraft — current position",
                marker={"color": phase_color.dark, "size": 9, "symbol": "diamond"},
                hovertemplate=(
                    f"<b>{spacecraft_position.phase_name}</b><br>"
                    f"Mission elapsed time: {spacecraft_position.elapsed_days:,.2f} days"
                    "<extra></extra>"
                ),
            ),
            row=1,
            col=scene_index,
        )

    figure.update_layout(
        height=720,
        margin={"l": 0, "r": 0, "t": 60, "b": 0},
        legend={"orientation": "h", "y": -0.08, "x": 0.5, "xanchor": "center"},
        scene={
            "xaxis": _axis("x (AU)"),
            "yaxis": _axis("y (AU)"),
            "zaxis": _axis("z (AU)"),
            "aspectmode": "data",
        },
        scene2={
            "xaxis": _axis("x (km)"),
            "yaxis": _axis("y (km)"),
            "zaxis": _axis("z (km)"),
            "aspectmode": "data",
        },
        uirevision="complete-mission-trajectory-v1",
    )
    return figure


def build_complete_mission_table(figure: go.Figure) -> pd.DataFrame:
    """Flatten every curve/marker trace of a built figure into one data table.

    Accessible alternative to the 3D chart (screen-reader/keyboard users, and
    exact-number export/verification): reads coordinates directly off the
    already-built Figure rather than recomputing them, so the table can never
    drift from what is actually plotted.
    """
    if not isinstance(figure, go.Figure):
        raise TypeError("figure must be a plotly.graph_objects.Figure.")

    rows: list[dict[str, object]] = []
    for trace in figure.data:
        panel, unit = _SCENE_PANEL.get(trace.scene, ("Unknown panel", ""))
        is_curve = trace.mode is not None and "lines" in trace.mode
        xs, ys, zs = trace.x or (), trace.y or (), trace.z or ()
        for index, (x, y, z) in enumerate(zip(xs, ys, zs, strict=True)):
            rows.append(
                {
                    "Element": trace.name,
                    "Type": "Curve" if is_curve else "Marker",
                    "Panel": panel,
                    "Point index": index,
                    "x": x,
                    "y": y,
                    "z": z,
                    "Unit": unit,
                }
            )
    return pd.DataFrame(
        rows,
        columns=["Element", "Type", "Panel", "Point index", "x", "y", "z", "Unit"],
    )


# --------------------------------------------------------------------------
# Generic scene figure - the only builder that consumes
# mission.trajectory_scene.TrajectorySegment instead of a specific mission's
# domain result type, so the same function renders a direct Lambert-based
# mission or a gravity-assist tour without knowing which one it is.
# --------------------------------------------------------------------------

# Named camera angles for the 3D scene. Values are Plotly `scene.camera.eye`
# vectors in the figure's own data units (so they compose with `aspectmode:
# "data"`); "Global" is a wide default view, the others are close-in on the
# Saturn-centred geometry these presets were named for (rings/periapsis/
# Titan's orbit). Display-only constants - not physical data.
CAMERA_PRESETS: dict[str, dict[str, object]] = {
    "Global": {"eye": {"x": 1.6, "y": 1.6, "z": 1.1}},
    "Rings": {"eye": {"x": 0.35, "y": 0.35, "z": 0.18}},
    "Periapsis": {"eye": {"x": 0.06, "y": 0.06, "z": 0.03}},
    "Titan": {"eye": {"x": 1.5, "y": 0.05, "z": 0.35}},
}
DEFAULT_VIEW_PRESET = "Global"

_REAL_SCALE_MAX_MARKER_PX = 26
_REAL_SCALE_MIN_MARKER_PX = 2


def _real_scale_reference_radius_m(segments: tuple[TrajectorySegment, ...]) -> float | None:
    """Largest sourced `true_radius_m` among the given segments, or None if none carry one."""
    radii = [
        radius
        for segment in segments
        for radius in (segment.metadata.get("true_radius_m") if segment.metadata else None,)
        if radius is not None
    ]
    return max(radii) if radii else None


def _marker_size_px(
    segment: TrajectorySegment,
    *,
    real_scale: bool,
    reference_radius_m: float | None,
) -> int:
    """Landmark marker pixel size.

    Not a true volumetric scale - Plotly Scatter3d marker `size` is a
    screen-pixel value, not a data-unit radius - so `real_scale=True` only
    makes marker sizes *linearly proportional to each other's real radius*
    within the legible pixel range below, anchored to the largest body in
    this figure. Smaller bodies shrinking toward illegibility (or a body
    with no sourced radius falling back to its default size) is expected,
    honest behavior for this toggle, not a bug.
    """
    if not real_scale:
        return segment.style.marker_size
    radius_m = segment.metadata.get("true_radius_m") if segment.metadata else None
    if radius_m is None or not reference_radius_m:
        return segment.style.marker_size
    scaled = _REAL_SCALE_MAX_MARKER_PX * (radius_m / reference_radius_m)
    return max(_REAL_SCALE_MIN_MARKER_PX, round(scaled))


def _segment_hover_template(segment: TrajectorySegment) -> str:
    """Hover text built only from fields this segment actually carries.

    Optional fields (dates, duration, delta-v) are omitted rather than
    padded with a placeholder when the segment does not provide them.
    """
    lines = [f"<b>{segment.name}</b>", f"{segment.origin_body} → {segment.destination_body}"]
    if segment.departure_date:
        lines.append(f"Departs: {segment.departure_date}")
    if segment.arrival_date:
        lines.append(f"Arrives: {segment.arrival_date}")
    if segment.duration_days is not None:
        lines.append(f"Duration: {segment.duration_days:,.3f} days")
    if segment.delta_v_m_s is not None:
        lines.append(f"Delta-v: {segment.delta_v_m_s:,.1f} m/s")
    return "<br>".join(lines) + "<extra></extra>"


def build_scene_figure(
    segments: tuple[TrajectorySegment, ...],
    *,
    unit_label: str,
    view_preset: str = DEFAULT_VIEW_PRESET,
    real_scale: bool = False,
) -> go.Figure:
    """Render a generic list of TrajectorySegment as one 3D Plotly scene.

    Pure figure construction from already-computed, generic data: this
    function knows nothing about Mission/Leg/GravityAssistResult or any
    other domain type, only the `TrajectorySegment` shape - see
    `mission/trajectory_scene.py` for the adapters that produce that shape
    from an existing mission result (a direct Earth->Saturn->Titan chain or
    the Cassini historical gravity-assist tour alike). No Lambert solve,
    ephemeris sampling, or flyby geometry happens here.
    """
    if not isinstance(segments, tuple) or not segments:
        raise ValueError("segments must be a non-empty tuple of TrajectorySegment.")
    if not all(isinstance(segment, TrajectorySegment) for segment in segments):
        raise TypeError("segments must contain only TrajectorySegment instances.")
    if view_preset not in CAMERA_PRESETS:
        raise ValueError(f"view_preset must be one of {tuple(CAMERA_PRESETS)}.")

    reference_radius_m = _real_scale_reference_radius_m(segments) if real_scale else None

    figure = go.Figure()
    for segment in segments:
        if segment.is_point:
            figure.add_trace(
                go.Scatter3d(
                    x=list(segment.x),
                    y=list(segment.y),
                    z=list(segment.z),
                    mode="markers+text",
                    name=segment.name,
                    text=[segment.name],
                    textposition="top center",
                    legendgroup=segment.style.legend_group,
                    marker={
                        "color": segment.style.color,
                        "size": _marker_size_px(
                            segment, real_scale=real_scale, reference_radius_m=reference_radius_m
                        ),
                    },
                    hovertemplate=_segment_hover_template(segment),
                )
            )
        else:
            figure.add_trace(
                go.Scatter3d(
                    x=list(segment.x),
                    y=list(segment.y),
                    z=list(segment.z),
                    mode="lines",
                    name=segment.name,
                    legendgroup=segment.style.legend_group,
                    line={
                        "color": segment.style.color,
                        "width": segment.style.width,
                        "dash": segment.style.dash,
                    },
                    hovertemplate=_segment_hover_template(segment),
                )
            )

    figure.update_layout(
        height=720,
        margin={"l": 0, "r": 0, "t": 40, "b": 0},
        showlegend=True,
        legend={"orientation": "h", "y": -0.08, "x": 0.5, "xanchor": "center"},
        scene={
            "xaxis": _axis(f"x ({unit_label})"),
            "yaxis": _axis(f"y ({unit_label})"),
            "zaxis": _axis(f"z ({unit_label})"),
            "aspectmode": "data",
            "camera": CAMERA_PRESETS[view_preset],
        },
        uirevision=f"generic-scene-{view_preset}-{real_scale}",
    )
    return figure


def _direct_animation_slider_label(frame: DirectTrajectoryFrame3D) -> str:
    """Date + elapsed time for one slider step - the only place this pair is
    still shown inside the Plotly figure itself; the fixed trajectory-type
    and date-range context now live in Streamlit above the chart (see
    pages/trajectory_3d.py) so the long per-frame title this replaced can
    never again get clipped at narrow widths."""
    return f"{frame.date_utc[:10]} · +{frame.elapsed_days:,.0f} d"


def build_direct_animation_figure(
    segments: tuple[TrajectorySegment, ...],
    timeline: DirectTrajectoryTimeline3D,
) -> go.Figure:
    """Add lightweight Plotly frames to one existing heliocentric/AU scene."""
    if not isinstance(timeline, DirectTrajectoryTimeline3D):
        raise TypeError("timeline must be a DirectTrajectoryTimeline3D.")
    if any(
        segment.metadata.get("reference_frame") != timeline.reference_frame
        or segment.metadata.get("distance_unit") != timeline.distance_unit
        for segment in segments
    ):
        raise ValueError("Animated segments must match the timeline frame and unit.")

    figure = build_scene_figure(segments, unit_label="AU")
    first = timeline.frames[0]
    last = timeline.frames[-1]
    figure.add_traces(
        (
            go.Scatter3d(
                x=[first.spacecraft_position_au[0]],
                y=[first.spacecraft_position_au[1]],
                z=[first.spacecraft_position_au[2]],
                mode="markers+text",
                name="Earth departure",
                text=["Departure"],
                textposition="top center",
                marker={"color": colors.LAUNCH.dark, "size": 7},
                hovertemplate=f"Earth departure<br>{first.date_utc}<extra></extra>",
            ),
            go.Scatter3d(
                x=[last.spacecraft_position_au[0]],
                y=[last.spacecraft_position_au[1]],
                z=[last.spacecraft_position_au[2]],
                mode="markers+text",
                name="Saturn arrival",
                text=["Arrival"],
                textposition="top center",
                marker={"color": colors.ARRIVAL.dark, "size": 7},
                hovertemplate=f"Saturn arrival<br>{last.date_utc}<extra></extra>",
            ),
            go.Scatter3d(
                x=[first.earth_position_au[0]],
                y=[first.earth_position_au[1]],
                z=[first.earth_position_au[2]],
                mode="markers",
                name="Earth — current ephemeris position",
                # Identified on hover and by its fixed marker color; kept out
                # of the legend band so that band stays short enough to
                # never wrap into the slider/button bands below it at
                # narrow widths (see build_direct_animation_figure).
                showlegend=False,
                marker={"color": colors.LANDMARK_BODY, "size": 6},
                hovertemplate="Earth<br>%{text}<extra></extra>",
                text=[first.date_utc],
            ),
            go.Scatter3d(
                x=[first.saturn_position_au[0]],
                y=[first.saturn_position_au[1]],
                z=[first.saturn_position_au[2]],
                mode="markers",
                name="Saturn — current ephemeris position",
                showlegend=False,
                marker={"color": colors.REFERENCE_ORBIT_WARM, "size": 7},
                hovertemplate="Saturn<br>%{text}<extra></extra>",
                text=[first.date_utc],
            ),
            go.Scatter3d(
                x=[first.spacecraft_position_au[0]],
                y=[first.spacecraft_position_au[1]],
                z=[first.spacecraft_position_au[2]],
                mode="markers",
                name="Spacecraft — sampled position",
                showlegend=False,
                marker={
                    "color": colors.INTERPLANETARY_TRANSFER.dark,
                    "size": 8,
                    "line": {"color": colors.MARKER_RIM, "width": 1},
                },
                customdata=[[first.date_utc, first.elapsed_days]],
                hovertemplate=(
                    "Spacecraft<br>Date: %{customdata[0]}<br>"
                    "Elapsed: %{customdata[1]:,.1f} days<extra></extra>"
                ),
            ),
        )
    )
    dynamic_indices = tuple(range(len(figure.data) - 3, len(figure.data)))
    frames = []
    for index, instant in enumerate(timeline.frames):
        frames.append(
            go.Frame(
                name=str(index),
                traces=dynamic_indices,
                data=(
                    go.Scatter3d(
                        x=[instant.earth_position_au[0]],
                        y=[instant.earth_position_au[1]],
                        z=[instant.earth_position_au[2]],
                        text=[instant.date_utc],
                    ),
                    go.Scatter3d(
                        x=[instant.saturn_position_au[0]],
                        y=[instant.saturn_position_au[1]],
                        z=[instant.saturn_position_au[2]],
                        text=[instant.date_utc],
                    ),
                    go.Scatter3d(
                        x=[instant.spacecraft_position_au[0]],
                        y=[instant.spacecraft_position_au[1]],
                        z=[instant.spacecraft_position_au[2]],
                        customdata=[[instant.date_utc, instant.elapsed_days]],
                    ),
                ),
            )
        )
    figure.frames = tuple(frames)

    frame_duration_ms = max(70, round(4_800 / len(timeline.frames)))
    # Three distinct vertical bands below the 3D scene - legend, then the
    # date/elapsed slider, then Play/Pause/Reset - each given its own y
    # position with a wide, fixed gap to the next so none can visually
    # collide regardless of container width (the figure's pixel height does
    # not change across breakpoints, only its width does). No Plotly title
    # is set here: the trajectory type, date range, and total elapsed time
    # are rendered once in Streamlit above this figure (see
    # pages/trajectory_3d.py) instead of a long per-frame title that could
    # get clipped at narrow widths.
    legend_band_y = -0.05
    slider_band_y = -0.17
    buttons_band_y = -0.27
    figure.update_layout(
        height=680,
        margin={"l": 0, "r": 0, "t": 20, "b": 180},
        legend={"orientation": "h", "y": legend_band_y, "x": 0.5, "xanchor": "center"},
        updatemenus=[
            {
                "type": "buttons",
                "direction": "left",
                "x": 0.0,
                "y": buttons_band_y,
                "buttons": [
                    {
                        "label": "Play",
                        "method": "animate",
                        "args": [
                            None,
                            {
                                "fromcurrent": True,
                                "frame": {"duration": frame_duration_ms, "redraw": True},
                                "transition": {"duration": 0},
                            },
                        ],
                    },
                    {
                        "label": "Pause",
                        "method": "animate",
                        "args": [
                            [None],
                            {
                                "mode": "immediate",
                                "frame": {"duration": 0, "redraw": False},
                                "transition": {"duration": 0},
                            },
                        ],
                    },
                    {
                        "label": "Reset",
                        "method": "animate",
                        "args": [
                            ["0"],
                            {
                                "mode": "immediate",
                                "frame": {"duration": 0, "redraw": True},
                                "transition": {"duration": 0},
                            },
                        ],
                    },
                ],
            }
        ],
        sliders=[
            {
                "active": 0,
                "x": 0.0,
                "y": slider_band_y,
                "len": 1.0,
                "currentvalue": {"prefix": "UTC: "},
                "steps": [
                    {
                        "label": _direct_animation_slider_label(instant),
                        "method": "animate",
                        "args": [
                            [str(index)],
                            {
                                "mode": "immediate",
                                "frame": {"duration": 0, "redraw": True},
                                "transition": {"duration": 0},
                            },
                        ],
                    }
                    for index, instant in enumerate(timeline.frames)
                ],
            }
        ],
        uirevision=f"direct-animation-{timeline.scenario_id}",
    )
    return figure


def build_scene_table(segments: tuple[TrajectorySegment, ...]) -> pd.DataFrame:
    """Flatten a generic segment list into one data table - the accessible
    alternative to `build_scene_figure`'s chart, built from the same segments
    rather than re-parsed off the Figure, so it can never drift from what
    was requested to be plotted.
    """
    if not isinstance(segments, tuple) or not all(
        isinstance(segment, TrajectorySegment) for segment in segments
    ):
        raise TypeError("segments must be a tuple of TrajectorySegment.")

    rows: list[dict[str, object]] = []
    for segment in segments:
        for index, (x, y, z) in enumerate(zip(segment.x, segment.y, segment.z, strict=True)):
            rows.append(
                {
                    "Segment": segment.name,
                    "Type": segment.type,
                    "Origin": segment.origin_body,
                    "Destination": segment.destination_body,
                    "Point index": index,
                    "x": x,
                    "y": y,
                    "z": z,
                    "Departure date": segment.departure_date,
                    "Arrival date": segment.arrival_date,
                    "Duration (days)": segment.duration_days,
                    "Delta-v (m/s)": segment.delta_v_m_s,
                }
            )
    return pd.DataFrame(
        rows,
        columns=[
            "Segment",
            "Type",
            "Origin",
            "Destination",
            "Point index",
            "x",
            "y",
            "z",
            "Departure date",
            "Arrival date",
            "Duration (days)",
            "Delta-v (m/s)",
        ],
    )


def scene_figure_to_standalone_html(figure: go.Figure) -> str:
    """Serialize a built figure to one self-contained, offline-capable HTML string.

    Embeds the full Plotly JS library (`include_plotlyjs=True`) rather than
    linking a CDN, so the exported file opens and stays interactive without
    a network connection.
    """
    if not isinstance(figure, go.Figure):
        raise TypeError("figure must be a plotly.graph_objects.Figure.")
    return figure.to_html(full_html=True, include_plotlyjs=True)
