from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Event:
    """Mission milestone or phase change.

    Examples include departure, arrival, capture, flyby, or landing.
    """

    name: str
    body: str
    event_type: str = "generic"
    epoch: Optional[Any] = None
    notes: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Event name must be a non-empty string.")
        if not isinstance(self.body, str) or not self.body.strip():
            raise ValueError("Event body must be a non-empty string.")
        if not isinstance(self.event_type, str) or not self.event_type.strip():
            raise ValueError("Event type must be a non-empty string.")


@dataclass
class TrajectoryResult:
    """A transfer result with explicit separation between v∞ and propulsive ΔV."""

    departure_mjd2000: Optional[float] = None
    arrival_mjd2000: Optional[float] = None
    tof_years: Optional[float] = None
    v_inf_depart: Optional[float] = None
    v_inf_arrival: Optional[float] = None
    delta_v: Optional[float] = None
    method: str = ""
    notes: str = ""

    def __post_init__(self) -> None:
        if self.v_inf_depart is not None and self.v_inf_depart < 0:
            raise ValueError("v_inf_depart must be non-negative.")
        if self.v_inf_arrival is not None and self.v_inf_arrival < 0:
            raise ValueError("v_inf_arrival must be non-negative.")
        if self.delta_v is not None and self.delta_v < 0:
            raise ValueError("delta_v must be non-negative.")


@dataclass
class Leg:
    """A single origin-body to destination-body transfer leg."""

    origin: str
    destination: str
    trajectory: Optional[TrajectoryResult] = None
    events: list[Event] = field(default_factory=list)
    notes: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.origin, str) or not self.origin.strip():
            raise ValueError("Leg origin must be a non-empty string.")
        if not isinstance(self.destination, str) or not self.destination.strip():
            raise ValueError("Leg destination must be a non-empty string.")

    def add_event(self, event: Event) -> None:
        self.events.append(event)


@dataclass
class Mission:
    """A mission is an ordered sequence of legs and mission events."""

    name: str = "Mission"
    legs: list[Leg] = field(default_factory=list)
    events: list[Event] = field(default_factory=list)
    notes: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("Mission name must be a non-empty string.")
        self._validate_leg_order()
        self._validate_event_order()

    def add_leg(self, leg: Leg) -> None:
        self.legs.append(leg)
        self._validate_leg_order()

    def add_event(self, event: Event) -> None:
        self.events.append(event)
        self._validate_event_order()

    def _validate_leg_order(self) -> None:
        """Basic chronology check when both legs carry transfer timing data."""
        for index in range(1, len(self.legs)):
            previous = self.legs[index - 1]
            current = self.legs[index]
            prev_traj = previous.trajectory
            curr_traj = current.trajectory
            if prev_traj is None or curr_traj is None:
                continue
            if prev_traj.arrival_mjd2000 is None or curr_traj.departure_mjd2000 is None:
                continue
            if prev_traj.arrival_mjd2000 > curr_traj.departure_mjd2000:
                raise ValueError(
                    "Mission legs are not chronologically ordered: "
                    "a later leg begins before the previous leg arrives."
                )

    def _validate_event_order(self) -> None:
        """Basic ordering check when event epochs are present."""
        if not self.events:
            return
        epochs = [event.epoch for event in self.events if event.epoch is not None]
        if len(epochs) < 2:
            return
        if epochs != sorted(epochs):
            raise ValueError("Mission events are not in chronological order.")
