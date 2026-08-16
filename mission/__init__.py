"""Minimal mission-domain objects for multi-leg mission analysis."""

from .builder import (
    build_event,
    build_leg,
    build_mission,
    build_mission_from_trajectory_alternatives,
    build_trajectory_result,
)
from .dv_budget import MissionDeltaVBudget, compose_complete_dv_budget
from .full_mission import EarthSaturnTitanMissionResult, compute_earth_saturn_titan_mission
from .models import Event, Leg, Mission, TrajectoryResult
from .moon_transfer import (
    SaturnTitanTransferResult,
    adapt_saturn_titan_transfer_to_leg,
    compute_saturn_titan_transfer,
)
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
    "EarthSaturnTitanMissionResult",
    "MissionDeltaVBudget",
    "adapt_saturn_arrival_staging_to_leg",
    "adapt_saturn_titan_transfer_to_leg",
    "compute_earth_saturn_titan_mission",
    "compose_complete_dv_budget",
    "compute_saturn_arrival_to_staging",
    "compute_saturn_titan_transfer",
    "build_event",
    "build_leg",
    "build_mission",
    "build_mission_from_trajectory_alternatives",
    "build_trajectory_result",
]
