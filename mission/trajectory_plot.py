"""Plotly rendering for the pure complete-mission trajectory scene."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from . import colors
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
