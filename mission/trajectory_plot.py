"""Plotly rendering for the pure complete-mission trajectory scene."""

from __future__ import annotations

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .trajectory_visualization import (
    CompleteMissionScene3D,
    SpacecraftPosition3D,
    TrajectoryCurve3D,
)

ROLE_STYLE: dict[str, tuple[str, int, str]] = {
    "planet_orbit": ("#7C8DA6", 3, "dot"),
    "moon_orbit": ("#D9A441", 3, "dot"),
    "capture_orbit": ("#B983FF", 5, "solid"),
    "staging_orbit": ("#4CC9F0", 4, "dash"),
    "spacecraft_transfer": ("#FF5A5F", 7, "solid"),
}


def _add_curve(figure: go.Figure, curve: TrajectoryCurve3D, scene_index: int) -> None:
    color, width, dash = ROLE_STYLE[curve.role]
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
        "backgroundcolor": "rgba(13, 20, 33, 0.75)",
        "gridcolor": "rgba(160, 174, 192, 0.25)",
        "zerolinecolor": "rgba(255, 255, 255, 0.35)",
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
        color="#FFD166",
        size=9,
        scene_index=1,
    )
    _add_marker(
        figure,
        name="Earth departure",
        x=lambert.x[0],
        y=lambert.y[0],
        z=lambert.z[0],
        color="#4CC9F0",
        size=6,
        scene_index=1,
    )
    _add_marker(
        figure,
        name="Saturn arrival",
        x=lambert.x[-1],
        y=lambert.y[-1],
        z=lambert.z[-1],
        color="#D9A441",
        size=8,
        scene_index=1,
    )
    _add_marker(
        figure,
        name="Saturn",
        x=0.0,
        y=0.0,
        z=0.0,
        color="#D9A441",
        size=10,
        scene_index=2,
    )
    _add_marker(
        figure,
        name="Titan encounter",
        x=titan_transfer.x[-1],
        y=titan_transfer.y[-1],
        z=titan_transfer.z[-1],
        color="#E8D9B5",
        size=7,
        scene_index=2,
    )
    if spacecraft_position is not None:
        if not isinstance(spacecraft_position, SpacecraftPosition3D):
            raise TypeError("spacecraft_position must be a SpacecraftPosition3D.")
        scene_index = 1 if spacecraft_position.frame == "heliocentric" else 2
        figure.add_trace(
            go.Scatter3d(
                x=[spacecraft_position.x],
                y=[spacecraft_position.y],
                z=[spacecraft_position.z],
                mode="markers",
                name="Spacecraft — current position",
                marker={"color": "#00F5A0", "size": 9, "symbol": "diamond"},
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
