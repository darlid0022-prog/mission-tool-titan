"""Cached application services kept separate from the Streamlit page."""

from datetime import date

import streamlit as st

from trajectory import compute_trajectory

PHYSICS_MODEL_VERSION = "local-body-mu-v2"


@st.cache_data(max_entries=32, show_spinner=False)
def compute_cached_trajectory(
    physics_model_version: str,
    destination: str,
    departure_type: str,
    launch_start: date,
    launch_end: date,
    leo_altitude_km: float,
    capture_altitude_km: float,
) -> dict:
    """Compute a trajectory once for each bounded set of orbital inputs."""
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
        capture_altitude_km,
    )
