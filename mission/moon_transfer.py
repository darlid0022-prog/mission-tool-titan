"""Preliminary circular, coplanar Saturn-to-Titan transfer model."""

from __future__ import annotations

import math
from dataclasses import dataclass

from . import physics
from .constants import (
    JPL_SATURN_SYSTEM_SOURCE,
    SATURN_MU_M3_S2,
    TITAN_MEAN_ORBIT_RADIUS_M,
    TITAN_MEAN_RADIUS_M,
    TITAN_MU_M3_S2,
)
from .models import Event, Leg, TrajectoryResult

DEFAULT_SATURN_STAGING_RADIUS_M = 6.0e8
DEFAULT_TITAN_CAPTURE_ALTITUDE_M = 1.5e6
MIN_SATURN_STAGING_RADIUS_M = 4.8e8
MIN_TITAN_CAPTURE_ALTITUDE_M = 1.0e6
SECONDS_PER_DAY = 86_400.0
DAYS_PER_JULIAN_YEAR = 365.25


@dataclass(frozen=True)
class SaturnTitanTransferResult:
    """Typed output of the preliminary Saturn-to-Titan Hohmann model."""

    origin: str
    destination: str
    method: str
    source: str
    saturn_staging_radius_m: float
    titan_orbit_radius_m: float
    titan_capture_altitude_m: float
    titan_capture_radius_m: float
    saturn_staging_circular_speed_m_s: float
    transfer_departure_speed_m_s: float
    departure_delta_v_m_s: float
    transfer_arrival_speed_m_s: float
    titan_orbital_speed_m_s: float
    v_infinity_titan_m_s: float
    time_of_flight_s: float
    capture_delta_v_m_s: float
    total_delta_v_m_s: float
    assumptions: tuple[str, ...]
    exclusions: tuple[str, ...]

    @property
    def time_of_flight_days(self) -> float:
        return self.time_of_flight_s / SECONDS_PER_DAY


def _require_finite_number(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise TypeError(f"{name} must be a real number in metres.")
    converted = float(value)
    if not math.isfinite(converted):
        raise ValueError(f"{name} must be finite.")
    return converted


def compute_saturn_titan_transfer(
    saturn_staging_radius_m: float = DEFAULT_SATURN_STAGING_RADIUS_M,
    titan_capture_altitude_m: float = DEFAULT_TITAN_CAPTURE_ALTITUDE_M,
) -> SaturnTitanTransferResult:
    """Compute the specification's first-order Saturn-to-Titan transfer.

    All inputs and outputs use SI units. The result excludes the manoeuvres
    required to move from Saturn arrival/capture to the staging orbit.
    """
    r_1 = _require_finite_number("saturn_staging_radius_m", saturn_staging_radius_m)
    capture_altitude = _require_finite_number("titan_capture_altitude_m", titan_capture_altitude_m)

    if r_1 <= MIN_SATURN_STAGING_RADIUS_M:
        raise ValueError(
            "saturn_staging_radius_m must be greater than the preliminary "
            f"ring guard ({MIN_SATURN_STAGING_RADIUS_M:.0f} m)."
        )
    if r_1 >= TITAN_MEAN_ORBIT_RADIUS_M:
        raise ValueError("saturn_staging_radius_m must be less than Titan's mean orbital radius.")
    if capture_altitude < MIN_TITAN_CAPTURE_ALTITUDE_M:
        raise ValueError(
            "titan_capture_altitude_m must be at least the preliminary "
            f"non-atmospheric guard ({MIN_TITAN_CAPTURE_ALTITUDE_M:.0f} m)."
        )

    r_2 = TITAN_MEAN_ORBIT_RADIUS_M
    transfer_semimajor_axis = (r_1 + r_2) / 2.0

    staging_circular_speed = math.sqrt(SATURN_MU_M3_S2 / r_1)
    transfer_departure_speed = math.sqrt(
        SATURN_MU_M3_S2 * (2.0 / r_1 - 1.0 / transfer_semimajor_axis)
    )
    departure_delta_v = transfer_departure_speed - staging_circular_speed

    transfer_arrival_speed = math.sqrt(
        SATURN_MU_M3_S2 * (2.0 / r_2 - 1.0 / transfer_semimajor_axis)
    )
    titan_orbital_speed = math.sqrt(SATURN_MU_M3_S2 / r_2)
    v_infinity_titan = abs(titan_orbital_speed - transfer_arrival_speed)

    time_of_flight = math.pi * math.sqrt(transfer_semimajor_axis**3 / SATURN_MU_M3_S2)

    titan_capture_radius = TITAN_MEAN_RADIUS_M + capture_altitude
    capture_delta_v = physics.delta_v_capture(
        v_infinity_titan,
        TITAN_MU_M3_S2,
        titan_capture_radius,
    )
    total_delta_v = departure_delta_v + capture_delta_v

    return SaturnTitanTransferResult(
        origin="Saturn",
        destination="Titan",
        method="hohmann_circular_coplanar",
        source=JPL_SATURN_SYSTEM_SOURCE,
        saturn_staging_radius_m=r_1,
        titan_orbit_radius_m=r_2,
        titan_capture_altitude_m=capture_altitude,
        titan_capture_radius_m=titan_capture_radius,
        saturn_staging_circular_speed_m_s=staging_circular_speed,
        transfer_departure_speed_m_s=transfer_departure_speed,
        departure_delta_v_m_s=departure_delta_v,
        transfer_arrival_speed_m_s=transfer_arrival_speed,
        titan_orbital_speed_m_s=titan_orbital_speed,
        v_infinity_titan_m_s=v_infinity_titan,
        time_of_flight_s=time_of_flight,
        capture_delta_v_m_s=capture_delta_v,
        total_delta_v_m_s=total_delta_v,
        assumptions=(
            "Saturn-centred circular and coplanar staging and Titan orbits.",
            "Two-impulse Hohmann transfer with instantaneous burns.",
            "Impulsive fully propulsive circular capture at Titan.",
        ),
        exclusions=(
            "Saturn arrival/capture to staging-orbit manoeuvres.",
            "Ring interactions, plane changes, perturbations, and finite burns.",
            "Titan aerocapture and atmospheric effects.",
        ),
    )


def adapt_saturn_titan_transfer_to_leg(
    result: SaturnTitanTransferResult,
    *,
    departure_epoch_mjd2000: float | None = None,
) -> Leg:
    """Adapt the preliminary transfer into the canonical mission-domain types."""
    if not isinstance(result, SaturnTitanTransferResult):
        raise TypeError("result must be a SaturnTitanTransferResult.")

    departure_epoch: float | None = None
    arrival_epoch: float | None = None
    if departure_epoch_mjd2000 is not None:
        departure_epoch = _require_finite_number("departure_epoch_mjd2000", departure_epoch_mjd2000)
        arrival_epoch = departure_epoch + result.time_of_flight_s / SECONDS_PER_DAY

    trajectory = TrajectoryResult(
        departure_mjd2000=departure_epoch,
        arrival_mjd2000=arrival_epoch,
        tof_years=result.time_of_flight_s / (DAYS_PER_JULIAN_YEAR * SECONDS_PER_DAY),
        v_inf_depart=None,
        v_inf_arrival=result.v_infinity_titan_m_s,
        delta_v=result.total_delta_v_m_s,
        method=result.method,
        notes=(f"{result.source}; Titan v-infinity remains distinct from propulsive delta-v."),
    )
    events = [
        Event(
            name="Saturn staging departure",
            body="Saturn",
            event_type="departure",
            epoch=departure_epoch,
            notes="Impulsive departure from the circular Saturn staging orbit.",
        ),
        Event(
            name="Titan capture",
            body="Titan",
            event_type="capture",
            epoch=arrival_epoch,
            notes="Impulsive fully propulsive circular capture at Titan.",
        ),
    ]
    return Leg(
        origin=result.origin,
        destination=result.destination,
        trajectory=trajectory,
        events=events,
        notes="Preliminary circular, coplanar Saturn-to-Titan transfer.",
    )
