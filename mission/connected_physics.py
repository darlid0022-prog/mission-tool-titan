"""First-order analytical Earth -> Saturn -> Titan-orbit physics chain.

The endpoint is a Saturn-centred circular orbit at Titan's mean orbital
radius. It is not a phased Titan encounter and includes no Titan capture.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .constants import (
    EARTH_MEAN_ORBIT_RADIUS_M,
    F_RING_REFERENCE_RADIUS_M,
    JPL_DE440_SOURCE,
    JPL_SATURN_SYSTEM_SOURCE,
    NOMINAL_SATURN_PERIAPSIS_RADIUS_M,
    SATURN_EQUATORIAL_RADIUS_M,
    SATURN_MEAN_ORBIT_RADIUS_M,
    SATURN_MU_M3_S2,
    SUN_MU_M3_S2,
    TITAN_MEAN_ORBIT_RADIUS_M,
)

SECONDS_PER_DAY = 86_400.0
METHOD = "hohmann_heliocentric_then_saturn_capture_to_titan_orbit"


@dataclass(frozen=True)
class EarthSaturnHohmannResult:
    source: str
    earth_orbit_radius_m: float
    saturn_orbit_radius_m: float
    transfer_semimajor_axis_m: float
    earth_circular_speed_m_s: float
    saturn_circular_speed_m_s: float
    transfer_departure_speed_m_s: float
    transfer_arrival_speed_m_s: float
    departure_v_infinity_m_s: float
    arrival_v_infinity_m_s: float
    time_of_flight_s: float

    @property
    def time_of_flight_days(self) -> float:
        return self.time_of_flight_s / SECONDS_PER_DAY


@dataclass(frozen=True)
class SaturnHyperbolaResult:
    specific_energy_j_kg: float
    semimajor_axis_m: float
    eccentricity: float
    periapsis_radius_m: float
    periapsis_speed_m_s: float
    turn_angle_rad: float


@dataclass(frozen=True)
class SaturnCaptureEllipseResult:
    specific_energy_j_kg: float
    semimajor_axis_m: float
    eccentricity: float
    periapsis_radius_m: float
    apoapsis_radius_m: float
    periapsis_speed_m_s: float
    apoapsis_speed_m_s: float
    circular_speed_at_apoapsis_m_s: float
    capture_delta_v_m_s: float
    circularisation_delta_v_m_s: float
    total_delta_v_m_s: float
    time_of_flight_s: float

    @property
    def time_of_flight_days(self) -> float:
        return self.time_of_flight_s / SECONDS_PER_DAY


@dataclass(frozen=True)
class ConnectedFirstOrderResult:
    method: str
    heliocentric: EarthSaturnHohmannResult
    saturn_hyperbola: SaturnHyperbolaResult
    saturn_capture: SaturnCaptureEllipseResult
    assumptions: tuple[str, ...]
    exclusions: tuple[str, ...]


def _finite_si(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise TypeError(f"{name} must be a real number in SI units.")
    converted = float(value)
    if not math.isfinite(converted):
        raise ValueError(f"{name} must be finite.")
    return converted


def compute_earth_saturn_hohmann(
    *,
    sun_mu_m3_s2: float = SUN_MU_M3_S2,
    earth_orbit_radius_m: float = EARTH_MEAN_ORBIT_RADIUS_M,
    saturn_orbit_radius_m: float = SATURN_MEAN_ORBIT_RADIUS_M,
) -> EarthSaturnHohmannResult:
    """Compute a circular, coplanar heliocentric Hohmann transfer in SI."""
    mu = _finite_si("sun_mu_m3_s2", sun_mu_m3_s2)
    r_earth = _finite_si("earth_orbit_radius_m", earth_orbit_radius_m)
    r_saturn = _finite_si("saturn_orbit_radius_m", saturn_orbit_radius_m)
    if mu <= 0.0 or r_earth <= 0.0 or r_saturn <= 0.0:
        raise ValueError("Gravitational parameter and orbital radii must be positive.")
    if r_saturn <= r_earth:
        raise ValueError("saturn_orbit_radius_m must exceed earth_orbit_radius_m.")

    axis = (r_earth + r_saturn) / 2.0
    earth_speed = math.sqrt(mu / r_earth)
    saturn_speed = math.sqrt(mu / r_saturn)
    departure_speed = math.sqrt(mu * (2.0 / r_earth - 1.0 / axis))
    arrival_speed = math.sqrt(mu * (2.0 / r_saturn - 1.0 / axis))
    return EarthSaturnHohmannResult(
        source=JPL_DE440_SOURCE,
        earth_orbit_radius_m=r_earth,
        saturn_orbit_radius_m=r_saturn,
        transfer_semimajor_axis_m=axis,
        earth_circular_speed_m_s=earth_speed,
        saturn_circular_speed_m_s=saturn_speed,
        transfer_departure_speed_m_s=departure_speed,
        transfer_arrival_speed_m_s=arrival_speed,
        departure_v_infinity_m_s=departure_speed - earth_speed,
        arrival_v_infinity_m_s=abs(saturn_speed - arrival_speed),
        time_of_flight_s=math.pi * math.sqrt(axis**3 / mu),
    )


def compute_saturn_capture_to_titan_orbit(
    arrival_v_infinity_m_s: float,
    *,
    saturn_mu_m3_s2: float = SATURN_MU_M3_S2,
    periapsis_radius_m: float = NOMINAL_SATURN_PERIAPSIS_RADIUS_M,
    apoapsis_radius_m: float = TITAN_MEAN_ORBIT_RADIUS_M,
) -> tuple[SaturnHyperbolaResult, SaturnCaptureEllipseResult]:
    """Capture at periapsis and circularise Saturn-centred at Titan's radius."""
    v_inf = _finite_si("arrival_v_infinity_m_s", arrival_v_infinity_m_s)
    mu = _finite_si("saturn_mu_m3_s2", saturn_mu_m3_s2)
    periapsis = _finite_si("periapsis_radius_m", periapsis_radius_m)
    apoapsis = _finite_si("apoapsis_radius_m", apoapsis_radius_m)
    if v_inf <= 0.0:
        raise ValueError("arrival_v_infinity_m_s must be positive for a hyperbola.")
    if mu <= 0.0:
        raise ValueError("saturn_mu_m3_s2 must be positive.")
    if periapsis <= SATURN_EQUATORIAL_RADIUS_M:
        raise ValueError("periapsis_radius_m must exceed Saturn's equatorial radius.")
    if periapsis <= F_RING_REFERENCE_RADIUS_M:
        raise ValueError("periapsis_radius_m must lie outside the reference F-ring radius.")
    if apoapsis <= periapsis:
        raise ValueError("apoapsis_radius_m must be greater than periapsis_radius_m.")

    hyperbolic_energy = v_inf**2 / 2.0
    hyperbolic_axis = -mu / v_inf**2
    hyperbolic_eccentricity = 1.0 + periapsis * v_inf**2 / mu
    hyperbolic_periapsis_speed = math.sqrt(v_inf**2 + 2.0 * mu / periapsis)
    turn_angle = 2.0 * math.asin(1.0 / hyperbolic_eccentricity)

    ellipse_axis = (periapsis + apoapsis) / 2.0
    ellipse_energy = -mu / (2.0 * ellipse_axis)
    ellipse_eccentricity = (apoapsis - periapsis) / (apoapsis + periapsis)
    ellipse_periapsis_speed = math.sqrt(
        mu * (2.0 / periapsis - 1.0 / ellipse_axis)
    )
    ellipse_apoapsis_speed = math.sqrt(mu * (2.0 / apoapsis - 1.0 / ellipse_axis))
    circular_speed = math.sqrt(mu / apoapsis)
    capture_delta_v = hyperbolic_periapsis_speed - ellipse_periapsis_speed
    circularisation_delta_v = circular_speed - ellipse_apoapsis_speed
    total_delta_v = capture_delta_v + circularisation_delta_v

    return (
        SaturnHyperbolaResult(
            specific_energy_j_kg=hyperbolic_energy,
            semimajor_axis_m=hyperbolic_axis,
            eccentricity=hyperbolic_eccentricity,
            periapsis_radius_m=periapsis,
            periapsis_speed_m_s=hyperbolic_periapsis_speed,
            turn_angle_rad=turn_angle,
        ),
        SaturnCaptureEllipseResult(
            specific_energy_j_kg=ellipse_energy,
            semimajor_axis_m=ellipse_axis,
            eccentricity=ellipse_eccentricity,
            periapsis_radius_m=periapsis,
            apoapsis_radius_m=apoapsis,
            periapsis_speed_m_s=ellipse_periapsis_speed,
            apoapsis_speed_m_s=ellipse_apoapsis_speed,
            circular_speed_at_apoapsis_m_s=circular_speed,
            capture_delta_v_m_s=capture_delta_v,
            circularisation_delta_v_m_s=circularisation_delta_v,
            total_delta_v_m_s=total_delta_v,
            time_of_flight_s=math.pi * math.sqrt(ellipse_axis**3 / mu),
        ),
    )


def compute_connected_first_order_chain() -> ConnectedFirstOrderResult:
    """Compute the complete deterministic analytical chain without ephemerides."""
    heliocentric = compute_earth_saturn_hohmann()
    hyperbola, capture = compute_saturn_capture_to_titan_orbit(
        heliocentric.arrival_v_infinity_m_s
    )
    return ConnectedFirstOrderResult(
        method=METHOD,
        heliocentric=heliocentric,
        saturn_hyperbola=hyperbola,
        saturn_capture=capture,
        assumptions=(
            "Circular coplanar Earth and Saturn heliocentric orbits.",
            "Two-body point-mass dynamics and tangential impulsive burns.",
            "All radii are measured from the relevant body's centre.",
        ),
        exclusions=(
            "Launch-window phasing, Lambert geometry, gravity assists, and corrections.",
            "Saturn oblateness, finite burns, perturbations, and ring-plane geometry.",
            "Titan encounter phasing and Titan-centred capture; endpoint is only co-orbital.",
        ),
    )
