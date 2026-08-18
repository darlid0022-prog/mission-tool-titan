"""Deterministic coarse-to-local search for direct Earth-Saturn trajectories."""

from __future__ import annotations

import hashlib
import math
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pykep as pk

from .bodies import resolve_body
from .connected_physics import SECONDS_PER_DAY, compute_connected_first_order_chain
from .constants import NOMINAL_SATURN_PERIAPSIS_RADIUS_M, TITAN_MEAN_ORBIT_RADIUS_M
from .launch_search_ephemeris import heliocentric_state, solve_earth_saturn_lambert
from .launch_search_models import (
    LaunchScenario,
    LaunchSearchConfig,
    LaunchSearchResult,
    SearchObjective,
    SearchTrajectorySegment,
)
from .physics import delta_v_injection

EARTH_PARKING_ALTITUDE_M = 250_000.0
COARSE_ARC_SAMPLE_COUNT = 48
FAST_ARC_SAMPLE_COUNT = 16
REFINEMENT_DIVISOR = 4.0


def _date_to_mjd2000(value) -> float:
    return float(pk.epoch(value.strftime("%Y-%m-%d 00:00:00")).mjd2000)


def _iso_date(epoch_mjd2000: float) -> str:
    instant = datetime(2000, 1, 1, tzinfo=timezone.utc) + timedelta(days=epoch_mjd2000)
    return instant.date().isoformat()


def _grid(start: float, stop: float, step: float) -> tuple[float, ...]:
    count = math.floor((stop - start) / step + 1e-12)
    values = [start + index * step for index in range(count + 1)]
    if not math.isclose(values[-1], stop, abs_tol=1e-9):
        values.append(stop)
    return tuple(values)


def _scenario_id(departure: float, arrival: float) -> str:
    payload = f"earth-saturn-titan:{departure:.9f}:{arrival:.9f}".encode()
    return f"est-{hashlib.sha256(payload).hexdigest()[:16]}"


def _capture_segment(
    departure_mjd2000: float,
    arrival_mjd2000: float,
    periapsis_radius_m: float,
    apoapsis_radius_m: float,
    sample_count: int,
) -> SearchTrajectorySegment:
    axis = (periapsis_radius_m + apoapsis_radius_m) / 2.0
    eccentricity = (apoapsis_radius_m - periapsis_radius_m) / (
        apoapsis_radius_m + periapsis_radius_m
    )
    points = []
    for index in range(sample_count):
        anomaly = math.pi * index / (sample_count - 1)
        points.append(
            (
                axis * (math.cos(anomaly) - eccentricity) / 1_000.0,
                axis * math.sqrt(1.0 - eccentricity**2) * math.sin(anomaly) / 1_000.0,
                0.0,
            )
        )
    return SearchTrajectorySegment(
        id="saturn-capture-ellipse",
        name="Saturn capture ellipse to Titan orbital radius",
        frame="saturn_centred",
        unit="km",
        x=tuple(point[0] for point in points),
        y=tuple(point[1] for point in points),
        z=tuple(point[2] for point in points),
        departure_mjd2000=departure_mjd2000,
        arrival_mjd2000=arrival_mjd2000,
    )


def evaluate_launch_scenario(
    departure_mjd2000: float,
    arrival_mjd2000: float,
    *,
    sample_count: int = COARSE_ARC_SAMPLE_COUNT,
) -> LaunchScenario:
    """Evaluate one feasible direct scenario or raise with an explicit reason."""
    transfer = solve_earth_saturn_lambert(
        departure_mjd2000,
        arrival_mjd2000,
        sample_count,
    )
    connected = compute_connected_first_order_chain(
        arrival_v_infinity_m_s=transfer.saturn_v_infinity_m_s,
        periapsis_radius_m=NOMINAL_SATURN_PERIAPSIS_RADIUS_M,
        apoapsis_radius_m=TITAN_MEAN_ORBIT_RADIUS_M,
    )
    capture = connected.saturn_capture
    earth = resolve_body("Earth")
    parking_radius = float(earth.pykep_body.get_radius()) + EARTH_PARKING_ALTITUDE_M
    departure_delta_v = delta_v_injection(
        transfer.earth_v_infinity_m_s,
        earth.get_mu_self(),
        parking_radius,
    )
    manoeuvres = (
        ("Earth departure injection", departure_delta_v),
        ("Saturn capture to 150,000 × 1,221,870 km ellipse", capture.capture_delta_v_m_s),
        (
            "Saturn circularization at Titan orbital radius",
            capture.circularisation_delta_v_m_s,
        ),
    )
    phase_end = arrival_mjd2000 + capture.time_of_flight_days
    lambert_points = transfer.sample_positions_au
    segments = (
        SearchTrajectorySegment(
            id="earth-saturn-lambert",
            name="Direct Earth → Saturn Lambert transfer",
            frame="heliocentric",
            unit="AU",
            x=tuple(point[0] for point in lambert_points),
            y=tuple(point[1] for point in lambert_points),
            z=tuple(point[2] for point in lambert_points),
            departure_mjd2000=departure_mjd2000,
            arrival_mjd2000=arrival_mjd2000,
        ),
        _capture_segment(
            arrival_mjd2000,
            phase_end,
            capture.periapsis_radius_m,
            capture.apoapsis_radius_m,
            sample_count,
        ),
    )
    total_delta_v = sum(value for _, value in manoeuvres)
    return LaunchScenario(
        scenario_id=_scenario_id(departure_mjd2000, arrival_mjd2000),
        launch_date=_iso_date(departure_mjd2000),
        saturn_arrival_date=_iso_date(arrival_mjd2000),
        reference_phase_end_date=_iso_date(phase_end),
        launch_mjd2000=departure_mjd2000,
        saturn_arrival_mjd2000=arrival_mjd2000,
        reference_phase_end_mjd2000=phase_end,
        interplanetary_duration_days=transfer.time_of_flight_s / SECONDS_PER_DAY,
        total_duration_days=phase_end - departure_mjd2000,
        c3_m2_s2=transfer.earth_v_infinity_m_s**2,
        earth_v_infinity_m_s=transfer.earth_v_infinity_m_s,
        saturn_v_infinity_m_s=transfer.saturn_v_infinity_m_s,
        delta_v_by_manoeuvre_m_s=manoeuvres,
        total_delta_v_m_s=total_delta_v,
        objective_score=0.0,
        feasible=True,
        rejection_reasons=(),
        assumptions=(
            "PyKEP jpl_lp heliocentric ephemerides and zero-revolution Lambert arc.",
            "250 km circular Earth parking orbit and impulsive injection.",
            "Coplanar two-body impulsive Saturn capture at 150,000 km centre radius.",
            "Endpoint is Saturn-centred circular orbit at Titan's 1,221,870 km mean radius.",
            "No Titan phasing, Titan encounter, Titan capture, flyby gain, or gravity assist.",
        ),
        segments=segments,
    )


def rank_scenarios(
    scenarios: tuple[LaunchScenario, ...],
    objective: SearchObjective,
) -> tuple[LaunchScenario, ...]:
    if not scenarios:
        return ()
    if objective is SearchObjective.MINIMUM_TOTAL_DELTA_V:
        scores = [scenario.total_delta_v_m_s for scenario in scenarios]
    elif objective is SearchObjective.MINIMUM_DURATION:
        scores = [scenario.total_duration_days for scenario in scenarios]
    elif objective is SearchObjective.MINIMUM_C3:
        scores = [scenario.c3_m2_s2 for scenario in scenarios]
    else:
        delta_values = [scenario.total_delta_v_m_s for scenario in scenarios]
        duration_values = [scenario.total_duration_days for scenario in scenarios]
        delta_span = max(delta_values) - min(delta_values)
        duration_span = max(duration_values) - min(duration_values)
        scores = [
            (scenario.total_delta_v_m_s - min(delta_values)) / (delta_span or 1.0)
            + (scenario.total_duration_days - min(duration_values)) / (duration_span or 1.0)
            for scenario in scenarios
        ]
    scored = tuple(replace(scenario, objective_score=score) for scenario, score in zip(scenarios, scores))
    return tuple(
        sorted(
            scored,
            key=lambda scenario: (
                scenario.objective_score,
                scenario.total_delta_v_m_s,
                scenario.total_duration_days,
                scenario.launch_mjd2000,
                scenario.saturn_arrival_mjd2000,
            ),
        )
    )


def compute_pareto_front(scenarios: tuple[LaunchScenario, ...]) -> tuple[LaunchScenario, ...]:
    """Return scenarios non-dominated in connected delta-v and total duration."""
    front = []
    for candidate in scenarios:
        dominated = any(
            other is not candidate
            and other.total_delta_v_m_s <= candidate.total_delta_v_m_s
            and other.total_duration_days <= candidate.total_duration_days
            and (
                other.total_delta_v_m_s < candidate.total_delta_v_m_s
                or other.total_duration_days < candidate.total_duration_days
            )
            for other in scenarios
        )
        if not dominated:
            front.append(candidate)
    return tuple(sorted(front, key=lambda item: (item.total_duration_days, item.total_delta_v_m_s)))


def _evaluate_pairs(
    pairs: tuple[tuple[float, float], ...],
    sample_count: int,
) -> tuple[tuple[LaunchScenario, ...], tuple[tuple[float, float, str], ...]]:
    scenarios = []
    rejected = []
    for departure, arrival in pairs:
        try:
            scenarios.append(evaluate_launch_scenario(departure, arrival, sample_count=sample_count))
        except (RuntimeError, TypeError, ValueError) as exc:
            rejected.append((departure, arrival, str(exc)))
    return tuple(scenarios), tuple(rejected)


def search_direct_earth_saturn_titan(config: LaunchSearchConfig) -> LaunchSearchResult:
    """Run configurable coarse search followed by deterministic local refinement."""
    if not isinstance(config, LaunchSearchConfig):
        raise TypeError("config must be a LaunchSearchConfig.")
    departure_start = _date_to_mjd2000(config.launch_start)
    departure_end = _date_to_mjd2000(config.launch_end)
    departures = _grid(departure_start, departure_end, config.departure_step_days)
    flight_times = _grid(
        config.min_time_of_flight_days,
        config.max_time_of_flight_days,
        config.arrival_step_days,
    )
    coarse_pairs = tuple((departure, departure + flight_time) for departure in departures for flight_time in flight_times)
    sample_count = FAST_ARC_SAMPLE_COUNT if config.fast_mode else COARSE_ARC_SAMPLE_COUNT
    coarse, rejected = _evaluate_pairs(coarse_pairs, sample_count)
    if not coarse:
        raise RuntimeError("No feasible direct Earth-to-Saturn Lambert solution was found.")

    ranked_coarse = rank_scenarios(coarse, config.objective)
    seeds = ranked_coarse[: min(config.refinement_count, len(ranked_coarse))]
    refined_pairs = set()
    if not config.fast_mode:
        departure_delta = config.departure_step_days / REFINEMENT_DIVISOR
        arrival_delta = config.arrival_step_days / REFINEMENT_DIVISOR
        for seed in seeds:
            for departure_offset in (-departure_delta, 0.0, departure_delta):
                for arrival_offset in (-arrival_delta, 0.0, arrival_delta):
                    departure = seed.launch_mjd2000 + departure_offset
                    arrival = seed.saturn_arrival_mjd2000 + arrival_offset
                    tof = arrival - departure
                    if (
                        departure_start <= departure <= departure_end
                        and config.min_time_of_flight_days <= tof <= config.max_time_of_flight_days
                    ):
                        refined_pairs.add((departure, arrival))
    refined_pairs.difference_update(coarse_pairs)
    refined, refined_rejected = _evaluate_pairs(tuple(sorted(refined_pairs)), sample_count)
    all_scenarios_by_id = {item.scenario_id: item for item in (*coarse, *refined)}
    ranked = rank_scenarios(tuple(all_scenarios_by_id.values()), config.objective)
    retained = ranked[: config.keep_count]
    evaluated_pairs = (*coarse_pairs, *tuple(sorted(refined_pairs)))
    unique_ephemeris_requests = {
        *(("Earth", departure) for departure, _ in evaluated_pairs),
        *(("Saturn", arrival) for _, arrival in evaluated_pairs),
    }
    return LaunchSearchResult(
        config=config,
        solutions=retained,
        pareto_front=compute_pareto_front(tuple(all_scenarios_by_id.values())),
        rejected_pairs=(*rejected, *refined_rejected),
        evaluated_pair_count=len(coarse_pairs) + len(refined_pairs),
        ephemeris_evaluation_count=len(unique_ephemeris_requests),
    )
