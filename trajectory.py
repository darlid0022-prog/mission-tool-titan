def compute_trajectory(destination: str, departure_type: str, launch_start, launch_end,
                        has_moon_transfer: bool, has_landing: bool, is_flyby_only: bool,
                        dv_per_flyby: float) -> dict:
    """
    TODO (Hermès) :
    - Remplacer ce placeholder par un vrai calcul pykep.
    - Retourner un dict avec les mêmes clés que l'application attend.
    """

    dv_budget = {
        "dV from LEO": 0.0,
        "dV DSM/Fly-By": 0.0,
        "dV Capture at Destination": 0.0,
        "dV Transfer to Moon": 0.0 if has_moon_transfer else 0.0,
        "dV Capture at Moon": 0.0,
        "dV Lower to Final Orbit": 0.0,
        "dV Break for landing": 0.0 if has_landing else 0.0,
        "dV Soft Landing": 0.0 if has_landing else 0.0,
    }

    return {
        "dv_budget": dv_budget,
        "dv_total": sum(dv_budget.values()),
        "best_launch_date": None,
        "arrival_date": None,
        "note": "Placeholder — moteur pykep pas encore branché",
    }