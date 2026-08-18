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
from .connected_physics import (
    ConnectedFirstOrderResult,
    EarthSaturnHohmannResult,
    SaturnCaptureEllipseResult,
    SaturnHyperbolaResult,
    compute_connected_first_order_chain,
    compute_earth_saturn_hohmann,
    compute_saturn_capture_to_titan_orbit,
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
from .launch_search import (
    compute_pareto_front,
    evaluate_launch_scenario,
    rank_scenarios,
    search_direct_earth_saturn_titan,
)
from .launch_search_models import (
    LaunchScenario,
    LaunchSearchConfig,
    LaunchSearchResult,
    SearchObjective,
    SearchTrajectorySegment,
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
    "LaunchScenario",
    "LaunchSearchConfig",
    "LaunchSearchResult",
    "SearchObjective",
    "SearchTrajectorySegment",
    "ConnectedFirstOrderResult",
    "EarthSaturnHohmannResult",
    "SaturnCaptureEllipseResult",
    "SaturnHyperbolaResult",
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
    "compute_pareto_front",
    "evaluate_launch_scenario",
    "rank_scenarios",
    "search_direct_earth_saturn_titan",
    "compute_connected_first_order_chain",
    "compute_earth_saturn_hohmann",
    "compute_saturn_capture_to_titan_orbit",
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
