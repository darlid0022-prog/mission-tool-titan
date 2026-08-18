"""Generic, reusable 3D trajectory-segment schema and adapters.

Separates *what to draw* (this module: a plain, ordered list of
`TrajectorySegment` records, each already carrying its own computed x/y/z
coordinates and display metadata) from *how to draw it*
(`mission/trajectory_plot.py`'s `build_scene_figure()`, which only ever
consumes this generic schema).

No Lambert solve, ephemeris sampling, or flyby geometry happens in this
module. Every adapter below only relabels, restyles, or re-slices
coordinates and results already computed by
`mission/trajectory_visualization.py` (heliocentric/Saturn-centred curves)
or `mission/gravity_assist.py` (the Cassini historical tour) - the same
separation of concerns `mission/trajectory_plot.py`'s existing figure
builders already follow, generalized into one reusable shape that does not
care whether the underlying mission was a direct Lambert transfer or a
chain of gravity-assist flybys.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from . import colors
from .bodies import resolve_body
from .constants import TITAN_MEAN_RADIUS_M
from .gravity_assist import GravityAssistResult, MissionSegment, OrbitInsertionResult
from .launch_search_models import SearchTrajectorySegment
from .trajectory_visualization import CompleteMissionScene3D, TrajectoryCurve3D

# --------------------------------------------------------------------------
# Generic schema
# --------------------------------------------------------------------------

Vector = tuple[float, ...]

SEGMENT_TYPE_TRANSFER = "transfer"
SEGMENT_TYPE_ORBIT_REFERENCE = "orbit_reference"
SEGMENT_TYPE_FLYBY = "flyby"
SEGMENT_TYPE_INSERTION = "insertion"
SEGMENT_TYPE_LANDMARK = "landmark"

SEGMENT_TYPES = (
    SEGMENT_TYPE_TRANSFER,
    SEGMENT_TYPE_ORBIT_REFERENCE,
    SEGMENT_TYPE_FLYBY,
    SEGMENT_TYPE_INSERTION,
    SEGMENT_TYPE_LANDMARK,
)


def segments_from_launch_search(
    segments: tuple[SearchTrajectorySegment, ...],
    *,
    reference_frame: str,
    distance_unit: str,
) -> tuple[TrajectorySegment, ...]:
    """Adapt one already-filtered launch-search scene without unit conversion."""
    if not segments:
        return ()
    if any(
        segment.frame != reference_frame or segment.unit != distance_unit
        for segment in segments
    ):
        raise ValueError(
            "Launch-search segments must share the requested reference frame and unit."
        )
    phase_color = (
        colors.INTERPLANETARY_TRANSFER.dark
        if reference_frame == "heliocentric"
        else colors.ARRIVAL.dark
    )
    segment_type = (
        SEGMENT_TYPE_TRANSFER
        if reference_frame == "heliocentric"
        else SEGMENT_TYPE_INSERTION
    )
    return tuple(
        TrajectorySegment(
            id=segment.id,
            name=segment.name,
            type=segment_type,
            origin_body="Earth" if reference_frame == "heliocentric" else "Saturn",
            destination_body="Saturn",
            x=segment.x,
            y=segment.y,
            z=segment.z,
            departure_date=_format_mjd2000(segment.departure_mjd2000),
            arrival_date=_format_mjd2000(segment.arrival_mjd2000),
            duration_days=segment.arrival_mjd2000 - segment.departure_mjd2000,
            style=SegmentStyle(
                color=phase_color,
                legend_group=reference_frame,
            ),
            metadata={
                "reference_frame": reference_frame,
                "distance_unit": distance_unit,
            },
        )
        for segment in segments
    )


@dataclass(frozen=True)
class SegmentStyle:
    """Display-only metadata - never a source of physical truth."""

    color: str
    width: int = 4
    dash: str = "solid"
    marker_size: int = 6
    legend_group: str | None = None

    def __post_init__(self) -> None:
        if not self.color or not str(self.color).strip():
            raise ValueError("SegmentStyle.color must be a non-empty string.")
        if self.width <= 0 or self.marker_size <= 0:
            raise ValueError("SegmentStyle.width and marker_size must be positive.")


@dataclass(frozen=True)
class TrajectorySegment:
    """One drawable piece of a mission: a curve (>=2 points) or a landmark (1 point).

    Coordinates are supplied pre-computed by the caller - ephemeris sampling,
    Lambert solving, and flyby geometry all happen upstream of this schema -
    and are assumed to already share one consistent reference frame and unit
    within a given figure (see `build_scene_figure`'s `unit_label`).
    """

    id: str
    name: str
    type: str
    origin_body: str
    destination_body: str
    x: Vector
    y: Vector
    z: Vector
    departure_date: str | None = None
    arrival_date: str | None = None
    duration_days: float | None = None
    delta_v_m_s: float | None = None
    style: SegmentStyle = field(default_factory=lambda: SegmentStyle(color=colors.REFERENCE_ORBIT))
    metadata: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id or not str(self.id).strip():
            raise ValueError("TrajectorySegment.id must be a non-empty string.")
        if not self.name or not str(self.name).strip():
            raise ValueError("TrajectorySegment.name must be a non-empty string.")
        if self.type not in SEGMENT_TYPES:
            raise ValueError(f"TrajectorySegment.type must be one of {SEGMENT_TYPES}.")
        if not self.origin_body or not str(self.origin_body).strip():
            raise ValueError("TrajectorySegment.origin_body must be a non-empty string.")
        if not self.destination_body or not str(self.destination_body).strip():
            raise ValueError("TrajectorySegment.destination_body must be a non-empty string.")
        if not self.x or len(self.x) != len(self.y) or len(self.x) != len(self.z):
            raise ValueError("x, y, and z must be non-empty and of equal length.")
        if not all(math.isfinite(value) for axis in (self.x, self.y, self.z) for value in axis):
            raise ValueError("x, y, and z must contain only finite values.")
        if self.duration_days is not None and self.duration_days < 0.0:
            raise ValueError("duration_days must be non-negative when provided.")
        if self.delta_v_m_s is not None and self.delta_v_m_s < 0.0:
            raise ValueError("delta_v_m_s must be non-negative when provided.")

    @property
    def is_point(self) -> bool:
        return len(self.x) == 1


def _format_mjd2000(epoch_mjd2000: float | None) -> str | None:
    """Format an already-known MJD2000 epoch as a date string.

    Pure formatting, not an ephemeris lookup: the epoch itself was already
    computed upstream (Lambert solve or the Cassini tour's fixed dates).
    """
    if epoch_mjd2000 is None:
        return None
    epoch = datetime(2000, 1, 1, tzinfo=timezone.utc) + timedelta(days=epoch_mjd2000)
    return epoch.strftime("%Y-%m-%d %H:%M UTC")


def _true_radius_m(body_name: str) -> float | None:
    """Best-effort real body radius in metres, for the optional real-scale toggle.

    Never guessed: returns None (not a fabricated value) when no sourced
    radius is available for this body, and callers must treat that as "no
    real-scale marker size for this landmark" rather than invent one.
    """
    if body_name == "Titan":
        return TITAN_MEAN_RADIUS_M
    try:
        body = resolve_body(body_name)
    except ValueError:
        return None
    if body.pykep_body is not None:
        return float(body.pykep_body.get_radius())
    return None


# --------------------------------------------------------------------------
# Adapter: the existing Saturn-centred arrival/staging/Titan-orbit scene
# --------------------------------------------------------------------------

_SATURN_CURVE_TYPE: dict[str, str] = {
    "capture_orbit": SEGMENT_TYPE_INSERTION,
    "staging_orbit": SEGMENT_TYPE_INSERTION,
    "spacecraft_transfer": SEGMENT_TYPE_TRANSFER,
    "moon_orbit": SEGMENT_TYPE_ORBIT_REFERENCE,
    "planet_orbit": SEGMENT_TYPE_ORBIT_REFERENCE,
}

_SATURN_CURVE_ORIGIN_DESTINATION: dict[str, tuple[str, str]] = {
    "Saturn arrival ellipse": ("Saturn", "Saturn"),
    "Saturn staging orbit": ("Saturn", "Saturn"),
    "Saturn → Titan transfer": ("Saturn", "Titan"),
    "Titan orbit": ("Titan", "Titan"),
}


def _saturn_curve_style(curve: TrajectoryCurve3D) -> SegmentStyle:
    from .trajectory_plot import CURVE_NAME_STYLE_OVERRIDE, ROLE_STYLE

    color, width, dash = CURVE_NAME_STYLE_OVERRIDE.get(curve.name) or ROLE_STYLE[curve.role]
    return SegmentStyle(color=color, width=width, dash=dash, legend_group=curve.frame)


def segments_from_saturn_system_scene(
    scene: CompleteMissionScene3D,
) -> tuple[TrajectorySegment, ...]:
    """Adapt the existing Saturn-centred curves (already computed by
    `mission.trajectory_visualization.build_complete_mission_scene`) into the
    generic segment schema, plus two landmarks (Saturn, Titan encounter)
    taken from the curves' own already-computed endpoints - no new geometry.
    """
    segments: list[TrajectorySegment] = []
    for index, curve in enumerate(scene.saturn_curves):
        origin, destination = _SATURN_CURVE_ORIGIN_DESTINATION.get(
            curve.name, (curve.name, curve.name)
        )
        segments.append(
            TrajectorySegment(
                id=f"saturn-system-{index}",
                name=curve.name,
                type=_SATURN_CURVE_TYPE.get(curve.role, SEGMENT_TYPE_TRANSFER),
                origin_body=origin,
                destination_body=destination,
                x=curve.x,
                y=curve.y,
                z=curve.z,
                style=_saturn_curve_style(curve),
                metadata={"frame": curve.frame, "unit": curve.unit},
            )
        )

    titan_transfer = scene.saturn_curves[2]
    segments.append(
        TrajectorySegment(
            id="saturn-system-landmark-saturn",
            name="Saturn",
            type=SEGMENT_TYPE_LANDMARK,
            origin_body="Saturn",
            destination_body="Saturn",
            x=(0.0,),
            y=(0.0,),
            z=(0.0,),
            style=SegmentStyle(color=colors.LANDMARK_BODY, marker_size=10),
            metadata={"true_radius_m": _true_radius_m("Saturn")},
        )
    )
    segments.append(
        TrajectorySegment(
            id="saturn-system-landmark-titan-encounter",
            name="Titan encounter",
            type=SEGMENT_TYPE_LANDMARK,
            origin_body="Titan",
            destination_body="Titan",
            x=(titan_transfer.x[-1],),
            y=(titan_transfer.y[-1],),
            z=(titan_transfer.z[-1],),
            style=SegmentStyle(color=colors.LANDMARK_MOON, marker_size=7),
            metadata={"true_radius_m": _true_radius_m("Titan")},
        )
    )
    return tuple(segments)


# --------------------------------------------------------------------------
# Adapter: the Cassini historical VVEJGA tour
# --------------------------------------------------------------------------

CASSINI_LEG_NAMES = (
    "Venus 1",
    "Venus 2",
    "Earth",
    "Jupiter",
    "Saturn insertion",
)
CASSINI_LEG_DASHES = ("solid", "dot", "dash", "longdash", "dashdot")


def segments_from_cassini_tour(
    tour: tuple[MissionSegment, ...],
) -> tuple[TrajectorySegment, ...]:
    """Adapt the five real Cassini legs (already computed by
    `mission.gravity_assist.compute_cassini_historical_tour`) into the
    generic segment schema: one line per leg plus one landmark per unique
    waypoint body, all taken from positions/dates/results the tour already
    computed - no new Lambert, ephemeris, or flyby calculation.
    """
    if len(tour) != len(CASSINI_LEG_NAMES):
        raise ValueError("tour must contain the five Cassini historical MissionSegments.")

    segments: list[TrajectorySegment] = []
    seen_landmarks: set[str] = set()
    for index, (leg, display_name, dash) in enumerate(
        zip(tour, CASSINI_LEG_NAMES, CASSINI_LEG_DASHES, strict=True)
    ):
        is_insertion = isinstance(leg.result, OrbitInsertionResult)
        if not is_insertion and not isinstance(leg.result, GravityAssistResult):
            raise TypeError("Each historical leg must end in a flyby or orbit insertion.")
        phase_color = colors.ARRIVAL if is_insertion else colors.INTERPLANETARY_TRANSFER
        segments.append(
            TrajectorySegment(
                id=f"cassini-tour-leg-{index}",
                name=display_name,
                type=SEGMENT_TYPE_INSERTION if is_insertion else SEGMENT_TYPE_FLYBY,
                origin_body=leg.departure_body,
                destination_body=leg.arrival_body,
                x=(leg.departure_position_m[0], leg.arrival_position_m[0]),
                y=(leg.departure_position_m[1], leg.arrival_position_m[1]),
                z=(leg.departure_position_m[2], leg.arrival_position_m[2]),
                departure_date=_format_mjd2000(leg.departure_epoch_mjd2000),
                arrival_date=_format_mjd2000(leg.arrival_epoch_mjd2000),
                duration_days=leg.arrival_epoch_mjd2000 - leg.departure_epoch_mjd2000,
                delta_v_m_s=(leg.result.delta_v_m_s if is_insertion else 0.0),
                style=SegmentStyle(
                    color=phase_color.dark, width=7, dash=dash, legend_group="cassini_tour"
                ),
                metadata={"event": "insertion" if is_insertion else leg.arrival_body},
            )
        )

        for body, position, epoch in (
            (leg.departure_body, leg.departure_position_m, leg.departure_epoch_mjd2000),
            (leg.arrival_body, leg.arrival_position_m, leg.arrival_epoch_mjd2000),
        ):
            landmark_key = f"{body}-{epoch}"
            if landmark_key in seen_landmarks:
                continue
            seen_landmarks.add(landmark_key)
            segments.append(
                TrajectorySegment(
                    id=f"cassini-tour-landmark-{landmark_key}",
                    name=body,
                    type=SEGMENT_TYPE_LANDMARK,
                    origin_body=body,
                    destination_body=body,
                    x=(position[0],),
                    y=(position[1],),
                    z=(position[2],),
                    departure_date=_format_mjd2000(epoch),
                    style=SegmentStyle(color=colors.LANDMARK_BODY, marker_size=6),
                    metadata={"true_radius_m": _true_radius_m(body)},
                )
            )
    return tuple(segments)
