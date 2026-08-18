from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass

import pykep as pk

from . import physics

Vector3 = tuple[float, float, float]

TURN_ANGLE_SOURCE = (
    "NASA NTRS 20170005667, patched-conic gravity-assist geometry: "
    "https://ntrs.nasa.gov/api/citations/20170005667/downloads/20170005667.pdf"
)

# Fixed epochs make this scientific demonstration reproducible. They cover
# Cassini's real VVEJGA (Venus-Venus-Earth-Jupiter gravity assist) tour from
# Earth departure through Saturn orbit insertion; this module does not
# reproduce or optimize the tour, only its documented dates/altitudes.
DEMO_EARTH_DEPARTURE = "1997-10-15 08:43:00"
DEMO_VENUS_ARRIVAL = "1998-04-26 13:44:00"
DEMO_SECOND_VENUS_FLYBY = "1999-06-24 20:30:00"
DEMO_EARTH_FLYBY = "1999-08-18 03:28:00"
DEMO_JUPITER_FLYBY = "2000-12-30 10:05:00"
# Saturn Orbit Insertion (SOI): the main-engine burn began 2004-07-01 01:12 UTC
# (ESA Cassini-Huygens Science Portal status report - see SOI_SOURCE below);
# used here as the arrival epoch for the Jupiter -> Saturn Lambert arc feeding
# the capture burn.
DEMO_SATURN_ARRIVAL = "2004-07-01 01:12:00"

FIRST_VENUS_ALTITUDE_SOURCE = (
    "NASA Cassini mission timeline: the first Venus flyby passed about 284 km "
    "(176 miles) above Venus: https://science.nasa.gov/mission/cassini/the-journey/timeline/"
)
SECOND_VENUS_ALTITUDE_SOURCE = (
    "NASA Cassini mission timeline: the second Venus flyby passed about 600 km "
    "above Venus: https://science.nasa.gov/mission/cassini/the-journey/timeline/"
)
EARTH_ALTITUDE_SOURCE = (
    "NASA JPL, Cassini successfully completes flyby of Earth: closest-approach altitude "
    "about 1,171 km: https://www.jpl.nasa.gov/news/cassini-successfully-completes-flyby-of-earth/"
)
JUPITER_ALTITUDE_SOURCE = (
    "NASA JPL DESCANSO Cassini Navigation Performance Assessment: Jupiter periapsis "
    "altitude 9,722,965 km: https://descanso.jpl.nasa.gov/DPSummary/DESCANSO17_Cassini_RevA.pdf"
)
SOI_SOURCE = (
    "NASA JPL, Cassini Spacecraft At Saturn's Doorstep: periapsis about 20,000 km "
    "above Saturn's cloud tops, 96-minute burn, 626 m/s delta-v, insertion beginning "
    "2004-07-01 01:12 UTC: https://www.jpl.nasa.gov/news/cassini-spacecraft-at-saturns-doorstep/ "
    "- cross-checked against the ESA Cassini-Huygens Science Portal's 80,230 km "
    "from-Saturn's-center periapsis radius: "
    "https://sci.esa.int/web/cassini-huygens/-/34955-approach-and-arrival"
)

DEMO_FIRST_VENUS_FLYBY_ALTITUDE_M = 284_000.0
DEMO_SECOND_VENUS_FLYBY_ALTITUDE_M = 600_000.0
DEMO_EARTH_FLYBY_ALTITUDE_M = 1_171_000.0
DEMO_JUPITER_FLYBY_ALTITUDE_M = 9_722_965_000.0
# ~20,000 km above the cloud tops (SOI_SOURCE). Combined with Saturn's ~60,268 km
# equatorial radius this gives a periapsis radius close to the 80,230 km the ESA
# source states directly, so either figure is consistent with the other.
CASSINI_SOI_PERIAPSIS_ALTITUDE_M = 20_000_000.0


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


@dataclass(frozen=True)
class OrbitInsertionResult:
    """A propulsive orbit-insertion burn from an incoming hyperbola into a captured orbit.

    Unlike GravityAssistResult (an unpowered flyby that conserves body-frame
    energy - the whole point of a gravity assist), this maneuver costs real
    propulsive delta-v. Modeled with the same single-impulse capture formula
    (physics.delta_v_capture) trajectory.py already applies at every other
    planetary arrival: a known simplification of Cassini's real capture into
    an eccentric orbit (not a circular one), consistent with the same
    simplification already made throughout this file and in trajectory.py's
    own Saturn-arrival budget term - not a new one introduced here.
    """

    body: str
    v_infinity_in_m_s: Vector3
    v_infinity_magnitude_m_s: float
    periapsis_altitude_m: float
    periapsis_radius_m: float
    delta_v_m_s: float
    method: str = "impulsive_capture_at_periapsis"


@dataclass(frozen=True)
class MissionSegment:
    """One leg of the historical Cassini-style gravity-assist tour.

    `result` is a GravityAssistResult (unpowered flyby) for every interior
    body, or an OrbitInsertionResult (the propulsive Saturn Orbit Insertion)
    for the final leg.
    """

    name: str
    departure_body: str
    departure_epoch_mjd2000: float
    departure_position_m: Vector3
    # Heliocentric v-infinity of the Lambert departure relative to the
    # departure body - e.g. for the first segment, the real Earth-departure
    # hyperbolic excess speed a launch-injection delta-v is computed from.
    departure_v_infinity_m_s: Vector3
    arrival_body: str
    arrival_epoch_mjd2000: float
    arrival_position_m: Vector3
    result: GravityAssistResult | OrbitInsertionResult


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


@dataclass(frozen=True)
class _FlybyLegSolution:
    """Everything a Lambert leg + best-turn flyby computes, for internal reuse."""

    departure_position_m: Vector3
    departure_epoch_mjd2000: float
    departure_v_infinity_m_s: Vector3
    arrival_position_m: Vector3
    arrival_epoch_mjd2000: float
    result: GravityAssistResult


def _solve_flyby_leg(
    *,
    departure_planet_name: str,
    arrival_planet_name: str,
    departure_epoch: str,
    arrival_epoch: str,
    arrival_body_label: str,
    periapsis_altitude_m: float,
) -> _FlybyLegSolution:
    """Solve one heliocentric two-body Lambert arc and its best-turn flyby at arrival.

    The shared primitive behind every compute_*_flyby_demonstration function
    below and compute_cassini_historical_tour(): the Lambert arc and its
    resulting flyby turn geometry are computed exactly once per leg, never
    duplicated between an individual demonstration and the chained tour.

    "Best turn" mirrors the existing functions' own choice: of the two
    possible unpowered turns for a given periapsis, retain the one that
    increases solar-frame (heliocentric) speed.
    """
    departure_planet = pk.planet(pk.udpla.jpl_lp(departure_planet_name))
    arrival_planet = pk.planet(pk.udpla.jpl_lp(arrival_planet_name))
    departure = pk.epoch(departure_epoch)
    arrival = pk.epoch(arrival_epoch)
    departure_position_raw, departure_body_velocity_raw = departure_planet.eph(departure.mjd2000)
    arrival_position_raw, arrival_velocity_raw = arrival_planet.eph(arrival.mjd2000)
    tof_seconds = (arrival.mjd2000 - departure.mjd2000) * 86_400.0
    lambert = pk.lambert_problem(
        departure_position_raw,
        arrival_position_raw,
        tof_seconds,
        departure_planet.get_mu_central_body(),
        multi_revs=0,
    )
    transfer_departure = _vector(lambert.v0[0], "Lambert departure velocity")
    transfer_arrival = _vector(lambert.v1[0], "Lambert arrival velocity")
    departure_body_velocity = _vector(
        departure_body_velocity_raw, "departure body heliocentric velocity"
    )
    arrival_velocity = _vector(arrival_velocity_raw, "arrival body heliocentric velocity")
    departure_position = _vector(departure_position_raw, "departure body heliocentric position")
    arrival_position = _vector(arrival_position_raw, "arrival body heliocentric position")

    departure_v_infinity = _sub(transfer_departure, departure_body_velocity)
    incoming = _sub(transfer_arrival, arrival_velocity)

    # This plane contains both v-infinity and the arrival body's heliocentric
    # velocity. Of its two possible unpowered turns, retain the one increasing
    # solar-frame speed.
    turn_axis = _unit(_cross(incoming, arrival_velocity), "demonstration turn plane")
    candidates = tuple(
        compute_unpowered_gravity_assist(
            body=arrival_body_label,
            body_radius_m=arrival_planet.get_radius(),
            gravitational_parameter_m3_s2=arrival_planet.get_mu_self(),
            periapsis_altitude_m=periapsis_altitude_m,
            v_infinity_in_m_s=incoming,
            body_heliocentric_velocity_m_s=arrival_velocity,
            turn_axis=turn_axis,
            turn_direction=direction,
        )
        for direction in (-1, 1)
    )
    best = max(
        candidates,
        key=lambda result: (result.heliocentric_speed_change_m_s, result.turn_direction),
    )

    return _FlybyLegSolution(
        departure_position_m=departure_position,
        departure_epoch_mjd2000=departure.mjd2000,
        departure_v_infinity_m_s=departure_v_infinity,
        arrival_position_m=arrival_position,
        arrival_epoch_mjd2000=arrival.mjd2000,
        result=best,
    )


def compute_venus_flyby_demonstration() -> GravityAssistResult:
    """Build one fixed Earth-to-Venus Lambert arrival and its best planar turn."""
    return _solve_flyby_leg(
        departure_planet_name="earth",
        arrival_planet_name="venus",
        departure_epoch=DEMO_EARTH_DEPARTURE,
        arrival_epoch=DEMO_VENUS_ARRIVAL,
        arrival_body_label="Venus",
        periapsis_altitude_m=DEMO_FIRST_VENUS_FLYBY_ALTITUDE_M,
    ).result


def compute_second_venus_flyby_demonstration() -> GravityAssistResult:
    """Build the fixed first-Venus-to-second-Venus Lambert arrival and planar turn.

    Cassini executed a deep-space maneuver (DSM) in early December 1998
    between the two Venus flybys; like every other segment in this file, this
    models the leg as a single two-body Lambert arc between the two flyby
    dates and ignores that DSM - a simplification consistent with (not new
    relative to) the rest of the file, none of whose segments include an
    intermediate maneuver either.
    """
    return _solve_flyby_leg(
        departure_planet_name="venus",
        arrival_planet_name="venus",
        departure_epoch=DEMO_VENUS_ARRIVAL,
        arrival_epoch=DEMO_SECOND_VENUS_FLYBY,
        arrival_body_label="Venus",
        periapsis_altitude_m=DEMO_SECOND_VENUS_FLYBY_ALTITUDE_M,
    ).result


def compute_earth_flyby_demonstration() -> GravityAssistResult:
    """Build one fixed second-Venus-to-Earth Lambert arrival and planar turn."""
    return _solve_flyby_leg(
        departure_planet_name="venus",
        arrival_planet_name="earth",
        departure_epoch=DEMO_SECOND_VENUS_FLYBY,
        arrival_epoch=DEMO_EARTH_FLYBY,
        arrival_body_label="Earth",
        periapsis_altitude_m=DEMO_EARTH_FLYBY_ALTITUDE_M,
    ).result


def compute_jupiter_flyby_demonstration() -> GravityAssistResult:
    """Build one fixed Earth-to-Jupiter Lambert arrival and distant planar turn."""
    return _solve_flyby_leg(
        departure_planet_name="earth",
        arrival_planet_name="jupiter",
        departure_epoch=DEMO_EARTH_FLYBY,
        arrival_epoch=DEMO_JUPITER_FLYBY,
        arrival_body_label="Jupiter",
        periapsis_altitude_m=DEMO_JUPITER_FLYBY_ALTITUDE_M,
    ).result


@dataclass(frozen=True)
class _OrbitInsertionLegSolution:
    """Everything the Jupiter -> Saturn Lambert arc + SOI capture computes, for internal reuse."""

    departure_position_m: Vector3
    departure_epoch_mjd2000: float
    departure_v_infinity_m_s: Vector3
    arrival_position_m: Vector3
    arrival_epoch_mjd2000: float
    result: OrbitInsertionResult


def _solve_saturn_orbit_insertion_leg() -> _OrbitInsertionLegSolution:
    """Solve the fixed Jupiter-to-Saturn Lambert arrival and its propulsive SOI capture."""
    jupiter = pk.planet(pk.udpla.jpl_lp("jupiter"))
    saturn = pk.planet(pk.udpla.jpl_lp("saturn"))
    departure = pk.epoch(DEMO_JUPITER_FLYBY)
    arrival = pk.epoch(DEMO_SATURN_ARRIVAL)
    jupiter_position_raw, jupiter_velocity_raw = jupiter.eph(departure.mjd2000)
    saturn_position_raw, saturn_velocity_raw = saturn.eph(arrival.mjd2000)
    tof_seconds = (arrival.mjd2000 - departure.mjd2000) * 86_400.0
    lambert = pk.lambert_problem(
        jupiter_position_raw,
        saturn_position_raw,
        tof_seconds,
        jupiter.get_mu_central_body(),
        multi_revs=0,
    )
    transfer_departure = _vector(lambert.v0[0], "Lambert departure velocity")
    transfer_arrival = _vector(lambert.v1[0], "Lambert arrival velocity")
    jupiter_velocity = _vector(jupiter_velocity_raw, "Jupiter heliocentric velocity")
    saturn_velocity = _vector(saturn_velocity_raw, "Saturn heliocentric velocity")
    jupiter_position = _vector(jupiter_position_raw, "Jupiter heliocentric position")
    saturn_position = _vector(saturn_position_raw, "Saturn heliocentric position")
    departure_v_infinity = _sub(transfer_departure, jupiter_velocity)
    incoming = _sub(transfer_arrival, saturn_velocity)
    v_infinity_magnitude = _norm(incoming)

    periapsis_radius = saturn.get_radius() + CASSINI_SOI_PERIAPSIS_ALTITUDE_M
    delta_v = physics.delta_v_capture(v_infinity_magnitude, saturn.get_mu_self(), periapsis_radius)

    result = OrbitInsertionResult(
        body="Saturn",
        v_infinity_in_m_s=incoming,
        v_infinity_magnitude_m_s=v_infinity_magnitude,
        periapsis_altitude_m=CASSINI_SOI_PERIAPSIS_ALTITUDE_M,
        periapsis_radius_m=periapsis_radius,
        delta_v_m_s=delta_v,
    )
    return _OrbitInsertionLegSolution(
        departure_position_m=jupiter_position,
        departure_epoch_mjd2000=departure.mjd2000,
        departure_v_infinity_m_s=departure_v_infinity,
        arrival_position_m=saturn_position,
        arrival_epoch_mjd2000=arrival.mjd2000,
        result=result,
    )


def compute_saturn_orbit_insertion() -> OrbitInsertionResult:
    """Build the fixed Jupiter-to-Saturn Lambert arrival and its propulsive SOI capture.

    Unlike the unpowered flybys above, Saturn Orbit Insertion (SOI) is a real
    propulsive maneuver: Cassini fired its main engine to capture from the
    incoming hyperbola into a bound orbit around Saturn. See SOI_SOURCE for
    the documented periapsis altitude, burn duration, and measured delta-v.
    """
    return _solve_saturn_orbit_insertion_leg().result


def compute_cassini_historical_tour() -> tuple[MissionSegment, ...]:
    """Chain the five real Cassini legs: Earth -> Venus -> Venus -> Earth -> Jupiter -> Saturn.

    Each leg reuses the same single Lambert-arc-plus-flyby (or, for the final
    leg, capture) computation as the corresponding compute_*_demonstration
    function above - nothing here is re-derived. Consecutive segments share
    their boundary epoch/body by construction (e.g. this chain's second
    segment departs at DEMO_VENUS_ARRIVAL, the same epoch the first segment
    arrives at), so each segment's arrival position exactly equals the next
    segment's departure position - see
    tests/test_cassini_historical_tour.py's continuity test, which checks
    this explicitly rather than assuming it.
    """
    venus_1 = _solve_flyby_leg(
        departure_planet_name="earth",
        arrival_planet_name="venus",
        departure_epoch=DEMO_EARTH_DEPARTURE,
        arrival_epoch=DEMO_VENUS_ARRIVAL,
        arrival_body_label="Venus",
        periapsis_altitude_m=DEMO_FIRST_VENUS_FLYBY_ALTITUDE_M,
    )
    venus_2 = _solve_flyby_leg(
        departure_planet_name="venus",
        arrival_planet_name="venus",
        departure_epoch=DEMO_VENUS_ARRIVAL,
        arrival_epoch=DEMO_SECOND_VENUS_FLYBY,
        arrival_body_label="Venus",
        periapsis_altitude_m=DEMO_SECOND_VENUS_FLYBY_ALTITUDE_M,
    )
    earth_2 = _solve_flyby_leg(
        departure_planet_name="venus",
        arrival_planet_name="earth",
        departure_epoch=DEMO_SECOND_VENUS_FLYBY,
        arrival_epoch=DEMO_EARTH_FLYBY,
        arrival_body_label="Earth",
        periapsis_altitude_m=DEMO_EARTH_FLYBY_ALTITUDE_M,
    )
    jupiter_1 = _solve_flyby_leg(
        departure_planet_name="earth",
        arrival_planet_name="jupiter",
        departure_epoch=DEMO_EARTH_FLYBY,
        arrival_epoch=DEMO_JUPITER_FLYBY,
        arrival_body_label="Jupiter",
        periapsis_altitude_m=DEMO_JUPITER_FLYBY_ALTITUDE_M,
    )
    soi = _solve_saturn_orbit_insertion_leg()

    return (
        MissionSegment(
            name="Earth -> Venus (first flyby)",
            departure_body="Earth",
            departure_epoch_mjd2000=venus_1.departure_epoch_mjd2000,
            departure_position_m=venus_1.departure_position_m,
            departure_v_infinity_m_s=venus_1.departure_v_infinity_m_s,
            arrival_body="Venus",
            arrival_epoch_mjd2000=venus_1.arrival_epoch_mjd2000,
            arrival_position_m=venus_1.arrival_position_m,
            result=venus_1.result,
        ),
        MissionSegment(
            name="Venus -> Venus (second flyby)",
            departure_body="Venus",
            departure_epoch_mjd2000=venus_2.departure_epoch_mjd2000,
            departure_position_m=venus_2.departure_position_m,
            departure_v_infinity_m_s=venus_2.departure_v_infinity_m_s,
            arrival_body="Venus",
            arrival_epoch_mjd2000=venus_2.arrival_epoch_mjd2000,
            arrival_position_m=venus_2.arrival_position_m,
            result=venus_2.result,
        ),
        MissionSegment(
            name="Venus -> Earth (flyby)",
            departure_body="Venus",
            departure_epoch_mjd2000=earth_2.departure_epoch_mjd2000,
            departure_position_m=earth_2.departure_position_m,
            departure_v_infinity_m_s=earth_2.departure_v_infinity_m_s,
            arrival_body="Earth",
            arrival_epoch_mjd2000=earth_2.arrival_epoch_mjd2000,
            arrival_position_m=earth_2.arrival_position_m,
            result=earth_2.result,
        ),
        MissionSegment(
            name="Earth -> Jupiter (flyby)",
            departure_body="Earth",
            departure_epoch_mjd2000=jupiter_1.departure_epoch_mjd2000,
            departure_position_m=jupiter_1.departure_position_m,
            departure_v_infinity_m_s=jupiter_1.departure_v_infinity_m_s,
            arrival_body="Jupiter",
            arrival_epoch_mjd2000=jupiter_1.arrival_epoch_mjd2000,
            arrival_position_m=jupiter_1.arrival_position_m,
            result=jupiter_1.result,
        ),
        MissionSegment(
            name="Jupiter -> Saturn (orbit insertion)",
            departure_body="Jupiter",
            departure_epoch_mjd2000=soi.departure_epoch_mjd2000,
            departure_position_m=soi.departure_position_m,
            departure_v_infinity_m_s=soi.departure_v_infinity_m_s,
            arrival_body="Saturn",
            arrival_epoch_mjd2000=soi.arrival_epoch_mjd2000,
            arrival_position_m=soi.arrival_position_m,
            result=soi.result,
        ),
    )
