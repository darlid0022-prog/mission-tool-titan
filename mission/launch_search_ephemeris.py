"""Cached real-ephemeris sampling and Lambert propagation for launch searches."""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

import pykep as pk

from .bodies import resolve_body
from .constants import ASTRONOMICAL_UNIT_M

SECONDS_PER_DAY = 86_400.0
EPHEMERIS_SOURCE = "PyKEP udpla.jpl_lp analytical JPL low-precision ephemerides"
LAMBERT_METHOD = "PyKEP zero-revolution Lambert problem"
Vector3 = tuple[float, float, float]


def _vector(values: object) -> Vector3:
    result = tuple(float(value) for value in values)  # type: ignore[arg-type]
    if len(result) != 3 or not all(math.isfinite(value) for value in result):
        raise ValueError("Ephemeris and Lambert vectors must contain three finite values.")
    return result  # type: ignore[return-value]


def _norm(vector: Vector3) -> float:
    return math.sqrt(sum(value * value for value in vector))


def _subtract(left: Vector3, right: Vector3) -> Vector3:
    return tuple(left[index] - right[index] for index in range(3))  # type: ignore[return-value]


@lru_cache(maxsize=16_384)
def heliocentric_state(body_name: str, epoch_mjd2000: float) -> tuple[Vector3, Vector3]:
    """Return a cached SI heliocentric state from PyKEP's JPL ephemeris."""
    epoch = float(epoch_mjd2000)
    if not math.isfinite(epoch):
        raise ValueError("epoch_mjd2000 must be finite.")
    body = resolve_body(body_name)
    if not body.supports_lambert:
        raise ValueError(f"{body.name} does not provide a heliocentric ephemeris.")
    position, velocity = body.eph(epoch)
    return _vector(position), _vector(velocity)


@dataclass(frozen=True)
class LambertTransfer:
    departure_mjd2000: float
    arrival_mjd2000: float
    time_of_flight_s: float
    departure_position_m: Vector3
    arrival_position_m: Vector3
    earth_velocity_m_s: Vector3
    saturn_velocity_m_s: Vector3
    transfer_departure_velocity_m_s: Vector3
    transfer_arrival_velocity_m_s: Vector3
    earth_v_infinity_vector_m_s: Vector3
    saturn_v_infinity_vector_m_s: Vector3
    earth_v_infinity_m_s: float
    saturn_v_infinity_m_s: float
    sample_positions_au: tuple[Vector3, ...]
    ephemeris_source: str = EPHEMERIS_SOURCE
    method: str = LAMBERT_METHOD


@lru_cache(maxsize=32_768)
def solve_earth_saturn_lambert(
    departure_mjd2000: float,
    arrival_mjd2000: float,
    sample_count: int = 48,
) -> LambertTransfer:
    """Solve one direct Earth-to-Saturn Lambert arc with cached real states."""
    departure = float(departure_mjd2000)
    arrival = float(arrival_mjd2000)
    if not math.isfinite(departure) or not math.isfinite(arrival):
        raise ValueError("Lambert epochs must be finite.")
    if arrival <= departure:
        raise ValueError("Lambert arrival must follow departure.")
    if isinstance(sample_count, bool) or not isinstance(sample_count, int) or sample_count < 2:
        raise ValueError("sample_count must be an integer of at least two.")

    earth_position, earth_velocity = heliocentric_state("Earth", departure)
    saturn_position, saturn_velocity = heliocentric_state("Saturn", arrival)
    tof_seconds = (arrival - departure) * SECONDS_PER_DAY
    solar_mu = float(resolve_body("Earth").get_mu_central_body())
    try:
        problem = pk.lambert_problem(
            earth_position,
            saturn_position,
            tof_seconds,
            solar_mu,
            multi_revs=0,
        )
    except Exception as exc:
        raise RuntimeError(f"Lambert solver failed: {exc}") from exc
    if not problem.v0:
        raise RuntimeError("Lambert solver returned no zero-revolution solution.")

    transfer_departure_velocity = _vector(problem.v0[0])
    transfer_arrival_velocity = _vector(problem.v1[0])
    earth_v_inf_vector = _subtract(transfer_departure_velocity, earth_velocity)
    saturn_v_inf_vector = _subtract(transfer_arrival_velocity, saturn_velocity)

    samples: list[Vector3] = []
    for index in range(sample_count):
        elapsed = tof_seconds * index / (sample_count - 1)
        if index == 0:
            position = earth_position
        elif index == sample_count - 1:
            position = saturn_position
        else:
            position, _ = pk.propagate_lagrangian(
                (earth_position, transfer_departure_velocity),
                elapsed,
                solar_mu,
            )
        samples.append(tuple(value / ASTRONOMICAL_UNIT_M for value in _vector(position)))

    return LambertTransfer(
        departure_mjd2000=departure,
        arrival_mjd2000=arrival,
        time_of_flight_s=tof_seconds,
        departure_position_m=earth_position,
        arrival_position_m=saturn_position,
        earth_velocity_m_s=earth_velocity,
        saturn_velocity_m_s=saturn_velocity,
        transfer_departure_velocity_m_s=transfer_departure_velocity,
        transfer_arrival_velocity_m_s=transfer_arrival_velocity,
        earth_v_infinity_vector_m_s=earth_v_inf_vector,
        saturn_v_infinity_vector_m_s=saturn_v_inf_vector,
        earth_v_infinity_m_s=_norm(earth_v_inf_vector),
        saturn_v_infinity_m_s=_norm(saturn_v_inf_vector),
        sample_positions_au=tuple(samples),
    )


def clear_launch_search_caches() -> None:
    heliocentric_state.cache_clear()
    solve_earth_saturn_lambert.cache_clear()
