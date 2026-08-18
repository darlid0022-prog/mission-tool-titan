"""Cached application services kept separate from the Streamlit page."""

from dataclasses import dataclass
from datetime import date

import pandas as pd
import streamlit as st

from mission.dv_budget import MissionDeltaVBudget, compose_complete_dv_budget
from mission.feasibility_check import (
    SingleStageFeasibilityResult,
    evaluate_single_stage_chemical_feasibility,
)
from mission.full_mission import (
    EarthDestinationMissionResult,
    EarthSaturnTitanMissionResult,
    compute_earth_destination_mission,
    compute_earth_saturn_titan_mission,
)
from mission.gravity_assist import (
    GravityAssistResult,
    compute_earth_flyby_demonstration,
    compute_jupiter_flyby_demonstration,
    compute_venus_flyby_demonstration,
)
from mission.mass_model import PayloadItem
from mission.models import TrajectoryResult
from mission.moon_transfer import SaturnTitanTransferResult
from mission.pareto import ParetoSearchResult, compute_connected_pareto_front
from mission.saturn_staging import SaturnArrivalStagingResult
from mission.sizing import compute_mass_budget
from mission.titan_edl import TitanEdlResult, compute_titan_edl
from mission.ui_text import UI_TEXT
from trajectory import compute_trajectory

PHYSICS_MODEL_VERSION = "deterministic-earth-saturn-v4"
PARETO_MODEL_VERSION = "connected-pareto-v2-real-payload"
LEGACY_SATURN_CAPTURE_ALTITUDE_KM = 2_000.0
DEFAULT_LAUNCH_WINDOW_START = date(2026, 6, 1)
DEFAULT_LAUNCH_WINDOW_END = date(2027, 6, 1)

MISSION_SETUP_STATE_KEY = "mission_setup_inputs"
MISSION_SETUP_REQUIRED_MESSAGE = (
    "Configure and calculate a mission on the Mission setup page first."
)


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


@dataclass(frozen=True)
class MissionSetupInputs:
    """Every simple, user-editable value collected by the Mission setup page.

    Pages other than Mission setup read this back out of st.session_state and
    call compute_mission_bundle() to rebuild the derived results they need -
    this is the generalized form of the trajectory_scene/session_state pattern
    already used for the 3D animation, applied so complex business objects
    never have to be shared directly between independently-run pages.
    """

    destination: str
    selected_moon: str | None
    departure_type: str
    leo_altitude_km: float
    saturn_periapsis_radius_km: float
    saturn_staging_radius_km: float
    titan_capture_altitude_km: float
    launch_window_start: date
    launch_window_end: date
    isp_s: float
    instruments_df: pd.DataFrame


def store_mission_setup_inputs(inputs: MissionSetupInputs) -> None:
    """Persist the mission-setup form inputs so every page can rebuild results."""
    st.session_state[MISSION_SETUP_STATE_KEY] = inputs


def load_mission_setup_inputs() -> MissionSetupInputs | None:
    """Return the last-submitted mission-setup inputs, or None before first submit."""
    return st.session_state.get(MISSION_SETUP_STATE_KEY)


class DestinationNotImplementedError(RuntimeError):
    """Raised when compute_cached_trajectory has no engine for the selection."""


class DirectArrivalOnlyError(RuntimeError):
    """Raised when no moon destination was selected (single-leg arrival only)."""


@dataclass(frozen=True)
class MissionBundle:
    """Every result derived from MissionSetupInputs that other pages render."""

    traj: dict
    # For planet-only destinations `complete_mission` will be the generic
    # EarthDestinationMissionResult and the Saturn/Titan-specific fields will
    # be None. For Saturn->Titan chains the full EarthSaturnTitanMissionResult
    # and related studies are populated.
    complete_mission: EarthDestinationMissionResult | EarthSaturnTitanMissionResult
    staging_result: SaturnArrivalStagingResult | None
    titan_transfer: SaturnTitanTransferResult | None
    titan_edl: TitanEdlResult | None
    complete_dv_budget: MissionDeltaVBudget
    dv_total: float
    mass: dict
    mass_ratio: float
    payload_items: tuple[PayloadItem, ...]
    single_stage_feasibility: SingleStageFeasibilityResult
    earth_saturn_trajectory: TrajectoryResult
    mission_duration_days: float
    flyby_demonstrations: tuple[GravityAssistResult, ...]
    combined_flyby_gain_m_s: float
    single_stage_deficit_m_s: float
    flyby_deficit_coverage: float | None


def compute_mission_bundle(inputs: MissionSetupInputs) -> MissionBundle:
    """Rebuild every derived mission result from stored mission-setup inputs.

    Deterministic and cheap to repeat: compute_cached_trajectory is already
    memoized by @st.cache_data, and every step downstream of it is plain
    Python/pandas arithmetic - so every page can call this on its own rerun
    instead of sharing the complex result objects through session_state.
    """
    with st.spinner(UI_TEXT["earth_saturn_spinner"]):
        traj = compute_cached_trajectory(
            PHYSICS_MODEL_VERSION,
            inputs.destination,
            inputs.departure_type,
            inputs.launch_window_start,
            inputs.launch_window_end,
            inputs.leo_altitude_km,
        )

    if "earth_saturn_leg" not in traj:
        raise DestinationNotImplementedError(
            traj.get("note", UI_TEXT["destination_not_implemented"])
        )
    # Build either the connected Saturn->Titan chain when a moon is selected,
    # or a simplified planet-only mission when no moon is selected. The latter
    # still provides sensible DV/mass numbers by composing the Earth->planet
    # Lambert budget and leaving Saturn/Titan-specific terms as zero.
    earth_leg = traj["earth_saturn_leg"]
    if inputs.selected_moon is None:
        # Planet-only mission: use the generic assembler which returns an
        # EarthDestinationMissionResult with arrival_staging/moon_transfer == None.
        complete_mission = compute_earth_destination_mission(
            earth_leg,
            destination_planet=inputs.destination,
            moon=None,
        )

        staging_result = None
        titan_transfer = None
        titan_edl = None

        # Compose a simplified DV budget: keep the Earth departure and DSM/flyby
        # terms from the Lambert budget and set Saturn/Titan-specific entries to
        # zero so downstream UI can still render a full table consistently.
        earth_budget = traj.get("dv_budget", {})
        earth_departure = float(earth_budget.get("dV from LEO", 0.0))
        dsm_flyby = float(earth_budget.get("dV DSM/Fly-By", 0.0))
        complete_dv_budget = MissionDeltaVBudget(
            earth_departure_m_s=earth_departure,
            dsm_flyby_m_s=dsm_flyby,
            saturn_capture_to_ellipse_m_s=0.0,
            saturn_staging_circularisation_m_s=0.0,
            saturn_titan_departure_m_s=0.0,
            titan_capture_m_s=0.0,
        )

        dv_total = complete_dv_budget.total_m_s
        mass = compute_mass_budget(dv_total, inputs.isp_s, inputs.instruments_df)
        mass_ratio = mass["wet_mass_kg"] / mass["dry_mass_kg"] if mass["dry_mass_kg"] > 0 else 1.0
    else:
        # Connected Saturn->Titan chain: use the historical facade which builds
        # the two Saturn-specific studies and returns the full EarthSaturnTitan
        # mission result expected across the app.
        complete_mission = compute_earth_saturn_titan_mission(
            earth_leg,
            saturn_periapsis_radius_m=float(inputs.saturn_periapsis_radius_km) * 1_000.0,
            saturn_periapsis_radius_provenance=(
                "User-selected Saturn-centered radius; nominal value preserves the "
                "PyKEP Saturn radius plus UI capture altitude."
            ),
            saturn_staging_radius_m=float(inputs.saturn_staging_radius_km) * 1_000.0,
            titan_capture_altitude_m=float(inputs.titan_capture_altitude_km) * 1_000.0,
        )

        staging_result = complete_mission.saturn_arrival_staging
        titan_transfer = complete_mission.saturn_titan_transfer
        titan_edl = compute_titan_edl(
            titan_transfer.v_infinity_titan_m_s,
            titan_transfer.capture_delta_v_m_s,
        )
        complete_dv_budget = compose_complete_dv_budget(
            traj["dv_budget"],
            staging_result,
            titan_transfer,
        )
        dv_total = complete_dv_budget.total_m_s
        mass = compute_mass_budget(dv_total, inputs.isp_s, inputs.instruments_df)
        mass_ratio = mass["wet_mass_kg"] / mass["dry_mass_kg"] if mass["dry_mass_kg"] > 0 else 1.0

    payload_items = tuple(
        PayloadItem(
            name=(str(row["Instrument"]).strip() or f"Payload item {index + 1}"),
            mass_kg=float(row["Masse (kg)"]),
            max_power_w=float(row["Puissance (W)"]),
            data_rate_bps=float(row["Débit (bps)"]),
        )
        for index, (_, row) in enumerate(inputs.instruments_df.fillna(0.0).iterrows())
    )
    single_stage_feasibility = evaluate_single_stage_chemical_feasibility(
        dv_total,
        float(inputs.isp_s),
        payload_items,
    )
    earth_saturn_trajectory = complete_mission.mission.legs[0].trajectory
    assert earth_saturn_trajectory is not None
    assert earth_saturn_trajectory.departure_mjd2000 is not None
    assert earth_saturn_trajectory.arrival_mjd2000 is not None
    mission_duration_days = (
        float(earth_saturn_trajectory.arrival_mjd2000)
        - float(earth_saturn_trajectory.departure_mjd2000)
        + (staging_result.time_of_flight_days if staging_result is not None else 0.0)
        + (titan_transfer.time_of_flight_days if titan_transfer is not None else 0.0)
    )
    flyby_demonstrations = (
        compute_venus_flyby_demonstration(),
        compute_earth_flyby_demonstration(),
        compute_jupiter_flyby_demonstration(),
    )
    combined_flyby_gain_m_s = sum(
        result.heliocentric_speed_change_m_s for result in flyby_demonstrations
    )
    single_stage_deficit_m_s = max(
        dv_total - single_stage_feasibility.maximum_feasible_delta_v_m_s,
        0.0,
    )
    flyby_deficit_coverage = (
        combined_flyby_gain_m_s / single_stage_deficit_m_s
        if single_stage_deficit_m_s > 0.0
        else None
    )

    return MissionBundle(
        traj=traj,
        complete_mission=complete_mission,
        staging_result=staging_result,
        titan_transfer=titan_transfer,
        titan_edl=titan_edl,
        complete_dv_budget=complete_dv_budget,
        dv_total=dv_total,
        mass=mass,
        mass_ratio=mass_ratio,
        payload_items=payload_items,
        single_stage_feasibility=single_stage_feasibility,
        earth_saturn_trajectory=earth_saturn_trajectory,
        mission_duration_days=mission_duration_days,
        flyby_demonstrations=flyby_demonstrations,
        combined_flyby_gain_m_s=combined_flyby_gain_m_s,
        single_stage_deficit_m_s=single_stage_deficit_m_s,
        flyby_deficit_coverage=flyby_deficit_coverage,
    )


def require_mission_bundle() -> MissionBundle | None:
    """Load stored mission-setup inputs and rebuild the full derived bundle.

    Renders the appropriate st.info/st.warning and returns None when the page
    should stop instead of rendering results; callers still call st.stop()
    themselves immediately afterwards, matching every other early-exit guard
    already used in this application.
    """
    inputs = load_mission_setup_inputs()
    if inputs is None:
        st.info(MISSION_SETUP_REQUIRED_MESSAGE)
        return None
    try:
        return compute_mission_bundle(inputs)
    except DestinationNotImplementedError as exc:
        st.warning(str(exc))
        return None
    except DirectArrivalOnlyError as exc:
        st.info(str(exc))
        return None
