"""Cached application services kept separate from the Streamlit page."""

from datetime import date

import streamlit as st

from mission.pareto import ParetoSearchResult, compute_connected_pareto_front
from trajectory import compute_trajectory

PHYSICS_MODEL_VERSION = "deterministic-earth-saturn-v4"
PARETO_MODEL_VERSION = "connected-pareto-v2-real-payload"
LEGACY_SATURN_CAPTURE_ALTITUDE_KM = 2_000.0
DEFAULT_LAUNCH_WINDOW_START = date(2026, 6, 1)
DEFAULT_LAUNCH_WINDOW_END = date(2027, 6, 1)


@st.cache_data(max_entries=32, persist="disk", show_spinner=False)
def compute_cached_trajectory(
    physics_model_version: str,
    destination: str,
    departure_type: str,
    launch_start: date,
    launch_end: date,
    leo_altitude_km: float,
) -> dict:
    """Compute and persist one trajectory for each bounded set of orbital inputs."""
    if physics_model_version != PHYSICS_MODEL_VERSION:
        raise ValueError("Unsupported physics model version.")
    return compute_trajectory(
        destination,
        departure_type,
        launch_start,
        launch_end,
        False,  # Moon transfer is not exposed until it is implemented.
        False,  # Landing is not exposed until it is implemented.
        False,  # Flyby-only mode is not exposed until it is implemented.
        0.0,  # No artificial flyby credit is applied.
        leo_altitude_km,
        LEGACY_SATURN_CAPTURE_ALTITUDE_KM,
    )


@st.cache_data(max_entries=2, persist="disk", show_spinner=False)
def compute_cached_pareto_front(pareto_model_version: str) -> ParetoSearchResult:
    """Persist the fixed deterministic Pareto study across application reruns."""
    if pareto_model_version != PARETO_MODEL_VERSION:
        raise ValueError("Unsupported Pareto model version.")
    return compute_connected_pareto_front()
