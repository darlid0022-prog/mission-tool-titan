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
    "SaturnTitanTransferResult",
    "SaturnArrivalStagingResult",
    "TitanEdlResult",
    "EarthSaturnTitanMissionResult",
    "MissionDeltaVBudget",
    "HESPEROS_MODEL_VERSION",
    "Manoeuvre",
    "MassArchitectureInfeasibleError",
    "ParametricBusCoefficients",
    "ParametricMassResult",
    "PayloadItem",
    "adapt_saturn_arrival_staging_to_leg",
    "adapt_saturn_titan_transfer_to_leg",
    "compute_earth_saturn_titan_mission",
    "compose_complete_dv_budget",
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
