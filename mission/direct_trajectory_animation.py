"""Time samples for the already-solved direct Earth-to-Saturn trajectory."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pykep as pk

from .constants import ASTRONOMICAL_UNIT_M
from .launch_search_ephemeris import heliocentric_state
from .launch_search_models import SearchTrajectorySegment
from .models import TrajectoryResult

SECONDS_PER_DAY = 86_400.0
DEFAULT_BASELINE_FRAME_COUNT = 64
MAXIMUM_ANIMATION_FRAMES = 72
Vector3 = tuple[float, float, float]


@dataclass(frozen=True)
class DirectTrajectoryFrame3D:
    """One display instant in the heliocentric/AU scene."""

    epoch_mjd2000: float
    date_utc: str
    elapsed_days: float
    spacecraft_position_au: Vector3
    earth_position_au: Vector3
    saturn_position_au: Vector3


@dataclass(frozen=True)
class DirectTrajectoryTimeline3D:
    """Frames derived from one existing Lambert segment, never a new solve."""

    scenario_id: str
    reference_frame: str
    distance_unit: str
    interpolation_notice: str
    frames: tuple[DirectTrajectoryFrame3D, ...]

    def __post_init__(self) -> None:
        if self.reference_frame != "heliocentric" or self.distance_unit != "AU":
            raise ValueError("Direct animation is restricted to the heliocentric/AU scene.")
        if len(self.frames) < 2:
            raise ValueError("Direct animation requires at least two frames.")
        epochs = tuple(frame.epoch_mjd2000 for frame in self.frames)
        if any(later <= earlier for earlier, later in zip(epochs, epochs[1:])):
            raise ValueError("Animation frame dates must be strictly increasing.")

    @property
    def departure_mjd2000(self) -> float:
        return self.frames[0].epoch_mjd2000

    @property
    def arrival_mjd2000(self) -> float:
        return self.frames[-1].epoch_mjd2000


def _vector_au(values_m) -> Vector3:
    values = tuple(float(value) / ASTRONOMICAL_UNIT_M for value in values_m)
    if len(values) != 3 or not all(math.isfinite(value) for value in values):
        raise ValueError("Trajectory vectors must contain three finite values.")
    return values  # type: ignore[return-value]


def _format_utc(epoch_mjd2000: float) -> str:
    instant = datetime(2000, 1, 1, tzinfo=UTC) + timedelta(days=epoch_mjd2000)
    return instant.strftime("%Y-%m-%d %H:%M UTC")


def build_baseline_lambert_segment(
    trajectory: TrajectoryResult,
    *,
    frame_count: int = DEFAULT_BASELINE_FRAME_COUNT,
) -> SearchTrajectorySegment:
    """Propagate the retained solved state without resolving Lambert."""
    if not isinstance(trajectory, TrajectoryResult):
        raise TypeError("trajectory must be a TrajectoryResult.")
    if isinstance(frame_count, bool) or not 2 <= frame_count <= MAXIMUM_ANIMATION_FRAMES:
        raise ValueError(f"frame_count must be between 2 and {MAXIMUM_ANIMATION_FRAMES}.")
    required = (
        trajectory.departure_mjd2000,
        trajectory.arrival_mjd2000,
        trajectory.departure_position_m,
        trajectory.arrival_position_m,
        trajectory.transfer_departure_velocity_m_s,
        trajectory.central_mu_m3_s2,
    )
    if any(value is None for value in required):
        raise ValueError("The baseline Lambert result does not retain its solved state.")

    departure = float(trajectory.departure_mjd2000)
    arrival = float(trajectory.arrival_mjd2000)
    duration_s = (arrival - departure) * SECONDS_PER_DAY
    if duration_s <= 0.0:
        raise ValueError("Lambert arrival must follow departure.")
    points: list[Vector3] = []
    for index in range(frame_count):
        elapsed_s = duration_s * index / (frame_count - 1)
        if index == 0:
            position_m = trajectory.departure_position_m
        elif index == frame_count - 1:
            position_m = trajectory.arrival_position_m
        else:
            position_m, _ = pk.propagate_lagrangian(
                (
                    trajectory.departure_position_m,
                    trajectory.transfer_departure_velocity_m_s,
                ),
                elapsed_s,
                float(trajectory.central_mu_m3_s2),
            )
        points.append(_vector_au(position_m))
    return SearchTrajectorySegment(
        id="mission-setup-earth-saturn-lambert",
        name="Direct Earth → Saturn Lambert transfer",
        frame="heliocentric",
        unit="AU",
        x=tuple(point[0] for point in points),
        y=tuple(point[1] for point in points),
        z=tuple(point[2] for point in points),
        departure_mjd2000=departure,
        arrival_mjd2000=arrival,
    )


def build_connected_capture_segment(
    departure_mjd2000: float,
    arrival_mjd2000: float,
    periapsis_radius_m: float,
    apoapsis_radius_m: float,
    sample_count: int,
) -> SearchTrajectorySegment:
    """Sample the already-defined connected capture ellipse for display."""
    if isinstance(sample_count, bool) or sample_count < 2:
        raise ValueError("sample_count must be an integer of at least two.")
    axis = (periapsis_radius_m + apoapsis_radius_m) / 2.0
    eccentricity = (apoapsis_radius_m - periapsis_radius_m) / (
        apoapsis_radius_m + periapsis_radius_m
    )
    points = []
    for index in range(sample_count):
        anomaly = math.pi * index / (sample_count - 1)
        points.append(
            (
                axis * (math.cos(anomaly) - eccentricity) / 1_000.0,
                axis * math.sqrt(1.0 - eccentricity**2) * math.sin(anomaly) / 1_000.0,
                0.0,
            )
        )
    return SearchTrajectorySegment(
        id="saturn-capture-ellipse",
        name="Saturn capture ellipse to Titan orbital radius",
        frame="saturn_centred",
        unit="km",
        x=tuple(point[0] for point in points),
        y=tuple(point[1] for point in points),
        z=tuple(point[2] for point in points),
        departure_mjd2000=departure_mjd2000,
        arrival_mjd2000=arrival_mjd2000,
    )


def build_direct_trajectory_timeline(
    segment: SearchTrajectorySegment,
    *,
    scenario_id: str,
) -> DirectTrajectoryTimeline3D:
    """Attach dates and real planetary ephemerides to existing arc samples.

    Spacecraft coordinates are copied from the scientific segment. Playback can
    graphically interpolate between Plotly frames; it is not a new propagation.
    Earth and Saturn positions are evaluated from the project's existing JPL
    low-precision ephemeris at the same frame epochs.
    """
    if not isinstance(segment, SearchTrajectorySegment):
        raise TypeError("segment must be a SearchTrajectorySegment.")
    if segment.frame != "heliocentric" or segment.unit != "AU":
        raise ValueError("The animated segment must be heliocentric and expressed in AU.")
    if not scenario_id:
        raise ValueError("scenario_id must not be empty.")
    count = len(segment.x)
    frames: list[DirectTrajectoryFrame3D] = []
    for index, spacecraft in enumerate(zip(segment.x, segment.y, segment.z, strict=True)):
        progress = index / (count - 1)
        epoch = segment.departure_mjd2000 + progress * (
            segment.arrival_mjd2000 - segment.departure_mjd2000
        )
        earth_position_m, _ = heliocentric_state("Earth", epoch)
        saturn_position_m, _ = heliocentric_state("Saturn", epoch)
        frames.append(
            DirectTrajectoryFrame3D(
                epoch_mjd2000=epoch,
                date_utc=_format_utc(epoch),
                elapsed_days=epoch - segment.departure_mjd2000,
                spacecraft_position_au=tuple(float(value) for value in spacecraft),
                earth_position_au=_vector_au(earth_position_m),
                saturn_position_au=_vector_au(saturn_position_m),
            )
        )
    return DirectTrajectoryTimeline3D(
        scenario_id=scenario_id,
        reference_frame=segment.frame,
        distance_unit=segment.unit,
        interpolation_notice=(
            "Visualization playback between sampled Lambert-arc points is graphical "
            "interpolation, not an independent dynamical propagation."
        ),
        frames=tuple(frames),
    )
