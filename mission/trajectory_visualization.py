"""Pure trajectory-scene geometry built from existing mission results."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import pykep as pk

from .bodies import CelestialBody, resolve_body
from .full_mission import EarthSaturnTitanMissionResult

SECONDS_PER_DAY = 86_400.0
METRES_PER_KILOMETRE = 1_000.0
MINIMUM_SAMPLES = 24


@dataclass(frozen=True)
class TrajectoryCurve3D:
    """One named curve in a declared reference frame and display unit."""

    name: str
    frame: str
    unit: str
    x: tuple[float, ...]
    y: tuple[float, ...]
    z: tuple[float, ...]
    role: str

    def __post_init__(self) -> None:
        if not self.name or not self.frame or not self.unit or not self.role:
            raise ValueError("Curve metadata must not be empty.")
        if not self.x or len(self.x) != len(self.y) or len(self.x) != len(self.z):
            raise ValueError("Curve coordinates must be non-empty and have equal lengths.")
        if not all(math.isfinite(value) for values in (self.x, self.y, self.z) for value in values):
            raise ValueError("Curve coordinates must be finite.")


@dataclass(frozen=True)
class CompleteMissionScene3D:
    """Two-scale scene for the heliocentric and Saturn-centred mission phases."""

    heliocentric_curves: tuple[TrajectoryCurve3D, ...]
    saturn_curves: tuple[TrajectoryCurve3D, ...]
    notes: tuple[str, ...]


@dataclass(frozen=True)
class MissionAnimationTimeline3D:
    """Pre-sampled spacecraft paths and durations used by the UI animation."""

    earth_saturn_duration_days: float
    saturn_staging_duration_days: float
    saturn_titan_duration_days: float
    earth_saturn_points: tuple[tuple[float, float, float], ...]
    saturn_staging_points: tuple[tuple[float, float, float], ...]
    saturn_titan_points: tuple[tuple[float, float, float], ...]

    def __post_init__(self) -> None:
        durations = (
            self.earth_saturn_duration_days,
            self.saturn_staging_duration_days,
            self.saturn_titan_duration_days,
        )
        if not all(math.isfinite(duration) and duration > 0.0 for duration in durations):
            raise ValueError("Animation phase durations must be finite and positive.")
        paths = (
            self.earth_saturn_points,
            self.saturn_staging_points,
            self.saturn_titan_points,
        )
        if not all(len(path) >= 2 for path in paths):
            raise ValueError("Animation paths must contain at least two points.")
        if not all(math.isfinite(value) for path in paths for point in path for value in point):
            raise ValueError("Animation path coordinates must be finite.")

    @property
    def total_duration_days(self) -> float:
        return (
            self.earth_saturn_duration_days
            + self.saturn_staging_duration_days
            + self.saturn_titan_duration_days
        )


@dataclass(frozen=True)
class SpacecraftPosition3D:
    """One interpolated spacecraft position in the active display frame."""

    elapsed_days: float
    total_duration_days: float
    phase_name: str
    frame: str
    x: float
    y: float
    z: float


def _validate_samples(samples: int) -> int:
    if isinstance(samples, bool) or not isinstance(samples, int):
        raise TypeError("samples must be an integer.")
    if samples < MINIMUM_SAMPLES:
        raise ValueError(f"samples must be at least {MINIMUM_SAMPLES}.")
    return samples


def _vector3(values: Sequence[float]) -> tuple[float, float, float]:
    try:
        return (float(values[0]), float(values[1]), float(values[2]))
    except (IndexError, TypeError) as error:
        raise ValueError("PyKEP state vectors must contain three components.") from error


def _scaled_curve(
    name: str,
    frame: str,
    unit: str,
    points: list[tuple[float, float, float]],
    scale: float,
    role: str,
) -> TrajectoryCurve3D:
    return TrajectoryCurve3D(
        name=name,
        frame=frame,
        unit=unit,
        x=tuple(point[0] / scale for point in points),
        y=tuple(point[1] / scale for point in points),
        z=tuple(point[2] / scale for point in points),
        role=role,
    )


def _sample_body_orbit(
    body: CelestialBody,
    start_mjd2000: float,
    samples: int,
) -> list[tuple[float, float, float]]:
    if body.pykep_body is None:
        raise ValueError(f"{body.name} does not expose a PyKEP ephemeris.")
    period_s = float(body.pykep_body.period())
    position, velocity = body.eph(start_mjd2000)
    mu_central = body.get_mu_central_body()
    points: list[tuple[float, float, float]] = []
    for index in range(samples):
        elapsed_s = period_s * index / (samples - 1)
        propagated_position, _ = pk.propagate_lagrangian(
            [position, velocity], elapsed_s, mu_central
        )
        points.append(_vector3(propagated_position))
    return points


def _sample_lambert_arc(
    departure_mjd2000: float,
    arrival_mjd2000: float,
    samples: int,
) -> list[tuple[float, float, float]]:
    earth = resolve_body("Earth")
    saturn = resolve_body("Saturn")
    departure_position, _ = earth.eph(departure_mjd2000)
    arrival_position, _ = saturn.eph(arrival_mjd2000)
    time_of_flight_s = (arrival_mjd2000 - departure_mjd2000) * SECONDS_PER_DAY
    if time_of_flight_s <= 0.0:
        raise ValueError("Earth-to-Saturn arrival must follow departure.")

    mu_sun = earth.get_mu_central_body()
    solution = pk.lambert_problem(
        departure_position,
        arrival_position,
        time_of_flight_s,
        mu_sun,
        cw=False,
        multi_revs=0,
    )
    departure_velocity = solution.v0[0]
    points: list[tuple[float, float, float]] = []
    for index in range(samples):
        elapsed_s = time_of_flight_s * index / (samples - 1)
        position, _ = pk.propagate_lagrangian(
            [departure_position, departure_velocity], elapsed_s, mu_sun
        )
        points.append(_vector3(position))
    points[0] = _vector3(departure_position)
    points[-1] = _vector3(arrival_position)
    return points


def _sample_circle(radius_m: float, samples: int) -> list[tuple[float, float, float]]:
    return [
        (
            radius_m * math.cos(2.0 * math.pi * index / (samples - 1)),
            radius_m * math.sin(2.0 * math.pi * index / (samples - 1)),
            0.0,
        )
        for index in range(samples)
    ]


def _sample_focus_ellipse(
    periapsis_radius_m: float,
    apoapsis_radius_m: float,
    samples: int,
    *,
    half_orbit: bool,
) -> list[tuple[float, float, float]]:
    semimajor_axis = (periapsis_radius_m + apoapsis_radius_m) / 2.0
    eccentricity = (apoapsis_radius_m - periapsis_radius_m) / (
        apoapsis_radius_m + periapsis_radius_m
    )
    semilatus_rectum = semimajor_axis * (1.0 - eccentricity**2)
    if half_orbit:
        angles = [math.pi * index / (samples - 1) for index in range(samples)]
    else:
        first_half_count = samples // 2 + 1
        second_half_count = samples - first_half_count
        angles = [math.pi * index / (first_half_count - 1) for index in range(first_half_count)]
        angles.extend(
            math.pi + math.pi * (index + 1) / second_half_count
            for index in range(second_half_count)
        )
    points: list[tuple[float, float, float]] = []
    for angle in angles:
        radius = semilatus_rectum / (1.0 + eccentricity * math.cos(angle))
        points.append((radius * math.cos(angle), radius * math.sin(angle), 0.0))
    return points


def _curve_points(curve: TrajectoryCurve3D) -> tuple[tuple[float, float, float], ...]:
    return tuple(zip(curve.x, curve.y, curve.z, strict=True))


def _find_curve(
    curves: tuple[TrajectoryCurve3D, ...],
    name: str,
) -> TrajectoryCurve3D:
    try:
        return next(curve for curve in curves if curve.name == name)
    except StopIteration as error:
        raise ValueError(f"Scene is missing required animation curve: {name}.") from error


def build_mission_animation_timeline(
    scene: CompleteMissionScene3D,
    mission_result: EarthSaturnTitanMissionResult,
) -> MissionAnimationTimeline3D:
    """Reuse scene samples to build a timeline without any new ephemeris call."""
    if not isinstance(scene, CompleteMissionScene3D):
        raise TypeError("scene must be a CompleteMissionScene3D.")
    if not isinstance(mission_result, EarthSaturnTitanMissionResult):
        raise TypeError("mission_result must be an EarthSaturnTitanMissionResult.")

    earth_saturn_trajectory = mission_result.mission.legs[0].trajectory
    if (
        earth_saturn_trajectory is None
        or earth_saturn_trajectory.departure_mjd2000 is None
        or earth_saturn_trajectory.arrival_mjd2000 is None
    ):
        raise ValueError("Earth-to-Saturn timing is required for animation.")
    earth_saturn_duration_days = float(earth_saturn_trajectory.arrival_mjd2000) - float(
        earth_saturn_trajectory.departure_mjd2000
    )

    lambert = _find_curve(scene.heliocentric_curves, "Earth → Saturn Lambert transfer")
    arrival_ellipse = _find_curve(scene.saturn_curves, "Saturn arrival ellipse")
    titan_transfer = _find_curve(scene.saturn_curves, "Saturn → Titan transfer")
    arrival_points = _curve_points(arrival_ellipse)
    first_half_count = len(arrival_points) // 2 + 1

    return MissionAnimationTimeline3D(
        earth_saturn_duration_days=earth_saturn_duration_days,
        saturn_staging_duration_days=(
            mission_result.saturn_arrival_staging.time_of_flight_s / SECONDS_PER_DAY
        ),
        saturn_titan_duration_days=(
            mission_result.saturn_titan_transfer.time_of_flight_s / SECONDS_PER_DAY
        ),
        earth_saturn_points=_curve_points(lambert),
        saturn_staging_points=arrival_points[:first_half_count],
        saturn_titan_points=_curve_points(titan_transfer),
    )


def _interpolate_points(
    points: tuple[tuple[float, float, float], ...],
    progress: float,
) -> tuple[float, float, float]:
    if progress <= 0.0:
        return points[0]
    if progress >= 1.0:
        return points[-1]
    fractional_index = progress * (len(points) - 1)
    lower_index = math.floor(fractional_index)
    upper_index = min(lower_index + 1, len(points) - 1)
    fraction = fractional_index - lower_index
    lower = points[lower_index]
    upper = points[upper_index]
    return (
        lower[0] + fraction * (upper[0] - lower[0]),
        lower[1] + fraction * (upper[1] - lower[1]),
        lower[2] + fraction * (upper[2] - lower[2]),
    )


def interpolate_spacecraft_position(
    timeline: MissionAnimationTimeline3D,
    elapsed_days: float,
) -> SpacecraftPosition3D:
    """Interpolate one marker position from pre-sampled display coordinates."""
    if not isinstance(timeline, MissionAnimationTimeline3D):
        raise TypeError("timeline must be a MissionAnimationTimeline3D.")
    if isinstance(elapsed_days, bool) or not isinstance(elapsed_days, int | float):
        raise TypeError("elapsed_days must be a real number.")
    elapsed = float(elapsed_days)
    total = timeline.total_duration_days
    if not math.isfinite(elapsed) or elapsed < 0.0 or elapsed > total:
        raise ValueError("elapsed_days must be within the mission timeline.")

    earth_end = timeline.earth_saturn_duration_days
    staging_end = earth_end + timeline.saturn_staging_duration_days
    if elapsed < earth_end:
        phase_name = "Earth → Saturn transfer"
        frame = "heliocentric"
        points = timeline.earth_saturn_points
        progress = elapsed / timeline.earth_saturn_duration_days
    elif elapsed < staging_end:
        phase_name = "Saturn arrival → staging"
        frame = "saturn_centred"
        points = timeline.saturn_staging_points
        progress = (elapsed - earth_end) / timeline.saturn_staging_duration_days
    else:
        phase_name = "Saturn → Titan transfer"
        frame = "saturn_centred"
        points = timeline.saturn_titan_points
        progress = (elapsed - staging_end) / timeline.saturn_titan_duration_days

    x, y, z = _interpolate_points(points, progress)
    return SpacecraftPosition3D(
        elapsed_days=elapsed,
        total_duration_days=total,
        phase_name=phase_name,
        frame=frame,
        x=x,
        y=y,
        z=z,
    )


def build_complete_mission_scene(
    mission_result: EarthSaturnTitanMissionResult,
    *,
    samples: int = 160,
) -> CompleteMissionScene3D:
    """Build display geometry without changing any trajectory result or equation."""
    if not isinstance(mission_result, EarthSaturnTitanMissionResult):
        raise TypeError("mission_result must be an EarthSaturnTitanMissionResult.")
    samples = _validate_samples(samples)

    earth_saturn_leg = mission_result.mission.legs[0]
    trajectory = earth_saturn_leg.trajectory
    if (
        trajectory is None
        or trajectory.departure_mjd2000 is None
        or trajectory.arrival_mjd2000 is None
    ):
        raise ValueError("Earth-to-Saturn leg must expose departure and arrival epochs.")
    departure_epoch = float(trajectory.departure_mjd2000)
    arrival_epoch = float(trajectory.arrival_mjd2000)

    earth = resolve_body("Earth")
    saturn = resolve_body("Saturn")
    heliocentric = (
        _scaled_curve(
            "Earth orbit",
            "Sun-centred J2000 ecliptic",
            "AU",
            _sample_body_orbit(earth, departure_epoch, samples),
            pk.AU,
            "planet_orbit",
        ),
        _scaled_curve(
            "Earth → Saturn Lambert transfer",
            "Sun-centred J2000 ecliptic",
            "AU",
            _sample_lambert_arc(departure_epoch, arrival_epoch, samples),
            pk.AU,
            "spacecraft_transfer",
        ),
        _scaled_curve(
            "Saturn orbit",
            "Sun-centred J2000 ecliptic",
            "AU",
            _sample_body_orbit(saturn, arrival_epoch, samples),
            pk.AU,
            "planet_orbit",
        ),
    )

    staging = mission_result.saturn_arrival_staging
    titan = mission_result.saturn_titan_transfer
    saturn_centred = (
        _scaled_curve(
            "Saturn arrival ellipse",
            "Saturn-centred coplanar model",
            "km",
            _sample_focus_ellipse(
                staging.periapsis_radius_m,
                staging.staging_radius_m,
                samples,
                half_orbit=False,
            ),
            METRES_PER_KILOMETRE,
            "capture_orbit",
        ),
        _scaled_curve(
            "Saturn staging orbit",
            "Saturn-centred coplanar model",
            "km",
            _sample_circle(staging.staging_radius_m, samples),
            METRES_PER_KILOMETRE,
            "staging_orbit",
        ),
        _scaled_curve(
            "Saturn → Titan transfer",
            "Saturn-centred coplanar model",
            "km",
            _sample_focus_ellipse(
                titan.saturn_staging_radius_m,
                titan.titan_orbit_radius_m,
                samples,
                half_orbit=True,
            ),
            METRES_PER_KILOMETRE,
            "spacecraft_transfer",
        ),
        _scaled_curve(
            "Titan orbit",
            "Saturn-centred coplanar model",
            "km",
            _sample_circle(titan.titan_orbit_radius_m, samples),
            METRES_PER_KILOMETRE,
            "moon_orbit",
        ),
    )
    return CompleteMissionScene3D(
        heliocentric_curves=heliocentric,
        saturn_curves=saturn_centred,
        notes=(
            "The two panels use different scales and reference frames.",
            "Planet and moon physical sizes are not shown to scale.",
            "The Saturn-centred panel is coplanar because the underlying preliminary models are.",
        ),
    )
