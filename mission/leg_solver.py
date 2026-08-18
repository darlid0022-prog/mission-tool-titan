from __future__ import annotations

import math
from dataclasses import dataclass

import pykep as pk

from .bodies import CelestialBody, resolve_body
from .models import TrajectoryResult


def _norm(v):
    return math.sqrt(sum(x * x for x in v))


def _sub(a, b):
    return [a[i] - b[i] for i in range(3)]


@dataclass(frozen=True)
class _LambertState:
    v_inf_depart_m_s: float
    v_inf_arrival_m_s: float
    departure_position_m: tuple[float, float, float]
    arrival_position_m: tuple[float, float, float]
    transfer_departure_velocity_m_s: tuple[float, float, float]


def _vector3(values) -> tuple[float, float, float]:
    return (float(values[0]), float(values[1]), float(values[2]))


def _solve_lambert_state(
    r0,
    r1,
    tof_seconds: float,
    mu_central_body: float,
    v_origin,
    v_destination,
) -> _LambertState | None:
    """Return the solved state once so callers can retain it for visualization."""
    try:
        lp = pk.lambert_problem(r0, r1, tof_seconds, mu_central_body, multi_revs=0)
    except Exception:
        return None
    if len(lp.v0) == 0:
        return None
    return _LambertState(
        v_inf_depart_m_s=_norm(_sub(lp.v0[0], v_origin)),
        v_inf_arrival_m_s=_norm(_sub(lp.v1[0], v_destination)),
        departure_position_m=_vector3(r0),
        arrival_position_m=_vector3(r1),
        transfer_departure_velocity_m_s=_vector3(lp.v0[0]),
    )


def _resolve_body(body_name: str) -> CelestialBody:
    """Backward-compatible wrapper around the generic body abstraction."""
    return resolve_body(body_name)


def solve_lambert_v_infinities(
    r0,
    r1,
    tof_seconds: float,
    mu_central_body: float,
    v_origin,
    v_destination,
) -> tuple[float, float] | None:
    """Solve one zero-revolution Lambert transfer between two given states.

    The single-pair primitive behind every Lambert grid in this codebase
    (compute_lambert_leg below, and mission/porkchop.py's departure x arrival
    date grid): takes already-sampled ephemeris state vectors so callers can
    reuse one body's state across many pairs instead of re-fetching it.

    Returns `(v_inf_depart, v_inf_arrival)` in m/s, or None if the solver does
    not converge for this geometry/time-of-flight (a geometrically impossible
    or degenerate transfer) - callers should skip/mark that pair rather than
    treat it as an error.
    """
    solved = _solve_lambert_state(
        r0,
        r1,
        tof_seconds,
        mu_central_body,
        v_origin,
        v_destination,
    )
    if solved is None:
        return None
    return solved.v_inf_depart_m_s, solved.v_inf_arrival_m_s


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
            f"Lambert transfer modeling from {origin_body.name} "
            "is intentionally not implemented yet."
        )
    if not destination_body.supports_lambert:
        raise NotImplementedError(
            f"Lambert transfer modeling to {destination_body.name} "
            "is intentionally not implemented yet."
        )

    t_start = (
        pk.epoch(launch_start.strftime("%Y-%m-%d 00:00:00"))
        if hasattr(launch_start, "strftime")
        else launch_start
    )
    t_end = (
        pk.epoch(launch_end.strftime("%Y-%m-%d 00:00:00"))
        if hasattr(launch_end, "strftime")
        else launch_end
    )

    launch_window_days = t_end.mjd2000 - t_start.mjd2000
    if launch_window_days < 0:
        raise ValueError("The launch_end date must be after launch_start.")

    if n_departures == 1:
        departure_offsets = [0.0]
    else:
        departure_offsets = [
            launch_window_days * i / (n_departures - 1) for i in range(n_departures)
        ]

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

            solved = _solve_lambert_state(
                r0,
                r1,
                tof_seconds,
                origin_body.get_mu_central_body(),
                v_origin,
                v_destination,
            )
            if solved is None:
                continue
            results.append(
                TrajectoryResult(
                    departure_mjd2000=departure_mjd2000,
                    arrival_mjd2000=arrival_mjd2000,
                    tof_years=tof_years,
                    v_inf_depart=solved.v_inf_depart_m_s,
                    v_inf_arrival=solved.v_inf_arrival_m_s,
                    delta_v=None,
                    method="lambert",
                    notes=(
                        "Generic Lambert Leg solver; v-infinity values are relative heliocentric "
                        "velocities and not propulsive delta-v."
                    ),
                    departure_position_m=solved.departure_position_m,
                    arrival_position_m=solved.arrival_position_m,
                    transfer_departure_velocity_m_s=(solved.transfer_departure_velocity_m_s),
                    central_mu_m3_s2=float(origin_body.get_mu_central_body()),
                )
            )

    if not results:
        raise RuntimeError(f"No Lambert solutions found for {origin} -> {destination}.")

    return results
