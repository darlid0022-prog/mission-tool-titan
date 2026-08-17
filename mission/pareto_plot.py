"""Plotly rendering for the deterministic connected-mission Pareto front."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

import plotly.graph_objects as go

from .pareto import ParetoPoint, ParetoSearchResult

MJD2000_EPOCH = datetime(2000, 1, 1)


@dataclass(frozen=True)
class ParetoHighlights:
    """Deterministically selected reference points and remaining Pareto samples."""

    baseline: ParetoPoint
    delta_v_optimum: ParetoPoint
    regular_front: tuple[ParetoPoint, ...]


def select_pareto_highlights(result: ParetoSearchResult) -> ParetoHighlights:
    """Select the locked minimum-departure-v-infinity baseline and delta-v optimum."""
    if not isinstance(result, ParetoSearchResult):
        raise TypeError("result must be a ParetoSearchResult.")
    if not result.evaluated_points or not result.pareto_front:
        raise ValueError("Pareto result must contain evaluated and non-dominated points.")

    baseline = min(
        result.evaluated_points,
        key=lambda point: (
            point.earth_departure_v_infinity_m_s,
            point.departure_mjd2000,
            point.earth_saturn_tof_years,
            point.total_delta_v_m_s,
        ),
    )
    optimum = min(
        result.pareto_front,
        key=lambda point: (
            point.total_delta_v_m_s,
            point.total_duration_days,
            point.wet_mass_kg,
            point.departure_mjd2000,
            point.earth_saturn_tof_years,
        ),
    )
    regular_front = tuple(
        point for point in result.pareto_front if point not in (baseline, optimum)
    )
    return ParetoHighlights(
        baseline=baseline,
        delta_v_optimum=optimum,
        regular_front=regular_front,
    )


def _departure_date(point: ParetoPoint) -> str:
    return (MJD2000_EPOCH + timedelta(days=point.departure_mjd2000)).date().isoformat()


def _custom_data(points: tuple[ParetoPoint, ...]) -> list[list[float | str]]:
    return [
        [
            point.wet_mass_kg,
            point.earth_saturn_tof_years * 365.25,
            _departure_date(point),
            point.departure_mjd2000,
        ]
        for point in points
    ]


def _hover_template(title: str) -> str:
    return (
        f"<b>{title}</b><br>"
        "Connected delta-v: %{x:,.3f} m/s<br>"
        "Total mission duration: %{y:,.3f} days<br>"
        "Wet mass: %{customdata[0]:,.3f} kg<br>"
        "Earth → Saturn TOF: %{customdata[1]:,.3f} days<br>"
        "Earth departure date: %{customdata[2]}<br>"
        "Departure MJD2000: %{customdata[3]:,.6f}<extra></extra>"
    )


def _highlight_trace(
    point: ParetoPoint,
    *,
    name: str,
    color: str,
    symbol: str,
    size: int,
) -> go.Scatter:
    return go.Scatter(
        x=[point.total_delta_v_m_s],
        y=[point.total_duration_days],
        mode="markers",
        name=name,
        marker={
            "color": color,
            "size": size,
            "symbol": symbol,
            "line": {"color": "white", "width": 2},
        },
        customdata=_custom_data((point,)),
        hovertemplate=_hover_template(name),
        meta={"role": name},
    )


def build_pareto_front_figure(result: ParetoSearchResult) -> go.Figure:
    """Render the 2D duration/delta-v trade space with wet mass encoded by color."""
    highlights = select_pareto_highlights(result)
    regular = highlights.regular_front
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=[point.total_delta_v_m_s for point in regular],
            y=[point.total_duration_days for point in regular],
            mode="markers",
            name="Pareto-optimal missions",
            marker={
                "color": [point.wet_mass_kg for point in regular],
                "colorscale": "Viridis",
                "size": 10,
                "opacity": 0.9,
                "colorbar": {"title": "Wet mass<br>(kg)"},
                "line": {"color": "rgba(255,255,255,0.55)", "width": 1},
            },
            customdata=_custom_data(regular),
            hovertemplate=_hover_template("Pareto-optimal mission"),
            meta={"role": "pareto_front"},
        )
    )
    figure.add_trace(
        _highlight_trace(
            highlights.delta_v_optimum,
            name="Minimum connected delta-v",
            color="#FF5A5F",
            symbol="star",
            size=18,
        )
    )
    figure.add_trace(
        _highlight_trace(
            highlights.baseline,
            name="Current mission baseline",
            color="#00F5A0",
            symbol="diamond-open",
            size=17,
        )
    )
    figure.update_layout(
        height=540,
        margin={"l": 20, "r": 20, "t": 30, "b": 20},
        xaxis={
            "title": "Connected propulsive delta-v (m/s)",
            "gridcolor": "rgba(160, 174, 192, 0.25)",
            "zeroline": False,
        },
        yaxis={
            "title": "Total mission duration (days)",
            "gridcolor": "rgba(160, 174, 192, 0.25)",
            "zeroline": False,
        },
        legend={"orientation": "h", "y": -0.18, "x": 0.5, "xanchor": "center"},
        hovermode="closest",
        uirevision="connected-mission-pareto-v1",
    )
    return figure
