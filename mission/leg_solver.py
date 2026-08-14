from __future__ import annotations

import math

import pykep as pk

from .bodies import CelestialBody, resolve_body
from .models import TrajectoryResult


def _norm(v):
    return math.sqrt(sum(x * x for x in v))


def _sub(a, b):
    return [a[i] - b[i] for i in range(3)]


def _resolve_body(body_name: str) -> CelestialBody:
    """Backward-compatible wrapper around the generic body abstraction."""
    return resolve_body(body_name)


def compute_lambert_leg(
    origin: str,
    destination: str,
    launch_start,
    launch_end,
    *,
    n_departures: int = 12,
    tof_min_years: float = 4.0,
    tof_max_years: float = 8.0,
    tof_step_days: float = 15.0,
) -> list[TrajectoryResult]:
    """Generic Lambert leg solver for Earth/Saturn-style interplanetary transfers.

    This intentionally mirrors the existing Earth->Saturn methodology in trajectory.py,
    but without hard-coding Earth/Saturn into the public API. It preserves the exact
    numerical approach: heliocentric state sampling, Lambert solving, and v∞ evaluation.
    """
    origin_body = _resolve_body(origin)
    destination_body = _resolve_body(destination)

    if not origin_body.supports_lambert:
        raise NotImplementedError(
            f"Lambert transfer modeling from {origin_body.name} is intentionally not implemented yet."
        )
    if not destination_body.supports_lambert:
        raise NotImplementedError(
            f"Lambert transfer modeling to {destination_body.name} is intentionally not implemented yet."
        )

    t_start = pk.epoch(launch_start.strftime("%Y-%m-%d 00:00:00")) if hasattr(launch_start, "strftime") else launch_start
    t_end = pk.epoch(launch_end.strftime("%Y-%m-%d 00:00:00")) if hasattr(launch_end, "strftime") else launch_end

    launch_window_days = t_end.mjd2000 - t_start.mjd2000
    if launch_window_days < 0:
        raise ValueError("The launch_end date must be after launch_start.")

    if n_departures == 1:
        departure_offsets = [0.0]
    else:
        departure_offsets = [launch_window_days * i / (n_departures - 1) for i in range(n_departures)]

    tof_years_list = []
    tof_years = tof_min_years
    while tof_years <= tof_max_years + 1e-9:
        tof_years_list.append(tof_years)
        tof_years += tof_step_days / 365.25

    results: list[TrajectoryResult] = []

    for departure_offset in departure_offsets:
        departure_mjd2000 = t_start.mjd2000 + departure_offset
        r0, v_origin = origin_body.eph(departure_mjd2000)

        for tof_years in tof_years_list:
            tof_seconds = tof_years * 365.25 * 86400.0
            arrival_mjd2000 = departure_mjd2000 + tof_seconds / 86400.0

            r1, v_destination = destination_body.eph(arrival_mjd2000)

            try:
                lp = pk.lambert_problem(
                    r0,
                    r1,
                    tof_seconds,
                    origin_body.get_mu_central_body(),
                    multi_revs=0,
                )
            except Exception:
                continue

            if len(lp.v0) == 0:
                continue

            v_transfer_depart = lp.v0[0]
            v_transfer_arrival = lp.v1[0]

            v_inf_depart = _norm(_sub(v_transfer_depart, v_origin))
            v_inf_arrival = _norm(_sub(v_transfer_arrival, v_destination))

            results.append(
                TrajectoryResult(
                    departure_mjd2000=departure_mjd2000,
                    arrival_mjd2000=arrival_mjd2000,
                    tof_years=tof_years,
                    v_inf_depart=v_inf_depart,
                    v_inf_arrival=v_inf_arrival,
                    delta_v=None,
                    method="lambert",
                    notes=(
                        "Generic Lambert Leg solver; v-infinity values are relative heliocentric "
                        "velocities and not propulsive delta-v."
                    ),
                )
            )

    if not results:
        raise RuntimeError(f"No Lambert solutions found for {origin} -> {destination}.")

    return results
