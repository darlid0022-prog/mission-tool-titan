"""Launch-window search: the data contract and injection seam for the engine.

This module defines *only* the shape of a launch-window search - the request
a user submits, the candidate result an engine returns, and the Protocol a
concrete engine must implement - plus one function, `get_launch_window_service`,
that is the single seam a real engine is wired into. No Lambert solve, no
ephemeris sampling, no delta-v/mass optimization happens here: those live in
mission/ (physics, ephemerides, Lambert, optimization, budget) and are
Codex's responsibility on a separate branch (`sprint/launch-engine`), not
this one.

Why an abstract contract instead of calling into an existing engine: Codex is
actively building the real launch-window search engine in parallel. Its exact
Python interface does not exist on this branch yet, and importing anything
speculative from an unmerged branch would create a dependency this branch
cannot honor. `pages/launch_windows.py` is therefore built entirely against
the `LaunchWindowSearchService` Protocol below, never against a concrete
engine. Once Codex's branch merges, wiring the real engine in is a one-line
change: replace `get_launch_window_service`'s body (or monkeypatch it) with
an adapter that satisfies the Protocol - no other file in this module or in
`pages/launch_windows.py` needs to change.

Until that happens, `get_launch_window_service()` returns None and the page
renders an explicit "engine not connected" state - it never fabricates or
displays example/placeholder search results in the running application.
Tests are the only place a fixture implementation of the Protocol is used,
and every such fixture is named/commented as a TEST FIXTURE (see
tests/test_launch_window_service.py and tests/test_launch_windows_ui.py) so
it is never mistaken for real engine output.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol, runtime_checkable

# Julian year in days - matches the convention already used for
# TrajectoryResult.tof_years elsewhere in this app (trajectory.py).
DAYS_PER_YEAR = 365.25

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
    notes: tuple[str, ...] = ()

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

    @property
    def time_of_flight_years(self) -> float:
        """Derived purely from `time_of_flight_days` - never re-requested from the engine."""
        return self.time_of_flight_days / DAYS_PER_YEAR


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
    # Placeholder for a future Pareto-front highlight over these same
    # candidates (see WEEKEND_PLAN/ROADMAP's trade-off objective): None until
    # an engine actually marks a subset as non-dominated, so the page can
    # render "not yet available" instead of a fabricated front.
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


def get_launch_window_service() -> LaunchWindowSearchService | None:
    """Return the connected launch-window search engine, or None if unconnected.

    This is the one seam a real engine is wired into once Codex's branch
    merges: replace this function's body with an adapter satisfying
    `LaunchWindowSearchService` (or monkeypatch this function where the app
    is composed). Every other line in this module and in
    pages/launch_windows.py is written against the Protocol, not this
    function's current stub body, so that swap never requires rewriting
    either. Returning None (rather than a fixture/example engine) is
    deliberate: the running application must never display fabricated
    search results.
    """
    return None
