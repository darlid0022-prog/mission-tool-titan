"""Minimal mission-domain objects for multi-leg mission analysis."""

from .builder import (
    build_event,
    build_leg,
    build_mission,
    build_mission_from_trajectory_alternatives,
    build_trajectory_result,
)
from .models import Event, Leg, Mission, TrajectoryResult
from .moon_transfer import SaturnTitanTransferResult, compute_saturn_titan_transfer
from .saturn_staging import (
    SaturnArrivalStagingResult,
    adapt_saturn_arrival_staging_to_leg,
    compute_saturn_arrival_to_staging,
)

__all__ = [
    "Event",
    "Leg",
    "Mission",
    "TrajectoryResult",
    "SaturnTitanTransferResult",
    "SaturnArrivalStagingResult",
    "adapt_saturn_arrival_staging_to_leg",
    "compute_saturn_arrival_to_staging",
    "compute_saturn_titan_transfer",
    "build_event",
    "build_leg",
    "build_mission",
    "build_mission_from_trajectory_alternatives",
    "build_trajectory_result",
]
