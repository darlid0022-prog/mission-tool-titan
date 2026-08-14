# REPRISE :
# Prochaine etape : elargir la plage de temps de vol testee
# pour Terre-Saturne a 4-8 ans, puis revalider contre
# v_inf depart ~10.3 km/s theorique.

import math
from datetime import date, datetime

import pykep as pk

from mission.leg_solver import compute_lambert_leg


def norm(v):
    """Norme d'un vecteur 3D."""
    return math.sqrt(sum(x * x for x in v))


def sub(a, b):
    """Soustraction de deux vecteurs 3D."""
    return [a[i] - b[i] for i in range(3)]


def to_pk_epoch(value):
    """Convertit une date Python en epoch PyKEP."""
    if isinstance(value, datetime):
        return pk.epoch(
            value.strftime("%Y-%m-%d %H:%M:%S")
        )

    if isinstance(value, date):
        return pk.epoch(
            value.strftime("%Y-%m-%d 00:00:00")
        )

    if isinstance(value, pk.epoch):
        return value

    raise TypeError(
        f"Date non supportee: {type(value)}. "
        "Un datetime/date Python est attendu."
    )


def _compute_lambert_earth_saturn_grid(
    launch_start,
    launch_end,
    n_departures=12,
    tof_min_years=4.0,
    tof_max_years=8.0,
    tof_step_days=15.0,
) -> list:
    """
    Compute all feasible Earth→Saturn Lambert trajectories over a grid.

    This is a compatibility wrapper around the generic Lambert leg solver. The
    numerical output remains identical, but the actual Lambert computation is now
    delegated to mission.leg_solver.compute_lambert_leg().
    """
    results = compute_lambert_leg(
        "Earth",
        "Saturn",
        launch_start,
        launch_end,
        n_departures=n_departures,
        tof_min_years=tof_min_years,
        tof_max_years=tof_max_years,
        tof_step_days=tof_step_days,
    )

    solutions = []
    for result in results:
        solutions.append(
            {
                "dv_depart": result.v_inf_depart,
                "v_infinity_saturn": result.v_inf_arrival,
                "departure_mjd2000": result.departure_mjd2000,
                "arrival_mjd2000": result.arrival_mjd2000,
                "tof_years": result.tof_years,
            }
        )

    if not solutions:
        raise RuntimeError(
            "Aucune solution Lambert Terre -> Saturne "
            "n'a ete trouvee."
        )

    return solutions


def select_best_by_criterion(solutions, key_name):
    """
    Select solution with minimum value for given criterion.
    
    Args:
        solutions: list of solution dicts from _compute_lambert_earth_saturn_grid()
        key_name: str, one of "dv_depart", "v_infinity_saturn", "tof_years"
    
    Returns:
        Single solution dict with minimum key_name value
    
    Raises:
        ValueError: if solutions is empty or key_name not found
    """
    if not solutions:
        raise ValueError("solutions list cannot be empty")
    
    if key_name not in solutions[0]:
        raise ValueError(f"key_name '{key_name}' not found in solution dict")
    
    return min(solutions, key=lambda s: s[key_name])


def select_best_by_departure_v_infinity(solutions):
    """
    Select solution with lowest departure v-infinity.
    
    Args:
        solutions: list of solution dicts
    
    Returns:
        Single solution dict (minimum dv_depart)
    """
    return select_best_by_criterion(solutions, "dv_depart")


def select_best_by_arrival_v_infinity(solutions):
    """
    Select solution with lowest arrival v-infinity at Saturn.
    
    Args:
        solutions: list of solution dicts
    
    Returns:
        Single solution dict (minimum v_infinity_saturn)
    """
    return select_best_by_criterion(solutions, "v_infinity_saturn")


def select_best_by_shortest_mission_duration(solutions):
    """
    Select solution with shortest time-of-flight.
    
    Args:
        solutions: list of solution dicts
    
    Returns:
        Single solution dict (minimum tof_years)
    """
    return select_best_by_criterion(solutions, "tof_years")


def select_pareto_frontier(solutions, objectives=None):
    """
    Filter to Pareto-optimal solutions (non-dominated).
    
    A solution is Pareto-optimal if no other solution is better
    in all objectives simultaneously.
    
    Args:
        solutions: list of solution dicts
        objectives: list of criterion names to minimize, default: ["dv_depart", "v_infinity_saturn"]
    
    Returns:
        list of non-dominated solutions (subset of input)
    
    Note:
        - Empty solutions list returns empty list
        - All solutions non-dominated returns full list
        - Result is NOT sorted (preserves grid order)
    """
    if not solutions:
        return []
    
    if objectives is None:
        objectives = ["dv_depart", "v_infinity_saturn"]
    
    # Verify all objectives exist in first solution
    for obj in objectives:
        if obj not in solutions[0]:
            raise ValueError(f"objective '{obj}' not found in solution dict")
    
    pareto = []
    
    for candidate in solutions:
        is_dominated = False
        
        for other in solutions:
            if candidate is other:
                continue
            
            # Check if other dominates candidate (better or equal in all objectives, strictly better in at least one)
            candidate_worse_or_equal = all(
                other[obj] <= candidate[obj] for obj in objectives
            )
            other_strictly_better = any(
                other[obj] < candidate[obj] for obj in objectives
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
) -> dict:

    # Premiere version du moteur:
    # Terre -> Saturne uniquement.
    if destination.lower() != "saturn":
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
                f"Destination '{destination}' non encore implemente. "
                "Selectionnez Saturn pour tester le moteur "
                "Terre -> Saturne."
            ),
        }

    # Compute all Lambert solutions over grid
    solutions = _compute_lambert_earth_saturn_grid(
        launch_start,
        launch_end,
    )

    # Select best solution (minimum departure v-infinity)
    best = select_best_by_departure_v_infinity(solutions)

    # Budget compatible avec app.py. NOTE: the values stored here are
    # heliocentric excess velocities (v-infinity) and NOT complete
    # propulsive ΔV calculations. Keys remain for backward compatibility
    # but the UI and notes clarify the semantics.
    dv_budget = {
        "dV from LEO": best["dv_depart"],
        "dV DSM/Fly-By": 0.0,
        "dV Capture at Destination": best["v_infinity_saturn"],
        "dV Transfer to Moon": 0.0,
        "dV Capture at Moon": 0.0,
        "dV Lower to Final Orbit": 0.0,
        "dV Break for landing": 0.0,
        "dV Soft Landing": 0.0,
    }

    dv_total = sum(dv_budget.values())

    best_launch_date = pk.epoch(
        best["departure_mjd2000"]
    )

    arrival_date = pk.epoch(
        best["arrival_mjd2000"]
    )

    note = (
        "Premiere version Terre -> Saturne avec Lambert (multi_revs=0). "
        "Important : les valeurs actuellement presentes dans le budget "
        "sont des vitesses d'exces heliocentriques (v∞), PAS des Delta-V "
        "propulsifs completes. Concretement :\n"
        "- departure v∞ : heliocentric excess velocity relative a la Terre.\n"
        "- arrival v∞ : relative velocity at Saturn on arrival.\n"
        "Le calcul complet de dV pour l'evasion depuis LEO ou la capture "
        "a Saturne n'est pas encore implemente. Saturne -> Titan, flybys, "
        "transferts lunaires et atterrissages seront ajoutes ulterieurement."
    )

    return {
        "dv_budget": dv_budget,
        "dv_total": dv_total,
        "best_launch_date": best_launch_date,
        "arrival_date": arrival_date,
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
        RuntimeError: if no valid Lambert solutions found (should not occur for Saturn in normal windows)
    """
    # Non-Saturn guard
    if destination.lower() != "saturn":
        return {
            "all_solutions": [],
            "solution_count": 0,
            "best_by_departure_v_inf": None,
            "best_by_arrival_v_inf": None,
            "best_by_shortest_tof": None,
            "pareto_frontier": [],
            "pareto_count": 0,
            "note": (
                f"Destination '{destination}' non encore implemente. "
                "Selectionnez Saturn pour voir les alternatives."
            ),
        }

    # Compute all Lambert solutions once
    all_solutions = _compute_lambert_earth_saturn_grid(
        launch_start,
        launch_end,
    )

    # Apply all selection strategies to the same grid. Selection helpers
    # continue to operate using legacy key names for compatibility but
    # the solution dicts also carry the explicit `v_inf_*` keys.
    best_by_dep = select_best_by_departure_v_infinity(all_solutions)
    best_by_arr = select_best_by_arrival_v_infinity(all_solutions)
    best_by_tof = select_best_by_shortest_mission_duration(all_solutions)
    pareto = select_pareto_frontier(
        all_solutions,
        objectives=["dv_depart", "v_infinity_saturn"]
    )

    note = (
        "Multiple Earth→Saturn Lambert trajectory alternatives. "
        "Best solutions ranked by different criteria. "
        "Pareto frontier shows non-dominated trade-offs between "
        "departure v-infinity and arrival v-infinity."
    )

    return {
        "all_solutions": all_solutions,
        "solution_count": len(all_solutions),
        "best_by_departure_v_inf": best_by_dep,
        "best_by_arrival_v_inf": best_by_arr,
        "best_by_shortest_tof": best_by_tof,
        "pareto_frontier": pareto,
        "pareto_count": len(pareto),
        "note": note,
    }
