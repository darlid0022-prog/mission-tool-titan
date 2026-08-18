"""Pure rendering for launch-window search results: a sortable table and a
delta-v-vs-duration chart. No search, ranking, or physics happens here -
every function below only reformats an already-built
`launch_window_service.LaunchWindowSearchResult`/`LaunchWindowCandidate`.

Mirrors the existing split between schema and rendering already used for the
3D scene (mission/trajectory_scene.py vs mission/trajectory_plot.py) and for
the Pareto front (mission/pareto.py vs mission/pareto_plot.py) - this module
plays the "rendering" role for the launch-window schema defined in
launch_window_service.py.
"""

from __future__ import annotations

from datetime import timezone

import pandas as pd
import plotly.graph_objects as go

from launch_window_service import LaunchWindowCandidate
from mission import colors

CANDIDATE_TABLE_COLUMNS = (
    "Rank",
    "Selected",
    "Pareto optimal",
    "Launch date (UTC)",
    "Launch time (UTC)",
    "Saturn arrival (UTC)",
    "Scenario end (UTC)",
    "Earth → Saturn flight time (days)",
    "Earth → Saturn flight time (years)",
    "Total reference-scenario duration (days)",
    "Total reference-scenario duration (years)",
    "C3 (km²/s²)",
    "v∞ Earth (m/s)",
    "v∞ Saturn (m/s)",
    "Earth departure Δv (m/s)",
    "Delta-v capture (m/s)",
    "Saturn-centered circularization Δv (m/s)",
    "Delta-v total (m/s)",
)


def _validate_candidates(candidates: tuple[LaunchWindowCandidate, ...]) -> None:
    if not isinstance(candidates, tuple) or not all(
        isinstance(candidate, LaunchWindowCandidate) for candidate in candidates
    ):
        raise TypeError("candidates must be a tuple of LaunchWindowCandidate.")


def build_candidates_dataframe(
    candidates: tuple[LaunchWindowCandidate, ...],
    *,
    selected_rank: int | None,
    pareto_candidate_ranks: tuple[int, ...] | None = None,
) -> pd.DataFrame:
    """One row per candidate, every field the launch-windows page must show.

    Streamlit's st.dataframe sorts by clicking any column header natively -
    this is the "sortable table of top candidates" and also the accessible,
    keyboard/screen-reader-navigable alternative to the chart built from the
    same data below, including which candidates the chart marks as
    Pareto-optimal (mirrors build_candidates_chart's pareto_candidate_ranks
    so the two never disagree about which ranks are highlighted).
    """
    _validate_candidates(candidates)
    pareto_ranks = set(pareto_candidate_ranks or ())
    rows = [
        {
            "Rank": candidate.rank,
            "Selected": candidate.rank == selected_rank,
            "Pareto optimal": candidate.rank in pareto_ranks,
            "Launch date (UTC)": candidate.departure_datetime.astimezone(timezone.utc).date(),
            "Launch time (UTC)": candidate.departure_datetime.astimezone(timezone.utc)
            .time()
            .isoformat(timespec="minutes"),
            "Saturn arrival (UTC)": candidate.saturn_arrival_datetime.astimezone(
                timezone.utc
            ).isoformat(timespec="minutes"),
            "Scenario end (UTC)": candidate.scenario_end_datetime.astimezone(
                timezone.utc
            ).isoformat(timespec="minutes"),
            "Earth → Saturn flight time (days)": candidate.time_of_flight_days,
            "Earth → Saturn flight time (years)": candidate.time_of_flight_years,
            "Total reference-scenario duration (days)": candidate.total_duration_days,
            "Total reference-scenario duration (years)": candidate.total_duration_years,
            "C3 (km²/s²)": candidate.c3_km2_s2,
            "v∞ Earth (m/s)": candidate.v_infinity_earth_m_s,
            "v∞ Saturn (m/s)": candidate.v_infinity_saturn_m_s,
            "Earth departure Δv (m/s)": candidate.delta_v_departure_m_s,
            "Delta-v capture (m/s)": candidate.delta_v_capture_m_s,
            "Saturn-centered circularization Δv (m/s)": candidate.delta_v_titan_circularization_m_s,
            "Delta-v total (m/s)": candidate.delta_v_total_m_s,
        }
        for candidate in candidates
    ]
    return pd.DataFrame(rows, columns=CANDIDATE_TABLE_COLUMNS)


def build_candidates_chart(
    candidates: tuple[LaunchWindowCandidate, ...],
    *,
    selected_rank: int | None,
    pareto_candidate_ranks: tuple[int, ...] | None = None,
) -> go.Figure:
    """Delta-v total (y) vs Earth -> Saturn flight time (x): one axis per
    physical quantity (never a dual y-axis), a single neutral hue for
    ordinary candidates, and the selected candidate picked out with a
    distinct highlight marker - the same highlight pattern already used for
    the connected-mission Pareto front (mission/pareto_plot.py).

    The x-axis is deliberately the Earth -> Saturn cruise only (candidate.
    time_of_flight_days), not candidate.total_duration_days (which also
    covers the post-arrival Saturn capture and Titan-orbital-radius
    circularization) - labeled explicitly as "Earth -> Saturn flight time"
    so it is never read as the full reference-scenario duration.
    """
    _validate_candidates(candidates)
    if not candidates:
        raise ValueError("candidates must be non-empty.")

    pareto_ranks = set(pareto_candidate_ranks or ())
    selected = next((c for c in candidates if c.rank == selected_rank), None)
    pareto = tuple(c for c in candidates if c.rank in pareto_ranks and c is not selected)
    regular = tuple(
        c for c in candidates if c.rank not in pareto_ranks and c is not selected
    )

    def hover_template(title: str) -> str:
        return (
            f"<b>{title}</b><br>"
            "Rank: %{customdata[0]}<br>"
            "Earth → Saturn flight time: %{x:,.1f} days<br>"
            "Delta-v total: %{y:,.1f} m/s<br>"
            "Launch: %{customdata[1]}<extra></extra>"
        )

    def custom_data(points: tuple[LaunchWindowCandidate, ...]) -> list[list[object]]:
        return [
            [point.rank, point.departure_datetime.astimezone(timezone.utc).isoformat(timespec="minutes")]
            for point in points
        ]

    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=[c.time_of_flight_days for c in regular],
            y=[c.delta_v_total_m_s for c in regular],
            mode="markers",
            name="Candidates",
            marker={
                "color": colors.REFERENCE_ORBIT,
                "size": 9,
                "opacity": 0.85,
                "line": {"color": colors.MARKER_RIM_TRANSLUCENT, "width": 1},
            },
            customdata=custom_data(regular),
            hovertemplate=hover_template("Candidate"),
            meta={"role": "candidates"},
        )
    )
    if pareto:
        figure.add_trace(
            go.Scatter(
                x=[c.time_of_flight_days for c in pareto],
                y=[c.delta_v_total_m_s for c in pareto],
                mode="markers",
                name="Pareto-optimal candidates",
                marker={
                    "color": colors.STATUS_GOOD.light,
                    "size": 11,
                    "symbol": "diamond",
                    "line": {"color": colors.MARKER_RIM_TRANSLUCENT, "width": 1},
                },
                customdata=custom_data(pareto),
                hovertemplate=hover_template("Pareto-optimal candidate"),
                meta={"role": "pareto"},
            )
        )
    if selected is not None:
        figure.add_trace(
            go.Scatter(
                x=[selected.time_of_flight_days],
                y=[selected.delta_v_total_m_s],
                mode="markers",
                name="Selected candidate",
                marker={
                    "color": colors.LAUNCH.light,
                    "size": 18,
                    "symbol": "star",
                    "line": {"color": "white", "width": 2},
                },
                customdata=custom_data((selected,)),
                hovertemplate=hover_template("Selected candidate"),
                meta={"role": "selected"},
            )
        )

    figure.update_layout(
        height=440,
        margin={"l": 20, "r": 20, "t": 30, "b": 20},
        xaxis={
            "title": "Earth → Saturn flight time (days)",
            "gridcolor": colors.GRIDLINE,
            "zeroline": False,
        },
        yaxis={
            "title": "Delta-v total (m/s)",
            "gridcolor": colors.GRIDLINE,
            "zeroline": False,
        },
        legend={"orientation": "h", "y": -0.22, "x": 0.5, "xanchor": "center"},
        hovermode="closest",
        uirevision="launch-window-candidates-v1",
    )
    return figure
