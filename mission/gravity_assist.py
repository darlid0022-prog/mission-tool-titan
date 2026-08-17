from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass

import pykep as pk

Vector3 = tuple[float, float, float]

TURN_ANGLE_SOURCE = (
    "NASA NTRS 20170005667, patched-conic gravity-assist geometry: "
    "https://ntrs.nasa.gov/api/citations/20170005667/downloads/20170005667.pdf"
)
VENUS_ALTITUDE_SOURCE = (
    "NASA Cassini mission timeline: the second Venus flyby passed about 600 km above Venus: "
    "https://science.nasa.gov/mission/cassini/the-journey/timeline/"
)

# Fixed epochs make this scientific demonstration reproducible. They bracket Cassini's
# first Earth-to-Venus leg; this module does not reproduce or optimize the full VVEJGA tour.
DEMO_EARTH_DEPARTURE = "1997-10-15 08:43:00"
DEMO_VENUS_ARRIVAL = "1998-04-26 13:44:00"
DEMO_VENUS_FLYBY_ALTITUDE_M = 600_000.0


@dataclass(frozen=True)
class GravityAssistResult:
    body: str
    periapsis_altitude_m: float
    periapsis_radius_m: float
    turn_angle_rad: float
    v_infinity_in_m_s: Vector3
    v_infinity_out_m_s: Vector3
    v_infinity_magnitude_m_s: float
    body_heliocentric_velocity_m_s: Vector3
    heliocentric_velocity_in_m_s: Vector3
    heliocentric_velocity_out_m_s: Vector3
    heliocentric_speed_in_m_s: float
    heliocentric_speed_out_m_s: float
    heliocentric_speed_change_m_s: float
    turn_direction: int
    method: str = "unpowered_patched_conic_flyby"


def _vector(values: Iterable[float], name: str) -> Vector3:
    try:
        vector = tuple(float(value) for value in values)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must contain three finite numeric values.") from exc
    if len(vector) != 3 or not all(math.isfinite(value) for value in vector):
        raise ValueError(f"{name} must contain three finite numeric values.")
    return vector


def _norm(vector: Vector3) -> float:
    return math.sqrt(sum(value * value for value in vector))


def _add(left: Vector3, right: Vector3) -> Vector3:
    return tuple(left[index] + right[index] for index in range(3))  # type: ignore[return-value]


def _sub(left: Vector3, right: Vector3) -> Vector3:
    return tuple(left[index] - right[index] for index in range(3))  # type: ignore[return-value]


def _dot(left: Vector3, right: Vector3) -> float:
    return sum(left[index] * right[index] for index in range(3))


def _cross(left: Vector3, right: Vector3) -> Vector3:
    return (
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    )


def _scale(vector: Vector3, factor: float) -> Vector3:
    return tuple(value * factor for value in vector)  # type: ignore[return-value]


def _unit(vector: Vector3, name: str) -> Vector3:
    magnitude = _norm(vector)
    if magnitude == 0.0:
        raise ValueError(f"{name} must be non-zero.")
    return _scale(vector, 1.0 / magnitude)


def flyby_turn_angle(
    *, gravitational_parameter_m3_s2: float, periapsis_radius_m: float, v_infinity_m_s: float
) -> float:
    """Return the unpowered hyperbolic-flyby turn angle in radians.

    The patched-conic relation is e = 1 + r_p*v_inf**2/mu and
    delta = 2*asin(1/e). Inputs use SI units.
    """
    values = (gravitational_parameter_m3_s2, periapsis_radius_m, v_infinity_m_s)
    if not all(math.isfinite(value) and value > 0.0 for value in values):
        raise ValueError("mu, periapsis radius, and v-infinity must be finite and positive.")
    eccentricity = 1.0 + periapsis_radius_m * v_infinity_m_s**2 / gravitational_parameter_m3_s2
    return 2.0 * math.asin(1.0 / eccentricity)


def compute_unpowered_gravity_assist(
    *,
    body: str,
    body_radius_m: float,
    gravitational_parameter_m3_s2: float,
    periapsis_altitude_m: float,
    v_infinity_in_m_s: Iterable[float],
    body_heliocentric_velocity_m_s: Iterable[float],
    turn_axis: Iterable[float],
    turn_direction: int,
) -> GravityAssistResult:
    """Rotate an incoming v-infinity vector without changing its body-frame energy."""
    if turn_direction not in (-1, 1):
        raise ValueError("turn_direction must be either -1 or +1.")
    if body_radius_m <= 0.0 or periapsis_altitude_m < 0.0:
        raise ValueError("body radius must be positive and periapsis altitude non-negative.")

    incoming = _vector(v_infinity_in_m_s, "v_infinity_in_m_s")
    body_velocity = _vector(body_heliocentric_velocity_m_s, "body_heliocentric_velocity_m_s")
    axis = _unit(_vector(turn_axis, "turn_axis"), "turn_axis")
    incoming_magnitude = _norm(incoming)
    if incoming_magnitude == 0.0:
        raise ValueError("v_infinity_in_m_s must be non-zero.")
    if abs(_dot(axis, incoming)) > 1e-12 * incoming_magnitude:
        raise ValueError("turn_axis must be perpendicular to v_infinity_in_m_s.")

    periapsis_radius = body_radius_m + periapsis_altitude_m
    turn_angle = flyby_turn_angle(
        gravitational_parameter_m3_s2=gravitational_parameter_m3_s2,
        periapsis_radius_m=periapsis_radius,
        v_infinity_m_s=incoming_magnitude,
    )
    signed_angle = turn_direction * turn_angle
    cosine = math.cos(signed_angle)
    sine = math.sin(signed_angle)
    # Rodrigues' formula; the final term is zero because the flyby-plane normal
    # is explicitly required to be perpendicular to the incoming asymptote.
    outgoing = _add(_scale(incoming, cosine), _scale(_cross(axis, incoming), sine))
    heliocentric_in = _add(body_velocity, incoming)
    heliocentric_out = _add(body_velocity, outgoing)
    speed_in = _norm(heliocentric_in)
    speed_out = _norm(heliocentric_out)

    return GravityAssistResult(
        body=body,
        periapsis_altitude_m=periapsis_altitude_m,
        periapsis_radius_m=periapsis_radius,
        turn_angle_rad=turn_angle,
        v_infinity_in_m_s=incoming,
        v_infinity_out_m_s=outgoing,
        v_infinity_magnitude_m_s=incoming_magnitude,
        body_heliocentric_velocity_m_s=body_velocity,
        heliocentric_velocity_in_m_s=heliocentric_in,
        heliocentric_velocity_out_m_s=heliocentric_out,
        heliocentric_speed_in_m_s=speed_in,
        heliocentric_speed_out_m_s=speed_out,
        heliocentric_speed_change_m_s=speed_out - speed_in,
        turn_direction=turn_direction,
    )


def compute_venus_flyby_demonstration() -> GravityAssistResult:
    """Build one fixed Earth-to-Venus Lambert arrival and its best planar turn."""
    earth = pk.planet(pk.udpla.jpl_lp("earth"))
    venus = pk.planet(pk.udpla.jpl_lp("venus"))
    departure = pk.epoch(DEMO_EARTH_DEPARTURE)
    arrival = pk.epoch(DEMO_VENUS_ARRIVAL)
    earth_position, _ = earth.eph(departure.mjd2000)
    venus_position, venus_velocity_raw = venus.eph(arrival.mjd2000)
    tof_seconds = (arrival.mjd2000 - departure.mjd2000) * 86_400.0
    lambert = pk.lambert_problem(
        earth_position,
        venus_position,
        tof_seconds,
        earth.get_mu_central_body(),
        multi_revs=0,
    )
    transfer_arrival = _vector(lambert.v1[0], "Lambert arrival velocity")
    venus_velocity = _vector(venus_velocity_raw, "Venus heliocentric velocity")
    incoming = _sub(transfer_arrival, venus_velocity)

    # This plane contains both v-infinity and Venus's heliocentric velocity. Of
    # its two possible unpowered turns, retain the one increasing solar-frame speed.
    turn_axis = _unit(_cross(incoming, venus_velocity), "demonstration turn plane")
    candidates = tuple(
        compute_unpowered_gravity_assist(
            body="Venus",
            body_radius_m=venus.get_radius(),
            gravitational_parameter_m3_s2=venus.get_mu_self(),
            periapsis_altitude_m=DEMO_VENUS_FLYBY_ALTITUDE_M,
            v_infinity_in_m_s=incoming,
            body_heliocentric_velocity_m_s=venus_velocity,
            turn_axis=turn_axis,
            turn_direction=direction,
        )
        for direction in (-1, 1)
    )
    return max(
        candidates,
        key=lambda result: (result.heliocentric_speed_change_m_s, result.turn_direction),
    )
