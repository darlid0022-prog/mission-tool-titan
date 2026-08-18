"""Launch-window UI contract and adapter seam for the scientific engine.

The authoritative dates, ephemerides, Lambert solution, capture physics,
ranking, Pareto front, assumptions, and drawable coordinates remain in
``mission.launch_search_*``. The concrete adapter returned here changes only
representations: UI names to engine enums, resolution names to documented grid
steps, MJD2000 to UTC datetimes, and C3 from m²/s² to km²/s². Delta-v values and
trajectory coordinates are copied without recomputation.
"""

from __future__ import annotations

import dataclasses
import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from mission.launch_search_models import SearchTrajectorySegment

if TYPE_CHECKING:
    from app_services import MissionSetupInputs

# Julian year in days - matches the convention already used for
# TrajectoryResult.tof_years elsewhere in this app (trajectory.py).
DAYS_PER_YEAR = 365.25
SECONDS_PER_DAY = 86_400.0

MAX_LAUNCH_WINDOW_RESULTS = 200

LAUNCH_WINDOW_OBJECTIVE_MIN_DELTA_V = "min_delta_v"
LAUNCH_WINDOW_OBJECTIVE_MIN_DURATION = "min_duration"
LAUNCH_WINDOW_OBJECTIVE_MIN_C3 = "min_c3"
LAUNCH_WINDOW_OBJECTIVE_TRADE_OFF = "trade_off"

LAUNCH_WINDOW_OBJECTIVES = (
    LAUNCH_WINDOW_OBJECTIVE_MIN_DELTA_V,
    LAUNCH_WINDOW_OBJECTIVE_MIN_DURATION,
    LAUNCH_WINDOW_OBJECTIVE_MIN_C3,
    LAUNCH_WINDOW_OBJECTIVE_TRADE_OFF,
)

# Display labels for the UI - kept next to the constants they label so the
# two can never drift out of sync.
LAUNCH_WINDOW_OBJECTIVE_LABELS: dict[str, str] = {
    LAUNCH_WINDOW_OBJECTIVE_MIN_DELTA_V: "Minimum delta-v",
    LAUNCH_WINDOW_OBJECTIVE_MIN_DURATION: "Minimum duration",
    LAUNCH_WINDOW_OBJECTIVE_MIN_C3: "Minimum C3",
    LAUNCH_WINDOW_OBJECTIVE_TRADE_OFF: "Trade-off (multi-objective)",
}

LAUNCH_WINDOW_RESOLUTION_FAST = "fast"
LAUNCH_WINDOW_RESOLUTION_DETAILED = "detailed"

LAUNCH_WINDOW_RESOLUTIONS = (
    LAUNCH_WINDOW_RESOLUTION_FAST,
    LAUNCH_WINDOW_RESOLUTION_DETAILED,
)

LAUNCH_WINDOW_RESOLUTION_LABELS: dict[str, str] = {
    LAUNCH_WINDOW_RESOLUTION_FAST: "Fast (coarse grid)",
    LAUNCH_WINDOW_RESOLUTION_DETAILED: "Detailed (fine grid)",
}

SELECTED_LAUNCH_WINDOW_CANDIDATE_STATE_KEY = "selected_launch_window_candidate"
ACTIVE_LAUNCH_WINDOW_CANDIDATE_STATE_KEY = "active_launch_window_candidate"

MISSION_SCENARIO_BASELINE_LABEL = "Mission setup baseline"
MISSION_SCENARIO_LAUNCH_WINDOW_LABEL = "Selected launch-window candidate"
MISSION_SCENARIO_CASSINI_LABEL = "Cassini VVEJGA"


@dataclass(frozen=True)
class LaunchWindowSearchRequest:
    """Every input the user submits from the `Find launch windows` form."""

    search_window_start: date
    search_window_end: date
    min_time_of_flight_days: float
    max_time_of_flight_days: float
    objective: str
    resolution: str
    max_results: int

    def __post_init__(self) -> None:
        if not isinstance(self.search_window_start, date) or not isinstance(
            self.search_window_end, date
        ):
            raise ValueError("search_window_start and search_window_end must be dates.")
        if self.search_window_end <= self.search_window_start:
            raise ValueError("search_window_end must be after search_window_start.")
        if (
            not math.isfinite(self.min_time_of_flight_days)
            or self.min_time_of_flight_days <= 0.0
        ):
            raise ValueError("min_time_of_flight_days must be a positive, finite number of days.")
        if (
            not math.isfinite(self.max_time_of_flight_days)
            or self.max_time_of_flight_days <= 0.0
        ):
            raise ValueError("max_time_of_flight_days must be a positive, finite number of days.")
        if self.max_time_of_flight_days < self.min_time_of_flight_days:
            raise ValueError(
                "max_time_of_flight_days must be greater than or equal to "
                "min_time_of_flight_days."
            )
        if self.objective not in LAUNCH_WINDOW_OBJECTIVES:
            raise ValueError(f"objective must be one of {LAUNCH_WINDOW_OBJECTIVES}.")
        if self.resolution not in LAUNCH_WINDOW_RESOLUTIONS:
            raise ValueError(f"resolution must be one of {LAUNCH_WINDOW_RESOLUTIONS}.")
        if isinstance(self.max_results, bool) or not isinstance(self.max_results, int):
            raise ValueError("max_results must be an integer.")
        if not 1 <= self.max_results <= MAX_LAUNCH_WINDOW_RESULTS:
            raise ValueError(f"max_results must be between 1 and {MAX_LAUNCH_WINDOW_RESULTS}.")


@dataclass(frozen=True)
class LaunchWindowCandidate:
    """One ranked launch-window result, exactly the fields the page displays.

    Every numeric field is engine output - this dataclass only validates
    shape (finite, correctly ordered, non-negative where physically required),
    it never computes or derives a physical value the engine did not supply.
    """

    rank: int
    departure_datetime: datetime
    saturn_arrival_datetime: datetime
    scenario_end_datetime: datetime
    time_of_flight_days: float
    c3_km2_s2: float
    v_infinity_earth_m_s: float
    v_infinity_saturn_m_s: float
    delta_v_departure_m_s: float
    delta_v_capture_m_s: float
    delta_v_titan_circularization_m_s: float
    delta_v_total_m_s: float
    scenario_id: str = ""
    notes: tuple[str, ...] = ()
    segments: tuple[SearchTrajectorySegment, ...] = ()

    def __post_init__(self) -> None:
        if self.rank < 1:
            raise ValueError("rank must be a positive integer (1 = best).")
        for label, value in (
            ("departure_datetime", self.departure_datetime),
            ("saturn_arrival_datetime", self.saturn_arrival_datetime),
            ("scenario_end_datetime", self.scenario_end_datetime),
        ):
            if not isinstance(value, datetime):
                raise ValueError(f"{label} must be a datetime.")
        if self.saturn_arrival_datetime <= self.departure_datetime:
            raise ValueError("saturn_arrival_datetime must be after departure_datetime.")
        if self.scenario_end_datetime < self.saturn_arrival_datetime:
            raise ValueError("scenario_end_datetime must not precede saturn_arrival_datetime.")
        for field_name in (
            "time_of_flight_days",
            "c3_km2_s2",
            "v_infinity_earth_m_s",
            "v_infinity_saturn_m_s",
            "delta_v_departure_m_s",
            "delta_v_capture_m_s",
            "delta_v_titan_circularization_m_s",
            "delta_v_total_m_s",
        ):
            value = getattr(self, field_name)
            if not math.isfinite(value) or value < 0.0:
                raise ValueError(f"{field_name} must be a finite, non-negative number.")
        if not all(isinstance(segment, SearchTrajectorySegment) for segment in self.segments):
            raise TypeError("segments must contain only SearchTrajectorySegment values.")

    @property
    def time_of_flight_years(self) -> float:
        """Derived purely from `time_of_flight_days` - never re-requested from the engine."""
        return self.time_of_flight_days / DAYS_PER_YEAR

    @property
    def total_duration_days(self) -> float:
        """The full reference-scenario span: departure to scenario end.

        Deliberately NOT the same quantity as `time_of_flight_days` (the
        Earth -> Saturn cruise only): this also covers the Saturn
        capture-to-ellipse burn and the circularization to Titan's orbital
        radius that happen after arrival, per `scenario_end_datetime`.
        Computed purely from the two already-validated datetimes below - not
        re-requested from the engine - but numerically identical to it: both
        datetimes were themselves built from the engine's own MJD2000 epochs,
        so this recovers the engine's total_duration_days without a second,
        independently-drifting field.
        """
        return (
            self.scenario_end_datetime - self.departure_datetime
        ).total_seconds() / SECONDS_PER_DAY

    @property
    def total_duration_years(self) -> float:
        """Derived purely from `total_duration_days` - never re-requested from the engine."""
        return self.total_duration_days / DAYS_PER_YEAR

    def segments_for_scene(
        self,
        *,
        reference_frame: str,
        distance_unit: str,
    ) -> tuple[SearchTrajectorySegment, ...]:
        """Select one physically homogeneous scene without converting coordinates."""
        if not reference_frame or not distance_unit:
            raise ValueError("reference_frame and distance_unit must not be empty.")
        matching_frame = tuple(
            segment for segment in self.segments if segment.frame == reference_frame
        )
        mismatched_units = tuple(
            segment for segment in matching_frame if segment.unit != distance_unit
        )
        if mismatched_units:
            raise ValueError(
                f"Scene {reference_frame!r} contains segments in a unit other than "
                f"{distance_unit!r}; refusing to mix coordinate scales."
            )
        return tuple(segment for segment in matching_frame if segment.unit == distance_unit)


@dataclass(frozen=True)
class LaunchWindowSearchResult:
    """Every candidate an engine found for one `LaunchWindowSearchRequest`."""

    request: LaunchWindowSearchRequest
    candidates: tuple[LaunchWindowCandidate, ...]
    engine_name: str
    # Free-text notes the engine wants surfaced in the page's assumptions
    # panel (grid resolution, ephemeris source, revolution count, etc.) -
    # never fabricated by this module.
    assumptions: tuple[str, ...] = ()
    # Ranks of retained candidates that the scientific engine marked as
    # non-dominated. None remains supported for test/third-party services that
    # do not provide Pareto membership.
    pareto_candidate_ranks: tuple[int, ...] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.request, LaunchWindowSearchRequest):
            raise TypeError("request must be a LaunchWindowSearchRequest.")
        if not isinstance(self.engine_name, str) or not self.engine_name.strip():
            raise ValueError("engine_name must be a non-empty string.")
        ranks = [candidate.rank for candidate in self.candidates]
        if len(set(ranks)) != len(ranks):
            raise ValueError("candidates must have unique ranks.")
        if len(self.candidates) > self.request.max_results:
            raise ValueError("candidates must not exceed the request's max_results.")
        if self.pareto_candidate_ranks is not None and not set(
            self.pareto_candidate_ranks
        ).issubset(ranks):
            raise ValueError("pareto_candidate_ranks must reference ranks present in candidates.")


class LaunchWindowSearchError(RuntimeError):
    """Raised by a connected engine when a search cannot be completed.

    Distinct from a ValueError raised by LaunchWindowSearchRequest's own
    validation (a malformed request never reaches an engine at all).
    """


@runtime_checkable
class LaunchWindowSearchService(Protocol):
    """The contract any concrete launch-window search engine must satisfy.

    `pages/launch_windows.py` depends on this Protocol only - never on a
    concrete implementation - so the real engine can be swapped in later
    (see this module's docstring) without changing the page.
    """

    def search(self, request: LaunchWindowSearchRequest) -> LaunchWindowSearchResult: ...


def get_launch_window_service() -> LaunchWindowSearchService:
    """Return the adapter backed by the authoritative mission search engine."""
    from launch_window_engine_adapter import MissionLaunchWindowSearchAdapter

    return MissionLaunchWindowSearchAdapter()


def apply_candidate_to_mission_setup(
    candidate: LaunchWindowCandidate,
    current_inputs: "MissionSetupInputs",
) -> "MissionSetupInputs":
    """Adapt one chosen candidate into an updated Mission-setup input set.

    Minimal, isolated "send to 3D" adapter: it narrows `current_inputs`'
    launch window to the single day the candidate departs on and forces
    the Direct trajectory type, then returns the updated inputs for the
    caller to store (see app_services.store_mission_setup_inputs). It does
    not compute or duplicate any trajectory itself - narrowing the launch
    window and letting the existing, unmodified Mission-setup pipeline
    (trajectory.py's compute_trajectory, already used everywhere else in
    this app) resolve it is how this app already lets a user pick a
    specific departure date, and how it already reaches
    pages/trajectory_3d.py (the completed, unmodified 3D page) without a
    second trajectory or visualization engine.

    Every other field (destination, moon, radii, Isp, instruments) is
    copied unchanged from `current_inputs`: this adapter only ever answers
    "when do we leave", never "what mission are we flying". Requires an
    existing MissionSetupInputs (from app_services.load_mission_setup_inputs())
    - callers should offer this action only once a mission is configured,
    matching every other page's existing "configure a mission first" guard,
    rather than this module inventing default mission parameters that could
    drift from Mission setup's own defaults.

    Isolated deliberately: once the real engine can hand off exact position
    vectors (or a full trajectory object) directly, this function is the
    only place that needs to change - neither
    LaunchWindowCandidate/LaunchWindowSearchResult above nor
    pages/trajectory_3d.py would need to.
    """
    # Local import: app_services is the UI orchestration layer this module
    # is deliberately kept independent of at import time (see module
    # docstring on isolation), even though no import cycle exists today.
    from app_services import TRAJECTORY_TYPE_DIRECT

    departure_date = candidate.departure_datetime.date()
    return dataclasses.replace(
        current_inputs,
        launch_window_start=departure_date,
        launch_window_end=departure_date + timedelta(days=1),
        trajectory_type=TRAJECTORY_TYPE_DIRECT,
    )
