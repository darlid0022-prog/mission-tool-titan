"""Pure, body-agnostic parent-body-to-moon Hohmann transfer model."""

from __future__ import annotations

import math
from dataclasses import dataclass

from . import physics
from .models import Event, Leg, TrajectoryResult

SECONDS_PER_DAY = 86_400.0
DAYS_PER_JULIAN_YEAR = 365.25
METHOD = "hohmann_circular_coplanar"


@dataclass(frozen=True)
class StagingRadiusGuard:
    """Optional body-specific lower bound for the departure staging radius."""

    minimum_radius_m: float
    description: str


@dataclass(frozen=True)
class MoonCaptureAltitudeGuard:
    """Optional body-specific lower bound for the moon capture altitude."""

    minimum_altitude_m: float
    description: str


@dataclass(frozen=True)
class ParentMoonTransferResult:
    """Typed result shared by parent-to-moon transfer studies for any pair."""

    parent_body: str
    moon_body: str
    method: str
    source: str
    parent_staging_radius_m: float
    moon_orbit_radius_m: float
    moon_capture_altitude_m: float
    moon_capture_radius_m: float
    parent_staging_circular_speed_m_s: float
    transfer_departure_speed_m_s: float
    departure_delta_v_m_s: float
    transfer_arrival_speed_m_s: float
    moon_orbital_speed_m_s: float
    v_infinity_moon_m_s: float
    time_of_flight_s: float
    capture_delta_v_m_s: float
    total_delta_v_m_s: float
    assumptions: tuple[str, ...]
    exclusions: tuple[str, ...]

    @property
    def time_of_flight_days(self) -> float:
        return self.time_of_flight_s / SECONDS_PER_DAY


def _require_non_empty_string(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string.")
    return value.strip()


def _require_finite_number(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise TypeError(f"{name} must be a real number in SI units.")
    converted = float(value)
    if not math.isfinite(converted):
        raise ValueError(f"{name} must be finite.")
    return converted


def compute_parent_to_moon_transfer(
    *,
    parent_body: str,
    moon_body: str,
    parent_mu_m3_s2: float,
    moon_mu_m3_s2: float,
    moon_radius_m: float,
    parent_staging_radius_m: float,
    moon_orbit_radius_m: float,
    moon_capture_altitude_m: float,
    source: str,
    staging_radius_guard: StagingRadiusGuard | None = None,
    moon_capture_altitude_guard: MoonCaptureAltitudeGuard | None = None,
) -> ParentMoonTransferResult:
    """Compute a first-order circular, coplanar Hohmann parent-to-moon transfer.

    All inputs and outputs use SI units. The two-body Hohmann-transfer equations
    are body agnostic; body-specific geometry or environmental constraints
    (ring guards, non-atmospheric capture-altitude guards, ...) are supplied as
    optional guards rather than hard-coded into the physics.
    """
    parent = _require_non_empty_string("parent_body", parent_body)
    moon = _require_non_empty_string("moon_body", moon_body)
    source_name = _require_non_empty_string("source", source)
    mu_parent = _require_finite_number("parent_mu_m3_s2", parent_mu_m3_s2)
    mu_moon = _require_finite_number("moon_mu_m3_s2", moon_mu_m3_s2)
    moon_radius = _require_finite_number("moon_radius_m", moon_radius_m)
    r_1 = _require_finite_number("parent_staging_radius_m", parent_staging_radius_m)
    r_2 = _require_finite_number("moon_orbit_radius_m", moon_orbit_radius_m)
    capture_altitude = _require_finite_number("moon_capture_altitude_m", moon_capture_altitude_m)

    if mu_parent <= 0.0:
        raise ValueError("parent_mu_m3_s2 must be positive.")
    if mu_moon <= 0.0:
        raise ValueError("moon_mu_m3_s2 must be positive.")
    if moon_radius <= 0.0:
        raise ValueError("moon_radius_m must be positive.")
    if r_2 <= 0.0:
        raise ValueError("moon_orbit_radius_m must be positive.")
    if capture_altitude < 0.0:
        raise ValueError("moon_capture_altitude_m must be non-negative.")

    if staging_radius_guard is not None:
        if not isinstance(staging_radius_guard, StagingRadiusGuard):
            raise TypeError("staging_radius_guard must be a StagingRadiusGuard or None.")
        minimum_staging_radius = _require_finite_number(
            "staging_radius_guard.minimum_radius_m",
            staging_radius_guard.minimum_radius_m,
        )
        guard_description = _require_non_empty_string(
            "staging_radius_guard.description",
            staging_radius_guard.description,
        )
        if minimum_staging_radius <= 0.0:
            raise ValueError("staging_radius_guard.minimum_radius_m must be positive.")
        if r_1 <= minimum_staging_radius:
            raise ValueError(
                "parent_staging_radius_m must be greater than "
                f"{guard_description} ({minimum_staging_radius:.0f} m)."
            )
    elif r_1 <= 0.0:
        raise ValueError("parent_staging_radius_m must be positive.")

    if r_1 >= r_2:
        raise ValueError(f"parent_staging_radius_m must be less than {moon}'s mean orbital radius.")

    if moon_capture_altitude_guard is not None:
        if not isinstance(moon_capture_altitude_guard, MoonCaptureAltitudeGuard):
            raise TypeError(
                "moon_capture_altitude_guard must be a MoonCaptureAltitudeGuard or None."
            )
        minimum_altitude = _require_finite_number(
            "moon_capture_altitude_guard.minimum_altitude_m",
            moon_capture_altitude_guard.minimum_altitude_m,
        )
        altitude_guard_description = _require_non_empty_string(
            "moon_capture_altitude_guard.description",
            moon_capture_altitude_guard.description,
        )
        if minimum_altitude < 0.0:
            raise ValueError("moon_capture_altitude_guard.minimum_altitude_m must be non-negative.")
        if capture_altitude < minimum_altitude:
            raise ValueError(
                "moon_capture_altitude_m must be at least "
                f"{altitude_guard_description} ({minimum_altitude:.0f} m)."
            )

    transfer_semimajor_axis = (r_1 + r_2) / 2.0

    parent_staging_circular_speed = math.sqrt(mu_parent / r_1)
    transfer_departure_speed = math.sqrt(mu_parent * (2.0 / r_1 - 1.0 / transfer_semimajor_axis))
    departure_delta_v = transfer_departure_speed - parent_staging_circular_speed

    transfer_arrival_speed = math.sqrt(mu_parent * (2.0 / r_2 - 1.0 / transfer_semimajor_axis))
    moon_orbital_speed = math.sqrt(mu_parent / r_2)
    v_infinity_moon = abs(moon_orbital_speed - transfer_arrival_speed)

    time_of_flight = math.pi * math.sqrt(transfer_semimajor_axis**3 / mu_parent)

    moon_capture_radius = moon_radius + capture_altitude
    capture_delta_v = physics.delta_v_capture(v_infinity_moon, mu_moon, moon_capture_radius)
    total_delta_v = departure_delta_v + capture_delta_v

    return ParentMoonTransferResult(
        parent_body=parent,
        moon_body=moon,
        method=METHOD,
        source=source_name,
        parent_staging_radius_m=r_1,
        moon_orbit_radius_m=r_2,
        moon_capture_altitude_m=capture_altitude,
        moon_capture_radius_m=moon_capture_radius,
        parent_staging_circular_speed_m_s=parent_staging_circular_speed,
        transfer_departure_speed_m_s=transfer_departure_speed,
        departure_delta_v_m_s=departure_delta_v,
        transfer_arrival_speed_m_s=transfer_arrival_speed,
        moon_orbital_speed_m_s=moon_orbital_speed,
        v_infinity_moon_m_s=v_infinity_moon,
        time_of_flight_s=time_of_flight,
        capture_delta_v_m_s=capture_delta_v,
        total_delta_v_m_s=total_delta_v,
        assumptions=(
            f"{parent}-centred circular and coplanar staging and {moon} orbits.",
            "Two-impulse Hohmann transfer with instantaneous burns.",
            f"Impulsive fully propulsive circular capture at {moon}.",
        ),
        exclusions=(
            f"{parent} arrival/capture to staging-orbit manoeuvres.",
            "Ring interactions, plane changes, perturbations, and finite burns.",
            f"{moon} aerocapture and atmospheric effects.",
        ),
    )


def adapt_parent_moon_transfer_to_leg(
    result: ParentMoonTransferResult,
    *,
    departure_epoch_mjd2000: float | None = None,
) -> Leg:
    """Adapt a generic parent-to-moon transfer result to canonical mission types."""
    if not isinstance(result, ParentMoonTransferResult):
        raise TypeError("result must be a ParentMoonTransferResult.")

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
        v_inf_arrival=result.v_infinity_moon_m_s,
        delta_v=result.total_delta_v_m_s,
        method=result.method,
        notes=(
            f"{result.source}; {result.moon_body} v-infinity remains distinct from "
            "propulsive delta-v."
        ),
    )
    events = [
        Event(
            name=f"{result.parent_body} staging departure",
            body=result.parent_body,
            event_type="departure",
            epoch=departure_epoch,
            notes=f"Impulsive departure from the circular {result.parent_body} staging orbit.",
        ),
        Event(
            name=f"{result.moon_body} capture",
            body=result.moon_body,
            event_type="capture",
            epoch=arrival_epoch,
            notes=f"Impulsive fully propulsive circular capture at {result.moon_body}.",
        ),
    ]
    return Leg(
        origin=result.parent_body,
        destination=result.moon_body,
        trajectory=trajectory,
        events=events,
        notes=(
            f"Preliminary circular, coplanar {result.parent_body}-to-{result.moon_body} transfer."
        ),
    )
