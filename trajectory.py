# REPRISE :
# Prochaine etape : elargir la plage de temps de vol testee
# pour Terre-Saturne a 4-8 ans, puis revalider contre
# v_inf depart ~10.3 km/s theorique.

import math
from datetime import date, datetime

import pykep as pk

from mission import physics
from mission.bodies import resolve_body
from mission.capabilities import PLANET_DESTINATIONS
from mission.models import Event, Leg, TrajectoryResult
from mission.pykep_trajectory_engine import PyKEPTrajectoryEngine


def norm(v):
    """Norme d'un vecteur 3D."""
    return math.sqrt(sum(x * x for x in v))


def sub(a, b):
    """Soustraction de deux vecteurs 3D."""
    return [a[i] - b[i] for i in range(3)]


def to_pk_epoch(value):
    """Convertit une date Python en epoch PyKEP."""
    if isinstance(value, datetime):
        return pk.epoch(value.strftime("%Y-%m-%d %H:%M:%S"))

    if isinstance(value, date):
        return pk.epoch(value.strftime("%Y-%m-%d 00:00:00"))

    if isinstance(value, pk.epoch):
        return value

    raise TypeError(f"Date non supportee: {type(value)}. Un datetime/date Python est attendu.")


def _legacy_solution_dict(result: TrajectoryResult) -> dict:
    """Convert the canonical internal TrajectoryResult into the legacy dict shape."""
    return {
        "dv_depart": result.v_inf_depart,
        "v_infinity_saturn": result.v_inf_arrival,
        "departure_mjd2000": result.departure_mjd2000,
        "arrival_mjd2000": result.arrival_mjd2000,
        "tof_years": result.tof_years,
    }


def _legacy_solution_list(results: list[TrajectoryResult]) -> list[dict]:
    """Compatibility boundary: convert internal TrajectoryResult objects to legacy dicts."""
    return [_legacy_solution_dict(result) for result in results]


def _legacy_dict_to_trajectory_result(solution: dict) -> TrajectoryResult:
    """Compatibility boundary: convert a legacy dict back to the canonical internal result type."""
    return TrajectoryResult(
        departure_mjd2000=solution.get("departure_mjd2000"),
        arrival_mjd2000=solution.get("arrival_mjd2000"),
        tof_years=solution.get("tof_years"),
        v_inf_depart=solution.get("dv_depart"),
        v_inf_arrival=solution.get("v_infinity_saturn"),
        delta_v=None,
        method="lambert",
        notes="Legacy compatibility conversion.",
        departure_position_m=solution.get("departure_position_m"),
        arrival_position_m=solution.get("arrival_position_m"),
        transfer_departure_velocity_m_s=solution.get("transfer_departure_velocity_m_s"),
        central_mu_m3_s2=solution.get("central_mu_m3_s2"),
    )


def _result_value(solution, key_name: str):
    """Read either a legacy dict or a TrajectoryResult using the relevant field name."""
    if isinstance(solution, dict):
        if key_name == "dv_depart":
            return solution.get("dv_depart")
        if key_name == "v_infinity_saturn":
            return solution.get("v_infinity_saturn")
        return solution.get(key_name)

    if hasattr(solution, key_name):
        return getattr(solution, key_name)

    if key_name == "dv_depart":
        return getattr(solution, "v_inf_depart", None)
    if key_name == "v_infinity_saturn":
        return getattr(solution, "v_inf_arrival", None)

    raise ValueError(f"key_name '{key_name}' not found on solution")


def _compute_lambert_grid(
    origin,
    destination,
    launch_start,
    launch_end,
    n_departures=12,
    tof_min_years=4.0,
    tof_max_years=8.0,
    tof_step_days=15.0,
) -> list[dict]:
    """
    Compute all feasible origin→destination Lambert trajectories over a grid.

    Internally the solver uses the canonical TrajectoryResult representation; at
    this compatibility boundary we convert back to the legacy dict shape expected
    by the current callers/tests. Body-agnostic: origin/destination are resolved
    generically by mission.bodies.resolve_body via PyKEPTrajectoryEngine.
    """
    engine = PyKEPTrajectoryEngine()
    results = engine.compute_trajectory(
        origin,
        destination,
        launch_start,
        launch_end,
        n_departures=n_departures,
        tof_min_years=tof_min_years,
        tof_max_years=tof_max_years,
        tof_step_days=tof_step_days,
    )

    if not results:
        raise RuntimeError(f"No {origin}-to-{destination} Lambert solution was found.")

    return _legacy_solution_list(results)


def _compute_lambert_earth_saturn_grid(
    launch_start,
    launch_end,
    n_departures=12,
    tof_min_years=4.0,
    tof_max_years=8.0,
    tof_step_days=15.0,
) -> list[dict]:
    """Earth→Saturn specialisation of _compute_lambert_grid.

    Kept with its original name/signature for backward compatibility: several
    existing regression tests (test_trajectory_saturn.py, test_solver_equivalence.py,
    test_celestial_body_resolution.py, test_leg_solver.py) import and call this
    function directly by name.
    """
    return _compute_lambert_grid(
        "Earth",
        "Saturn",
        launch_start,
        launch_end,
        n_departures=n_departures,
        tof_min_years=tof_min_years,
        tof_max_years=tof_max_years,
        tof_step_days=tof_step_days,
    )


def select_best_by_criterion(solutions, key_name):
    """
    Select solution with minimum value for given criterion.

    Internal canonical representation is TrajectoryResult, but legacy dict-based
    inputs remain supported at the selection boundary for compatibility.
    """
    if not solutions:
        raise ValueError("solutions list cannot be empty")

    if isinstance(solutions[0], dict):
        if key_name not in solutions[0]:
            raise ValueError(f"key_name '{key_name}' not found in solution dict")
    elif not hasattr(solutions[0], key_name):
        if key_name == "dv_depart":
            if not hasattr(solutions[0], "v_inf_depart"):
                raise ValueError(f"key_name '{key_name}' not found in solution")
        elif key_name == "v_infinity_saturn":
            if not hasattr(solutions[0], "v_inf_arrival"):
                raise ValueError(f"key_name '{key_name}' not found in solution")
        else:
            raise ValueError(f"key_name '{key_name}' not found in solution")

    # Make equal-primary-value selection independent of grid/list ordering.
    # The orbital criterion remains unchanged; the remaining fields only provide
    # a stable lexicographic tie-break for otherwise equivalent candidates.
    tie_break_fields = (
        "departure_mjd2000",
        "tof_years",
        "arrival_mjd2000",
        "dv_depart",
        "v_infinity_saturn",
    )

    def deterministic_key(solution):
        values = [_result_value(solution, key_name)]
        values.extend(_result_value(solution, field) for field in tie_break_fields)
        return tuple(math.inf if value is None else float(value) for value in values)

    return min(solutions, key=deterministic_key)


def select_best_by_departure_v_infinity(solutions):
    """Select solution with lowest departure v-infinity."""
    return select_best_by_criterion(solutions, "dv_depart")


def select_best_by_arrival_v_infinity(solutions):
    """Select solution with lowest arrival v-infinity at Saturn."""
    return select_best_by_criterion(solutions, "v_infinity_saturn")


def select_best_by_shortest_mission_duration(solutions):
    """Select solution with shortest time-of-flight."""
    return select_best_by_criterion(solutions, "tof_years")


def select_pareto_frontier(solutions, objectives=None):
    """
    Filter to Pareto-optimal solutions (non-dominated).

    Internal canonical representation is TrajectoryResult, but legacy dicts remain
    accepted for compatibility.
    """
    if not solutions:
        return []

    if objectives is None:
        objectives = ["dv_depart", "v_infinity_saturn"]

    canonical_objectives = []
    for objective in objectives:
        if objective == "dv_depart":
            canonical_objectives.append("v_inf_depart")
        elif objective == "v_infinity_saturn":
            canonical_objectives.append("v_inf_arrival")
        else:
            canonical_objectives.append(objective)

    for objective in objectives:
        if isinstance(solutions[0], dict):
            if objective not in solutions[0]:
                raise ValueError(f"objective '{objective}' not found in solution dict")
        else:
            if objective == "dv_depart" and not hasattr(solutions[0], "v_inf_depart"):
                raise ValueError(f"objective '{objective}' not found in solution")
            if objective == "v_infinity_saturn" and not hasattr(solutions[0], "v_inf_arrival"):
                raise ValueError(f"objective '{objective}' not found in solution")
            if objective == "tof_years" and not hasattr(solutions[0], "tof_years"):
                raise ValueError(f"objective '{objective}' not found in solution")

    pareto = []

    for candidate in solutions:
        is_dominated = False

        for other in solutions:
            if candidate is other:
                continue

            candidate_worse_or_equal = all(
                _result_value(other, objective) <= _result_value(candidate, objective)
                for objective in objectives
            )
            other_strictly_better = any(
                _result_value(other, objective) < _result_value(candidate, objective)
                for objective in objectives
            )

            if candidate_worse_or_equal and other_strictly_better:
                is_dominated = True
                break

        if not is_dominated:
            pareto.append(candidate)

    return pareto


def compute_trajectory(
    destination: str,
    departure_type: str,
    launch_start,
    launch_end,
    has_moon_transfer: bool,
    has_landing: bool,
    is_flyby_only: bool,
    dv_per_flyby: float,
    leo_altitude_km: float,
    capture_altitude_km: float,
) -> dict:
    # Direct planetary arrival: any Lambert-capable planet in
    # mission.capabilities.PLANET_DESTINATIONS. Moon-only names (e.g. Titan) are
    # not offered here - they are reached through the connected staging-and-
    # transfer chain in mission/full_mission.py, not this direct Lambert engine.
    supported_destinations = {name.lower() for name in PLANET_DESTINATIONS}
    if destination.lower() not in supported_destinations:
        dv_budget = {
            "dV from LEO": 0.0,
            "dV DSM/Fly-By": 0.0,
            "dV Capture at Destination": 0.0,
            "dV Transfer to Moon": 0.0,
            "dV Capture at Moon": 0.0,
            "dV Lower to Final Orbit": 0.0,
            "dV Break for landing": 0.0,
            "dV Soft Landing": 0.0,
        }

        return {
            "dv_budget": dv_budget,
            "dv_total": 0.0,
            "best_launch_date": None,
            "arrival_date": None,
            "note": (
                f"Destination '{destination}' is not implemented yet. "
                f"Supported destinations: {', '.join(PLANET_DESTINATIONS)}."
            ),
        }

    # Compute all Lambert solutions over grid
    solutions = PyKEPTrajectoryEngine().compute_trajectory(
        "Earth",
        destination,
        launch_start,
        launch_end,
    )

    # Select best solution (minimum departure v-infinity)
    best = select_best_by_departure_v_infinity(solutions)
    best_departure_v_inf = _result_value(best, "dv_depart")
    best_arrival_v_inf = _result_value(best, "v_infinity_saturn")
    best_departure_mjd2000 = _result_value(best, "departure_mjd2000")
    best_arrival_mjd2000 = _result_value(best, "arrival_mjd2000")

    # Compute propulsive ΔV where applicable (LEO injection and destination capture).
    # Use body-provided radii and mu values; altitudes are provided by the UI
    # in kilometres and must be converted to metres.
    earth = resolve_body("Earth")
    destination_body = resolve_body(destination)
    assert earth.pykep_body is not None
    # Guaranteed: destination is in PLANET_DESTINATIONS, i.e. supports_lambert,
    # which mission/bodies.py only sets for jpl_lp-backed (pykep_body-having) planets.
    assert destination_body.pykep_body is not None

    # Convert altitudes from km to m
    r_leo = earth.pykep_body.get_radius() + float(leo_altitude_km) * 1000.0
    r_capture = destination_body.pykep_body.get_radius() + float(capture_altitude_km) * 1000.0

    mu_earth = earth.get_mu_self()
    mu_destination = destination_body.get_mu_self()

    # For LEO departures compute actual injection ΔV; for Direct keep legacy v_inf value
    if str(departure_type).lower() == "leo":
        dv_from_leo = physics.delta_v_injection(best_departure_v_inf, mu_earth, r_leo)
    else:
        dv_from_leo = best_departure_v_inf

    # Always compute capture ΔV at the destination planet
    dv_capture_dest = physics.delta_v_capture(best_arrival_v_inf, mu_destination, r_capture)

    dv_budget = {
        "dV from LEO": dv_from_leo,
        "dV DSM/Fly-By": 0.0,
        "dV Capture at Destination": dv_capture_dest,
        "dV Transfer to Moon": 0.0,
        "dV Capture at Moon": 0.0,
        "dV Lower to Final Orbit": 0.0,
        "dV Break for landing": 0.0,
        "dV Soft Landing": 0.0,
    }

    dv_total = sum(dv_budget.values())

    best_launch_date = pk.epoch(best_departure_mjd2000)

    arrival_date = pk.epoch(best_arrival_mjd2000)

    note = (
        f"Preliminary Earth-to-{destination_body.name} Lambert model (multi_revs=0). "
        "The following budget values are propulsive delta-v terms:\n"
        "- 'dV from LEO': impulsive LEO escape delta-v when LEO is selected.\n"
        f"- 'dV Capture at Destination': impulsive {destination_body.name} capture delta-v, "
        f"computed with {destination_body.name}'s own gravitational parameter (preliminary).\n"
        "Other entries remain preliminary or unimplemented."
    )

    earth_leg_trajectory = TrajectoryResult(
        departure_mjd2000=best_departure_mjd2000,
        arrival_mjd2000=best_arrival_mjd2000,
        tof_years=_result_value(best, "tof_years"),
        v_inf_depart=best_departure_v_inf,
        v_inf_arrival=best_arrival_v_inf,
        delta_v=dv_from_leo,
        method="lambert",
        notes=(
            f"Earth-to-{destination_body.name} Lambert leg; delta_v contains Earth departure only."
        ),
        departure_position_m=_result_value(best, "departure_position_m"),
        arrival_position_m=_result_value(best, "arrival_position_m"),
        transfer_departure_velocity_m_s=_result_value(best, "transfer_departure_velocity_m_s"),
        central_mu_m3_s2=_result_value(best, "central_mu_m3_s2"),
    )
    earth_departure_event = Event(
        name="Earth departure",
        body="Earth",
        event_type="departure",
        epoch=best_departure_mjd2000,
    )
    destination_arrival_event = Event(
        name=f"{destination_body.name} arrival",
        body=destination_body.name,
        event_type="arrival",
        epoch=best_arrival_mjd2000,
    )
    earth_leg = Leg(
        origin="Earth",
        destination=destination_body.name,
        trajectory=earth_leg_trajectory,
        events=[earth_departure_event, destination_arrival_event],
        notes=f"Canonical Earth-to-{destination_body.name} leg for the connected mission chain.",
    )

    return {
        "dv_budget": dv_budget,
        "dv_total": dv_total,
        "best_launch_date": best_launch_date,
        "arrival_date": arrival_date,
        # Key name kept as "earth_saturn_leg" for every destination (not just
        # Saturn) for backward compatibility: it is pinned as an exact top-level
        # key set by tests/test_trajectory_saturn.py's EXPECTED_TOP_LEVEL_KEYS,
        # and app.py/other tests already read this literal key. It now holds the
        # generic Earth-to-destination leg, regardless of which planet.
        "earth_saturn_leg": earth_leg,
        "note": note,
    }


def compute_trajectory_alternatives(
    destination: str,
    departure_type: str,
    launch_start,
    launch_end,
    has_moon_transfer: bool,
    has_landing: bool,
    is_flyby_only: bool,
    dv_per_flyby: float,
) -> dict:
    """
    Compute multiple trajectory alternatives based on different selection criteria.

    Uses the same Lambert grid as compute_trajectory(), but exposes all selection strategies
    to allow mission designers to compare trade-offs.

    Args:
        destination: target body (currently "Saturn" only)
        departure_type: "Direct" or "LEO"
        launch_start: Python date/datetime (launch window start)
        launch_end: Python date/datetime (launch window end)
        has_moon_transfer: bool (for future Titan transfer)
        has_landing: bool (for future landing logic)
        is_flyby_only: bool (for future flyby-only missions)
        dv_per_flyby: float (for future gravity assists)

    Returns:
        dict containing:
        {
            "all_solutions": list of all solution dicts from grid,
            "solution_count": int, total number of grid solutions,
            "best_by_departure_v_inf": dict, solution minimizing departure v-infinity,
            "best_by_arrival_v_inf": dict, solution minimizing arrival v-infinity,
            "best_by_shortest_tof": dict, solution minimizing time-of-flight,
            "pareto_frontier": list of non-dominated solutions,
            "pareto_count": int, number of Pareto-optimal solutions,
            "note": str, description of results,
        }

    Note:
        - Only Saturn is currently implemented (other destinations return empty results)
        - No duplicate Lambert calculations; one grid computation feeds all selectors
        - Pareto frontier uses ["dv_depart", "v_infinity_saturn"] as default objectives

    Raises:
        ValueError: if launch_end < launch_start
        RuntimeError: if no valid Lambert solutions are found (not expected for
            Saturn in normal launch windows)
    """
    # Unsupported-destination guard, same PLANET_DESTINATIONS set as compute_trajectory().
    supported_destinations = {name.lower() for name in PLANET_DESTINATIONS}
    if destination.lower() not in supported_destinations:
        return {
            "all_solutions": [],
            "solution_count": 0,
            "best_by_departure_v_inf": None,
            "best_by_arrival_v_inf": None,
            "best_by_shortest_tof": None,
            "pareto_frontier": [],
            "pareto_count": 0,
            "note": (
                f"Destination '{destination}' is not implemented yet. "
                f"Supported destinations: {', '.join(PLANET_DESTINATIONS)}."
            ),
        }

    # Compute all Lambert solutions once. Internally we convert to the canonical
    # TrajectoryResult representation so the selection logic works on consistent objects.
    all_legacy_solutions = _compute_lambert_grid(
        "Earth",
        destination,
        launch_start,
        launch_end,
    )
    all_results = [_legacy_dict_to_trajectory_result(solution) for solution in all_legacy_solutions]

    best_by_dep = select_best_by_departure_v_infinity(all_results)
    best_by_arr = select_best_by_arrival_v_infinity(all_results)
    best_by_tof = select_best_by_shortest_mission_duration(all_results)
    pareto = select_pareto_frontier(all_results, objectives=["dv_depart", "v_infinity_saturn"])

    note = (
        "Multiple Earth→Saturn Lambert trajectory alternatives. "
        "Best solutions ranked by different criteria. "
        "Pareto frontier shows non-dominated trade-offs between "
        "departure v-infinity and arrival v-infinity."
    )

    return {
        "all_solutions": _legacy_solution_list(all_results),
        "solution_count": len(all_results),
        "best_by_departure_v_inf": _legacy_solution_dict(best_by_dep)
        if best_by_dep is not None
        else None,
        "best_by_arrival_v_inf": _legacy_solution_dict(best_by_arr)
        if best_by_arr is not None
        else None,
        "best_by_shortest_tof": _legacy_solution_dict(best_by_tof)
        if best_by_tof is not None
        else None,
        "pareto_frontier": _legacy_solution_list(pareto),
        "pareto_count": len(pareto),
        "note": note,
    }
