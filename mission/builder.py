from __future__ import annotations

from typing import Iterable, Optional

from .models import Event, Leg, Mission, TrajectoryResult


def build_mission_from_trajectory_alternatives(
    trajectory_alternatives: dict,
    *,
    mission_name: str = "Earth -> Saturn",
    selection_key: str = "best_by_departure_v_inf",
) -> Mission:
    """Convert an Earth->Saturn result from compute_trajectory_alternatives() into a Mission.

    The legacy trajectory dict values are preserved exactly. v∞ values are copied into
    TrajectoryResult.v_inf_depart and TrajectoryResult.v_inf_arrival, while actual
    propulsive delta-v remains unset (None).
    """
    if not isinstance(trajectory_alternatives, dict):
        raise TypeError("trajectory_alternatives must be a dict from compute_trajectory_alternatives().")

    selected = trajectory_alternatives.get(selection_key)
    if selected is None:
        raise ValueError(f"No solution found under selection key '{selection_key}'.")

    departure_mjd2000 = selected.get("departure_mjd2000")
    arrival_mjd2000 = selected.get("arrival_mjd2000")
    tof_years = selected.get("tof_years")
    v_inf_depart = selected.get("dv_depart")
    v_inf_arrival = selected.get("v_infinity_saturn")

    trajectory = TrajectoryResult(
        departure_mjd2000=departure_mjd2000,
        arrival_mjd2000=arrival_mjd2000,
        tof_years=tof_years,
        v_inf_depart=v_inf_depart,
        v_inf_arrival=v_inf_arrival,
        delta_v=None,
        method="lambert",
        notes="Legacy trajectory values preserved; actual propulsive delta-v is not implemented.",
    )

    departure_event = Event(
        name="Earth departure",
        body="Earth",
        event_type="departure",
        epoch=departure_mjd2000,
        notes="Legacy trajectory departure epoch.",
    )
    arrival_event = Event(
        name="Saturn arrival",
        body="Saturn",
        event_type="arrival",
        epoch=arrival_mjd2000,
        notes="Legacy trajectory arrival epoch.",
    )

    leg = Leg(
        origin="Earth",
        destination="Saturn",
        trajectory=trajectory,
        events=[departure_event, arrival_event],
        notes="Earth -> Saturn Lambert transfer represented in the mission domain model.",
    )

    mission = Mission(
        name=mission_name,
        legs=[leg],
        events=[departure_event, arrival_event],
        notes="Legacy Earth->Saturn trajectory adapted into the mission-domain model.",
    )
    return mission


def build_event(
    name: str,
    body: str,
    event_type: str = "generic",
    epoch: Optional[object] = None,
    notes: str = "",
) -> Event:
    """Construct a mission event with basic validation."""
    return Event(
        name=name,
        body=body,
        event_type=event_type,
        epoch=epoch,
        notes=notes,
    )


def build_trajectory_result(
    *,
    departure_mjd2000: Optional[float] = None,
    arrival_mjd2000: Optional[float] = None,
    tof_years: Optional[float] = None,
    v_inf_depart: Optional[float] = None,
    v_inf_arrival: Optional[float] = None,
    delta_v: Optional[float] = None,
    method: str = "",
    notes: str = "",
) -> TrajectoryResult:
    """Construct a transfer result while keeping v∞ distinct from actual ΔV."""
    return TrajectoryResult(
        departure_mjd2000=departure_mjd2000,
        arrival_mjd2000=arrival_mjd2000,
        tof_years=tof_years,
        v_inf_depart=v_inf_depart,
        v_inf_arrival=v_inf_arrival,
        delta_v=delta_v,
        method=method,
        notes=notes,
    )


def build_leg(
    origin: str,
    destination: str,
    *,
    trajectory: Optional[TrajectoryResult] = None,
    events: Optional[Iterable[Event]] = None,
    notes: str = "",
) -> Leg:
    """Construct a transfer leg with optional trajectory result and events."""
    return Leg(
        origin=origin,
        destination=destination,
        trajectory=trajectory,
        events=list(events) if events is not None else [],
        notes=notes,
    )


def build_mission(
    name: str = "Mission",
    *,
    legs: Optional[Iterable[Leg]] = None,
    events: Optional[Iterable[Event]] = None,
    notes: str = "",
) -> Mission:
    """Construct a mission with basic ordering validation."""
    return Mission(
        name=name,
        legs=list(legs) if legs is not None else [],
        events=list(events) if events is not None else [],
        notes=notes,
    )
