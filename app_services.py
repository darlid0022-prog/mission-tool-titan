"""Cached application services kept separate from the Streamlit page."""

import base64
import binascii
import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from urllib.parse import urlencode, urlsplit

import pandas as pd
import streamlit as st

from mission import physics
from mission.bodies import resolve_body
from mission.capabilities import MOON_DESTINATIONS, PLANET_DESTINATIONS
from mission.connected_physics import ConnectedFirstOrderResult
from mission.constants import (
    F_RING_REFERENCE_RADIUS_M,
    NOMINAL_SATURN_PERIAPSIS_RADIUS_M,
    TITAN_MEAN_ORBIT_RADIUS_M,
)
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
    MissionSegment,
    OrbitInsertionResult,
    compute_cassini_historical_tour,
    compute_earth_flyby_demonstration,
    compute_jupiter_flyby_demonstration,
    compute_venus_flyby_demonstration,
)
from mission.mass_model import PayloadItem
from mission.models import Leg, TrajectoryResult
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
MISSION_QUERY_PARAM = "mission"
MISSION_QUERY_VERSION = 2
LEGACY_MISSION_QUERY_VERSION = 1
MISSION_QUERY_RESTORED_KEY = "mission_query_restored"
MISSION_QUERY_MIGRATION_WARNING_KEY = "mission_query_migration_warning"
MISSION_SETUP_REQUIRED_MESSAGE = (
    "Configure and calculate a mission on the Mission setup page first."
)

# Trajectory-type choices, offered only for a Saturn destination (see
# pages/mission_setup.py). TRAJECTORY_TYPE_DIRECT is the pre-existing,
# unchanged Lambert-solve behavior; TRAJECTORY_TYPE_CASSINI_HISTORICAL
# replaces it with the real 1997-2004 Cassini VVEJGA tour's own dates and
# delta-v (see mission/gravity_assist.py's compute_cassini_historical_tour).
TRAJECTORY_TYPE_DIRECT = "Direct"
TRAJECTORY_TYPE_CASSINI_HISTORICAL = "Cassini historical gravity assist"
TRAJECTORY_TYPES = (TRAJECTORY_TYPE_DIRECT, TRAJECTORY_TYPE_CASSINI_HISTORICAL)


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
    # Defaults to the pre-existing behavior so every old call site (and every
    # decoded pre-this-feature share link) keeps computing the same Lambert-
    # solve mission it always did.
    trajectory_type: str = TRAJECTORY_TYPE_DIRECT
    connected_saturn_periapsis_radius_km: float = (
        NOMINAL_SATURN_PERIAPSIS_RADIUS_M / 1_000.0
    )
    connected_capture_apoapsis_radius_km: float = (
        TITAN_MEAN_ORBIT_RADIUS_M / 1_000.0
    )

    def __post_init__(self) -> None:
        periapsis_m = float(self.connected_saturn_periapsis_radius_km) * 1_000.0
        apoapsis_m = float(self.connected_capture_apoapsis_radius_km) * 1_000.0
        if not math.isfinite(periapsis_m) or periapsis_m <= F_RING_REFERENCE_RADIUS_M:
            raise ValueError(
                "Connected Saturn periapsis must lie strictly outside the reference F ring."
            )
        if apoapsis_m != TITAN_MEAN_ORBIT_RADIUS_M:
            raise ValueError(
                "Connected capture-ellipse apoapsis must equal Titan's mean orbital radius."
            )
        if apoapsis_m <= periapsis_m:
            raise ValueError("Connected capture-ellipse apoapsis must exceed periapsis.")


INSTRUMENT_COLUMNS = (
    "Instrument",
    "Cible",
    "Masse (kg)",
    "Puissance (W)",
    "Débit (bps)",
)


def _validated_number(
    name: str,
    value: object,
    *,
    minimum: float,
    maximum: float,
) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{name} must be numeric.")
    converted = float(value)
    if not math.isfinite(converted) or not minimum <= converted <= maximum:
        raise ValueError(f"{name} is outside the supported range.")
    return converted


def _instrument_records(instruments_df: pd.DataFrame) -> list[dict[str, object]]:
    if tuple(instruments_df.columns) != INSTRUMENT_COLUMNS:
        raise ValueError("The shared instrument table has an unsupported schema.")
    # Pandas' JSON conversion normalizes numpy scalar values into plain JSON
    # scalars while preserving the exact row/column order used by the editor.
    records = json.loads(instruments_df.to_json(orient="records"))
    if not isinstance(records, list) or len(records) > 100:
        raise ValueError("The shared instrument table has too many rows.")
    return records


def encode_mission_setup_query(inputs: MissionSetupInputs) -> dict[str, str]:
    """Serialize only user inputs into one versioned, URL-safe query parameter."""
    payload = {
        "version": MISSION_QUERY_VERSION,
        "destination": inputs.destination,
        "selected_moon": inputs.selected_moon,
        "departure_type": inputs.departure_type,
        "leo_altitude_km": inputs.leo_altitude_km,
        "connected_saturn_periapsis_radius_km": (
            inputs.connected_saturn_periapsis_radius_km
        ),
        "connected_capture_apoapsis_radius_km": (
            inputs.connected_capture_apoapsis_radius_km
        ),
        "launch_window_start": inputs.launch_window_start.isoformat(),
        "launch_window_end": inputs.launch_window_end.isoformat(),
        "isp_s": inputs.isp_s,
        "instruments": _instrument_records(inputs.instruments_df),
        "trajectory_type": inputs.trajectory_type,
    }
    serialized = json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    token = base64.urlsafe_b64encode(serialized).decode("ascii").rstrip("=")
    return {MISSION_QUERY_PARAM: token}


def decode_mission_setup_query(
    query_params: Mapping[str, str | list[str]],
) -> MissionSetupInputs:
    """Validate and reconstruct mission inputs from a shared URL query mapping."""
    token = query_params.get(MISSION_QUERY_PARAM)
    if isinstance(token, list):
        token = token[-1] if len(token) == 1 else None
    if not token or not isinstance(token, str) or len(token) > 32_000:
        raise ValueError("The mission share parameter is missing or invalid.")
    try:
        padding = "=" * (-len(token) % 4)
        raw = base64.b64decode(token + padding, altchars=b"-_", validate=True)
        payload = json.loads(raw.decode("utf-8"))
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("The mission share parameter is malformed.") from exc
    if not isinstance(payload, dict) or payload.get("version") not in {
        LEGACY_MISSION_QUERY_VERSION,
        MISSION_QUERY_VERSION,
    }:
        raise ValueError("The mission share parameter uses an unsupported version.")
    query_version = payload["version"]

    destination = payload.get("destination")
    if destination not in PLANET_DESTINATIONS:
        raise ValueError("The shared destination is not supported.")
    selected_moon = payload.get("selected_moon")
    if selected_moon is not None and MOON_DESTINATIONS.get(selected_moon) != destination:
        raise ValueError("The shared moon is incompatible with its parent planet.")
    departure_type = payload.get("departure_type")
    if departure_type not in {"Direct", "LEO"}:
        raise ValueError("The shared departure type is not supported.")
    # Absent for links shared before this option existed: falls back to the
    # pre-existing Direct-solve behavior, same as a fresh MissionSetupInputs.
    trajectory_type = payload.get("trajectory_type", TRAJECTORY_TYPE_DIRECT)
    if trajectory_type not in TRAJECTORY_TYPES:
        raise ValueError("The shared trajectory type is not supported.")

    try:
        launch_window_start = date.fromisoformat(payload["launch_window_start"])
        launch_window_end = date.fromisoformat(payload["launch_window_end"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("The shared launch window is invalid.") from exc
    if launch_window_end < launch_window_start:
        raise ValueError("The shared launch window ends before it starts.")

    records = payload.get("instruments")
    if not isinstance(records, list) or len(records) > 100:
        raise ValueError("The shared instrument table is invalid.")
    normalized_records: list[dict[str, object]] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict) or set(record) != set(INSTRUMENT_COLUMNS):
            raise ValueError("The shared instrument table has an unsupported schema.")
        name = record["Instrument"]
        target = record["Cible"]
        if not isinstance(name, str) or not name.strip() or len(name) > 200:
            raise ValueError(f"Shared instrument row {index + 1} has an invalid name.")
        if not isinstance(target, str) or not target.strip() or len(target) > 100:
            raise ValueError(f"Shared instrument row {index + 1} has an invalid target.")
        normalized_records.append(
            {
                "Instrument": name,
                "Cible": target,
                "Masse (kg)": _validated_number(
                    "instrument mass", record["Masse (kg)"], minimum=0.0, maximum=1e9
                ),
                "Puissance (W)": _validated_number(
                    "instrument power", record["Puissance (W)"], minimum=0.0, maximum=1e9
                ),
                "Débit (bps)": _validated_number(
                    "instrument data rate", record["Débit (bps)"], minimum=0.0, maximum=1e15
                ),
            }
        )
    instruments_df = pd.DataFrame(normalized_records, columns=INSTRUMENT_COLUMNS)

    if query_version == LEGACY_MISSION_QUERY_VERSION:
        # Validate the old values, but never reinterpret their inner-ring and
        # staging/Titan-study meanings as the new connected architecture.
        legacy_periapsis_radius_km = _validated_number(
            "Legacy Saturn periapsis radius",
            payload.get("saturn_periapsis_radius_km"),
            minimum=60_269.0,
            maximum=66_899.0,
        )
        legacy_staging_radius_km = _validated_number(
            "Legacy Saturn staging radius",
            payload.get("saturn_staging_radius_km"),
            minimum=480_001.0,
            maximum=1_221_899.0,
        )
        legacy_titan_capture_altitude_km = _validated_number(
            "Legacy Titan capture altitude",
            payload.get("titan_capture_altitude_km"),
            minimum=1_000.0,
            maximum=100_000.0,
        )
        connected_periapsis_radius_km = NOMINAL_SATURN_PERIAPSIS_RADIUS_M / 1_000.0
        connected_apoapsis_radius_km = TITAN_MEAN_ORBIT_RADIUS_M / 1_000.0
    else:
        legacy_periapsis_radius_km = 62_330.0
        legacy_staging_radius_km = 600_000.0
        legacy_titan_capture_altitude_km = 1_500.0
        connected_periapsis_radius_km = _validated_number(
            "Connected Saturn periapsis radius",
            payload.get("connected_saturn_periapsis_radius_km"),
            minimum=F_RING_REFERENCE_RADIUS_M / 1_000.0 + 1.0,
            maximum=TITAN_MEAN_ORBIT_RADIUS_M / 1_000.0 - 1.0,
        )
        connected_apoapsis_radius_km = _validated_number(
            "Connected capture-ellipse apoapsis",
            payload.get("connected_capture_apoapsis_radius_km"),
            minimum=connected_periapsis_radius_km + 1.0,
            maximum=TITAN_MEAN_ORBIT_RADIUS_M / 1_000.0,
        )

    return MissionSetupInputs(
        destination=destination,
        selected_moon=selected_moon,
        departure_type=departure_type,
        leo_altitude_km=_validated_number(
            "LEO altitude", payload.get("leo_altitude_km"), minimum=100.0, maximum=100_000.0
        ),
        saturn_periapsis_radius_km=legacy_periapsis_radius_km,
        saturn_staging_radius_km=legacy_staging_radius_km,
        titan_capture_altitude_km=legacy_titan_capture_altitude_km,
        launch_window_start=launch_window_start,
        launch_window_end=launch_window_end,
        isp_s=_validated_number("Isp", payload.get("isp_s"), minimum=100.0, maximum=100_000.0),
        instruments_df=instruments_df,
        trajectory_type=trajectory_type,
        connected_saturn_periapsis_radius_km=connected_periapsis_radius_km,
        connected_capture_apoapsis_radius_km=connected_apoapsis_radius_km,
    )


def build_mission_share_url(base_url: str, query_params: Mapping[str, str]) -> str:
    """Return a stable absolute URL containing the encoded mission inputs."""
    parsed = urlsplit(base_url)
    if parsed.scheme and parsed.netloc:
        current_location = f"{parsed.scheme}://{parsed.netloc}{parsed.path or '/'}"
    else:
        current_location = base_url.split("?", 1)[0]
    return f"{current_location}?{urlencode(dict(query_params))}"


def restore_mission_setup_from_query_params(
    query_params: Mapping[str, str | list[str]],
) -> bool:
    """Restore a shared mission once, before st.navigation renders any page."""
    if st.session_state.get(MISSION_QUERY_RESTORED_KEY):
        return False
    st.session_state[MISSION_QUERY_RESTORED_KEY] = True
    if MISSION_QUERY_PARAM not in query_params:
        return False
    token = query_params[MISSION_QUERY_PARAM]
    if isinstance(token, list):
        token = token[-1]
    padding = "=" * (-len(token) % 4)
    raw_payload = json.loads(
        base64.b64decode(token + padding, altchars=b"-_", validate=True).decode("utf-8")
    )
    st.session_state[MISSION_SETUP_STATE_KEY] = decode_mission_setup_query(query_params)
    if raw_payload.get("version") == LEGACY_MISSION_QUERY_VERSION:
        st.session_state[MISSION_QUERY_MIGRATION_WARNING_KEY] = (
            "This version 1 link used the legacy 62,330/600,000 km Saturn studies. "
            "It was explicitly migrated to the version 2 connected architecture: "
            "150,000 km periapsis and 1,221,870 km final Saturn-centred radius."
        )
    return True


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
    # Isolated, unpowered demonstrators (see pages/gravity_assists.py) - kept
    # here only as individual results. Never summed: each flyby's heliocentric
    # speed gain depends on the incoming state the *previous* leg would have
    # delivered, which none of these independently-computed demonstrators
    # supplies to the next, so a Venus+Earth+Jupiter total would overstate
    # what a real connected multi-leg trajectory could actually bank. Gravity-
    # assist delta-v savings remain unavailable until a connected multi-leg
    # trajectory (not these isolated demonstrators) is computed end-to-end.
    flyby_demonstrations: tuple[GravityAssistResult, ...]
    # Populated only for TRAJECTORY_TYPE_CASSINI_HISTORICAL - the five real
    # Cassini VVEJGA legs this bundle's delta-v/duration were computed from.
    # None for every other trajectory type/destination.
    cassini_tour: tuple[MissionSegment, ...] | None
    connected_first_order: ConnectedFirstOrderResult | None


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
    # Build one of three mission shapes: the historical Cassini-style
    # gravity-assist trajectory (real dates/delta-v, Saturn only), the
    # connected Saturn->Titan chain when a moon is selected, or a simplified
    # planet-only mission when no moon is selected. The latter two still
    # provide sensible DV/mass numbers by composing the Earth->planet Lambert
    # budget and leaving Saturn/Titan-specific terms as zero.
    earth_leg = traj["earth_saturn_leg"]
    cassini_tour: tuple[MissionSegment, ...] | None = None
    connected_first_order: ConnectedFirstOrderResult | None = None
    if inputs.destination == "Saturn" and inputs.trajectory_type == TRAJECTORY_TYPE_CASSINI_HISTORICAL:
        # The whole point of a gravity-assist tour is that its flybys are
        # unpowered: only the real Earth-departure injection and the real
        # Saturn Orbit Insertion (SOI) capture burn cost delta-v, and the
        # mission duration is the real Oct 1997 -> Jul 2004 cruise - none of
        # this depends on the user's chosen launch window/departure type.
        cassini_tour = compute_cassini_historical_tour()
        departure_segment = cassini_tour[0]
        soi_segment = cassini_tour[-1]
        soi_result = soi_segment.result
        assert isinstance(soi_result, OrbitInsertionResult)

        earth = resolve_body("Earth")
        assert earth.pykep_body is not None
        r_leo = earth.pykep_body.get_radius() + float(inputs.leo_altitude_km) * 1_000.0
        v_inf_depart = math.sqrt(
            sum(value**2 for value in departure_segment.departure_v_infinity_m_s)
        )
        departure_delta_v = physics.delta_v_injection(v_inf_depart, earth.get_mu_self(), r_leo)

        historical_trajectory = TrajectoryResult(
            departure_mjd2000=departure_segment.departure_epoch_mjd2000,
            arrival_mjd2000=soi_segment.arrival_epoch_mjd2000,
            tof_years=(
                (soi_segment.arrival_epoch_mjd2000 - departure_segment.departure_epoch_mjd2000)
                / 365.25
            ),
            v_inf_depart=v_inf_depart,
            v_inf_arrival=soi_result.v_infinity_magnitude_m_s,
            delta_v=departure_delta_v,
            method="cassini_historical_vvejga",
            notes=(
                "Real Cassini VVEJGA tour (Earth -> Venus -> Venus -> Earth -> Jupiter -> "
                "Saturn); delta_v is Earth-departure injection only, matching how every "
                "other Earth-departure leg in this app reports delta_v."
            ),
        )
        historical_leg = Leg(
            origin="Earth",
            destination="Saturn",
            trajectory=historical_trajectory,
            notes="Historical Cassini-style gravity-assist departure-to-SOI summary leg.",
        )
        complete_mission = compute_earth_destination_mission(
            historical_leg,
            destination_planet="Saturn",
            moon=None,
        )

        staging_result = None
        titan_transfer = None
        titan_edl = None

        # SOI captured Cassini into an ellipse (not a circular staging orbit,
        # and with no further burns modeled here), so its delta-v is carried
        # on the "capture to transfer ellipse" term; every Titan-chain-specific
        # term is correctly zero since this trajectory type does not model a
        # moon transfer at all.
        complete_dv_budget = MissionDeltaVBudget(
            earth_departure_m_s=departure_delta_v,
            dsm_flyby_m_s=0.0,
            saturn_capture_to_ellipse_m_s=soi_result.delta_v_m_s,
            saturn_staging_circularisation_m_s=0.0,
            saturn_titan_departure_m_s=0.0,
            titan_capture_m_s=0.0,
        )
        dv_total = complete_dv_budget.total_m_s
        mass = compute_mass_budget(dv_total, inputs.isp_s, inputs.instruments_df)
        mass_ratio = mass["wet_mass_kg"] / mass["dry_mass_kg"] if mass["dry_mass_kg"] > 0 else 1.0
    elif inputs.selected_moon is None:
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
            connected_periapsis_radius_m=(
                float(inputs.connected_saturn_periapsis_radius_km) * 1_000.0
            ),
            connected_apoapsis_radius_m=(
                float(inputs.connected_capture_apoapsis_radius_km) * 1_000.0
            ),
        )

        staging_result = complete_mission.saturn_arrival_staging
        titan_transfer = complete_mission.saturn_titan_transfer
        titan_edl = compute_titan_edl(
            titan_transfer.v_infinity_titan_m_s,
            titan_transfer.capture_delta_v_m_s,
        )
        earth = resolve_body("Earth")
        assert earth.pykep_body is not None
        earth_trajectory = earth_leg.trajectory
        assert earth_trajectory is not None
        assert earth_trajectory.v_inf_depart is not None
        complete_dv_budget = compose_complete_dv_budget(
            {
                **traj["dv_budget"],
                "dV from LEO": physics.delta_v_injection(
                    earth_trajectory.v_inf_depart,
                    earth.get_mu_self(),
                    earth.pykep_body.get_radius() + float(inputs.leo_altitude_km) * 1_000.0,
                ),
            },
            staging_result,
            titan_transfer,
            connected_result=complete_mission.connected_first_order,
        )
        connected_first_order = complete_mission.connected_first_order
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
    if connected_first_order is not None:
        mission_duration_days = (
            float(earth_saturn_trajectory.arrival_mjd2000)
            - float(earth_saturn_trajectory.departure_mjd2000)
            + connected_first_order.saturn_capture.time_of_flight_days
        )
    flyby_demonstrations = (
        compute_venus_flyby_demonstration(),
        compute_earth_flyby_demonstration(),
        compute_jupiter_flyby_demonstration(),
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
        cassini_tour=cassini_tour,
        connected_first_order=connected_first_order,
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
