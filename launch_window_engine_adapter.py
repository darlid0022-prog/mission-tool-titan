"""Adapter between the launch-window UI contract and the scientific engine.

The adapter performs representation changes only. It contains no trajectory,
Lambert, capture, delta-v, ranking, or Pareto formula.

Grid presets:
- ``fast``: 60-day departure and flight-time steps, no local refinement,
  16 samples per drawable segment (engine ``fast_mode``).
- ``detailed``: 15-day departure and 30-day flight-time steps, three locally
  refined seeds, 48 samples per drawable segment.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from launch_window_service import (
    LAUNCH_WINDOW_OBJECTIVE_MIN_C3,
    LAUNCH_WINDOW_OBJECTIVE_MIN_DELTA_V,
    LAUNCH_WINDOW_OBJECTIVE_MIN_DURATION,
    LAUNCH_WINDOW_OBJECTIVE_TRADE_OFF,
    LAUNCH_WINDOW_RESOLUTION_DETAILED,
    LAUNCH_WINDOW_RESOLUTION_FAST,
    LaunchWindowCandidate,
    LaunchWindowSearchError,
    LaunchWindowSearchRequest,
    LaunchWindowSearchResult,
)
from mission.launch_search import search_direct_earth_saturn_titan
from mission.launch_search_models import (
    LaunchScenario,
    LaunchSearchConfig,
    LaunchSearchResult,
    SearchObjective,
)

ENGINE_NAME = "mission.launch_search direct Earth-Saturn-Titan v1"
MJD2000_EPOCH = datetime(2000, 1, 1, tzinfo=timezone.utc)

OBJECTIVE_MAP = {
    LAUNCH_WINDOW_OBJECTIVE_MIN_DELTA_V: SearchObjective.MINIMUM_TOTAL_DELTA_V,
    LAUNCH_WINDOW_OBJECTIVE_MIN_DURATION: SearchObjective.MINIMUM_DURATION,
    LAUNCH_WINDOW_OBJECTIVE_MIN_C3: SearchObjective.MINIMUM_C3,
    LAUNCH_WINDOW_OBJECTIVE_TRADE_OFF: SearchObjective.BALANCED_DELTA_V_DURATION,
}

RESOLUTION_CONFIG = {
    LAUNCH_WINDOW_RESOLUTION_FAST: {
        "departure_step_days": 60.0,
        "arrival_step_days": 60.0,
        "refinement_count": 0,
        "fast_mode": True,
    },
    LAUNCH_WINDOW_RESOLUTION_DETAILED: {
        "departure_step_days": 15.0,
        "arrival_step_days": 30.0,
        "refinement_count": 3,
        "fast_mode": False,
    },
}

_DEPARTURE_LABEL = "Earth departure injection"
_CAPTURE_LABEL = "Saturn capture to 150,000 × 1,221,870 km ellipse"
_CIRCULARISATION_LABEL = "Saturn circularization at Titan orbital radius"


def request_to_engine_config(request: LaunchWindowSearchRequest) -> LaunchSearchConfig:
    """Convert UI dates, names, and resolution preset to the engine contract."""
    if not isinstance(request, LaunchWindowSearchRequest):
        raise TypeError("request must be a LaunchWindowSearchRequest.")
    resolution = RESOLUTION_CONFIG[request.resolution]
    return LaunchSearchConfig(
        launch_start=request.search_window_start,
        launch_end=request.search_window_end,
        min_time_of_flight_days=request.min_time_of_flight_days,
        max_time_of_flight_days=request.max_time_of_flight_days,
        objective=OBJECTIVE_MAP[request.objective],
        keep_count=request.max_results,
        **resolution,
    )


def _mjd2000_to_datetime(epoch_mjd2000: float) -> datetime:
    return MJD2000_EPOCH + timedelta(days=epoch_mjd2000)


def scenario_to_candidate(scenario: LaunchScenario, rank: int) -> LaunchWindowCandidate:
    """Map engine output without recomputing any physical quantity."""
    manoeuvres = dict(scenario.delta_v_by_manoeuvre_m_s)
    try:
        departure_delta_v = manoeuvres[_DEPARTURE_LABEL]
        capture_delta_v = manoeuvres[_CAPTURE_LABEL]
        circularisation_delta_v = manoeuvres[_CIRCULARISATION_LABEL]
    except KeyError as exc:
        raise LaunchWindowSearchError(
            f"Scientific result is missing manoeuvre {exc.args[0]!r}."
        ) from exc
    return LaunchWindowCandidate(
        rank=rank,
        departure_datetime=_mjd2000_to_datetime(scenario.launch_mjd2000),
        saturn_arrival_datetime=_mjd2000_to_datetime(scenario.saturn_arrival_mjd2000),
        scenario_end_datetime=_mjd2000_to_datetime(scenario.reference_phase_end_mjd2000),
        time_of_flight_days=scenario.interplanetary_duration_days,
        c3_km2_s2=scenario.c3_m2_s2 / 1_000_000.0,
        v_infinity_earth_m_s=scenario.earth_v_infinity_m_s,
        v_infinity_saturn_m_s=scenario.saturn_v_infinity_m_s,
        delta_v_departure_m_s=departure_delta_v,
        delta_v_capture_m_s=capture_delta_v,
        delta_v_titan_circularization_m_s=circularisation_delta_v,
        delta_v_total_m_s=scenario.total_delta_v_m_s,
        scenario_id=scenario.scenario_id,
        notes=(*scenario.assumptions, *scenario.rejection_reasons),
        segments=scenario.segments,
    )


def engine_result_to_ui_result(
    request: LaunchWindowSearchRequest,
    engine_result: LaunchSearchResult,
) -> LaunchWindowSearchResult:
    candidates = tuple(
        scenario_to_candidate(scenario, rank)
        for rank, scenario in enumerate(engine_result.solutions, start=1)
    )
    rank_by_scenario_id = {
        candidate.scenario_id: candidate.rank for candidate in candidates
    }
    pareto_ranks = tuple(
        sorted(
            rank_by_scenario_id[scenario.scenario_id]
            for scenario in engine_result.pareto_front
            if scenario.scenario_id in rank_by_scenario_id
        )
    )
    resolution = RESOLUTION_CONFIG[request.resolution]
    candidate_assumptions = tuple(
        dict.fromkeys(note for scenario in engine_result.solutions for note in scenario.assumptions)
    )
    assumptions = (
        f"Resolution {request.resolution}: departure step "
        f"{resolution['departure_step_days']:.0f} days; flight-time step "
        f"{resolution['arrival_step_days']:.0f} days; refinement seeds "
        f"{resolution['refinement_count']}.",
        *candidate_assumptions,
        "C3 converted from m²/s² to km²/s² for display; delta-v remains in m/s.",
        "Heliocentric/AU and Saturn-centred/km segments remain separate scenes.",
    )
    return LaunchWindowSearchResult(
        request=request,
        candidates=candidates,
        engine_name=ENGINE_NAME,
        assumptions=assumptions,
        pareto_candidate_ranks=pareto_ranks,
    )


class MissionLaunchWindowSearchAdapter:
    """Concrete UI service delegating every scientific operation to the engine."""

    def __init__(
        self,
        engine_search: Callable[[LaunchSearchConfig], LaunchSearchResult] = (
            search_direct_earth_saturn_titan
        ),
    ) -> None:
        self._engine_search = engine_search

    def search(self, request: LaunchWindowSearchRequest) -> LaunchWindowSearchResult:
        config = request_to_engine_config(request)
        try:
            engine_result = self._engine_search(config)
        except RuntimeError as exc:
            if "No feasible direct" in str(exc):
                return LaunchWindowSearchResult(
                    request=request,
                    candidates=(),
                    engine_name=ENGINE_NAME,
                    assumptions=(str(exc),),
                    pareto_candidate_ranks=(),
                )
            raise LaunchWindowSearchError(str(exc)) from exc
        return engine_result_to_ui_result(request, engine_result)
