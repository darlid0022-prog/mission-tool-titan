"""Minimal mission-domain objects for multi-leg mission analysis."""

from .arrival_staging import (
    ArrivalStagingResult,
    StagingRadiusGuard,
    adapt_arrival_staging_to_leg,
    compute_arrival_to_staging,
)
from .builder import (
    build_event,
    build_leg,
    build_mission,
    build_mission_from_trajectory_alternatives,
    build_trajectory_result,
)
from .dv_budget import MissionDeltaVBudget, compose_complete_dv_budget
from .full_mission import (
    EarthDestinationMissionResult,
    EarthSaturnTitanMissionResult,
    compute_earth_destination_mission,
    compute_earth_saturn_titan_mission,
)
from .mass_model import (
    HESPEROS_MODEL_VERSION,
    Manoeuvre,
    MassArchitectureInfeasibleError,
    ParametricBusCoefficients,
    ParametricMassResult,
    PayloadItem,
    size_parametric_vehicle,
)
from .models import Event, Leg, Mission, TrajectoryResult
from .moon_transfer import (
    SaturnTitanTransferResult,
    adapt_saturn_titan_transfer_to_leg,
    compute_saturn_titan_transfer,
)
from .parent_moon_transfer import (
    ParentMoonTransferResult,
    adapt_parent_moon_transfer_to_leg,
    compute_parent_to_moon_transfer,
)
from .saturn_staging import (
    SaturnArrivalStagingResult,
    adapt_saturn_arrival_staging_to_leg,
    compute_saturn_arrival_to_staging,
)
from .titan_edl import TitanEdlResult, compute_titan_edl

__all__ = [
    "Event",
    "Leg",
    "Mission",
    "TrajectoryResult",
    "ArrivalStagingResult",
    "StagingRadiusGuard",
    "ParentMoonTransferResult",
    "SaturnTitanTransferResult",
    "SaturnArrivalStagingResult",
    "TitanEdlResult",
    "EarthSaturnTitanMissionResult",
    "EarthDestinationMissionResult",
    "MissionDeltaVBudget",
    "HESPEROS_MODEL_VERSION",
    "Manoeuvre",
    "MassArchitectureInfeasibleError",
    "ParametricBusCoefficients",
    "ParametricMassResult",
    "PayloadItem",
    "adapt_parent_moon_transfer_to_leg",
    "adapt_arrival_staging_to_leg",
    "adapt_saturn_arrival_staging_to_leg",
    "adapt_saturn_titan_transfer_to_leg",
    "compute_earth_saturn_titan_mission",
    "compute_earth_destination_mission",
    "compose_complete_dv_budget",
    "compute_arrival_to_staging",
    "compute_parent_to_moon_transfer",
    "compute_saturn_arrival_to_staging",
    "compute_saturn_titan_transfer",
    "compute_titan_edl",
    "size_parametric_vehicle",
    "build_event",
    "build_leg",
    "build_mission",
    "build_mission_from_trajectory_alternatives",
    "build_trajectory_result",
]
