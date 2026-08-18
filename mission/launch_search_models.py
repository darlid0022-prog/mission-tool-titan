"""Serializable data contract for direct Earth-to-Saturn launch searches."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from datetime import date
from enum import StrEnum
from typing import Any


class SearchObjective(StrEnum):
    MINIMUM_TOTAL_DELTA_V = "minimum_total_delta_v"
    MINIMUM_DURATION = "minimum_duration"
    MINIMUM_C3 = "minimum_c3"
    BALANCED_DELTA_V_DURATION = "balanced_delta_v_duration"


@dataclass(frozen=True)
class LaunchSearchConfig:
    launch_start: date
    launch_end: date
    min_time_of_flight_days: float
    max_time_of_flight_days: float
    departure_step_days: float
    arrival_step_days: float
    objective: SearchObjective = SearchObjective.MINIMUM_TOTAL_DELTA_V
    keep_count: int = 10
    refinement_count: int = 3
    fast_mode: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.launch_start, date) or not isinstance(self.launch_end, date):
            raise TypeError("launch_start and launch_end must be date values.")
        if self.launch_end < self.launch_start:
            raise ValueError("launch_end must not precede launch_start.")
        for name in (
            "min_time_of_flight_days",
            "max_time_of_flight_days",
            "departure_step_days",
            "arrival_step_days",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int | float):
                raise TypeError(f"{name} must be a real number of days.")
            if not math.isfinite(float(value)) or value <= 0.0:
                raise ValueError(f"{name} must be finite and positive.")
        if self.max_time_of_flight_days < self.min_time_of_flight_days:
            raise ValueError("max_time_of_flight_days must not be below the minimum.")
        if not isinstance(self.objective, SearchObjective):
            raise TypeError("objective must be a SearchObjective.")
        if isinstance(self.keep_count, bool) or not isinstance(self.keep_count, int):
            raise TypeError("keep_count must be an integer.")
        if self.keep_count <= 0:
            raise ValueError("keep_count must be positive.")
        if isinstance(self.refinement_count, bool) or not isinstance(
            self.refinement_count, int
        ):
            raise TypeError("refinement_count must be an integer.")
        if self.refinement_count < 0:
            raise ValueError("refinement_count must be non-negative.")


@dataclass(frozen=True)
class SearchTrajectorySegment:
    id: str
    name: str
    frame: str
    unit: str
    x: tuple[float, ...]
    y: tuple[float, ...]
    z: tuple[float, ...]
    departure_mjd2000: float
    arrival_mjd2000: float

    def __post_init__(self) -> None:
        if not self.id or not self.name or not self.frame or not self.unit:
            raise ValueError("Segment identifiers and reference metadata must not be empty.")
        if len(self.x) < 2 or len(self.x) != len(self.y) or len(self.x) != len(self.z):
            raise ValueError("Segment coordinate arrays must have equal lengths of at least two.")
        values = (*self.x, *self.y, *self.z, self.departure_mjd2000, self.arrival_mjd2000)
        if not all(math.isfinite(value) for value in values):
            raise ValueError("Segment coordinates and epochs must be finite.")
        if self.arrival_mjd2000 <= self.departure_mjd2000:
            raise ValueError("Segment arrival must follow departure.")


@dataclass(frozen=True)
class LaunchScenario:
    scenario_id: str
    launch_date: str
    saturn_arrival_date: str
    reference_phase_end_date: str
    launch_mjd2000: float
    saturn_arrival_mjd2000: float
    reference_phase_end_mjd2000: float
    interplanetary_duration_days: float
    total_duration_days: float
    c3_m2_s2: float
    earth_v_infinity_m_s: float
    saturn_v_infinity_m_s: float
    delta_v_by_manoeuvre_m_s: tuple[tuple[str, float], ...]
    total_delta_v_m_s: float
    objective_score: float
    feasible: bool
    rejection_reasons: tuple[str, ...]
    assumptions: tuple[str, ...]
    segments: tuple[SearchTrajectorySegment, ...]

    def __post_init__(self) -> None:
        if not self.scenario_id:
            raise ValueError("scenario_id must not be empty.")
        numeric_values = (
            self.launch_mjd2000,
            self.saturn_arrival_mjd2000,
            self.reference_phase_end_mjd2000,
            self.interplanetary_duration_days,
            self.total_duration_days,
            self.c3_m2_s2,
            self.earth_v_infinity_m_s,
            self.saturn_v_infinity_m_s,
            self.total_delta_v_m_s,
            self.objective_score,
        )
        if not all(math.isfinite(value) for value in numeric_values):
            raise ValueError("Scenario numeric fields must be finite.")
        if not self.launch_mjd2000 < self.saturn_arrival_mjd2000 < self.reference_phase_end_mjd2000:
            raise ValueError("Scenario epochs must be strictly chronological.")
        if self.feasible == bool(self.rejection_reasons):
            raise ValueError("Feasible scenarios cannot have rejection reasons, and vice versa.")
        if self.total_delta_v_m_s != sum(value for _, value in self.delta_v_by_manoeuvre_m_s):
            raise ValueError("total_delta_v_m_s must equal the exact manoeuvre sum.")

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible representation for UI and persistence layers."""
        return asdict(self)


@dataclass(frozen=True)
class LaunchSearchResult:
    config: LaunchSearchConfig
    solutions: tuple[LaunchScenario, ...]
    pareto_front: tuple[LaunchScenario, ...]
    rejected_pairs: tuple[tuple[float, float, str], ...]
    evaluated_pair_count: int
    ephemeris_evaluation_count: int
    elapsed_seconds: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
