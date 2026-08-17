"""Deterministic Pareto search for the connected Earth-Saturn-Titan mission.

Scientific interpretation for the current fixed architecture:

- With fixed Isp and payload, wet mass is a strictly increasing function of
  connected delta-v, so mass is reported but is not an independent Pareto axis.
- The locked 2,856-day Earth-to-Saturn point is 3.253614 m/s (about 0.02%) above
  the sampled minimum connected delta-v. It remains the reproducible application
  baseline even though a 2,826-day sample dominates it on all three objectives.

Next step: expose this front in Streamlit, or freeze the computed results for the
mission presentation if feature development is complete.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date

import pandas as pd

from . import physics
from .bodies import resolve_body
from .dv_budget import compose_complete_dv_budget
from .full_mission import compute_earth_saturn_titan_mission
from .leg_solver import compute_lambert_leg
from .models import Leg, TrajectoryResult
from .moon_transfer import DEFAULT_TITAN_CAPTURE_ALTITUDE_M
from .saturn_staging import DEFAULT_SATURN_STAGING_RADIUS_M
from .sizing import compute_mass_budget

LOCKED_LAUNCH_WINDOW_START = date(2026, 6, 1)
LOCKED_LAUNCH_WINDOW_END = date(2027, 6, 1)
EARTH_SATURN_TOF_MIN_YEARS = 4.0
EARTH_SATURN_TOF_MAX_YEARS = 8.0
EARTH_SATURN_TOF_STEP_DAYS = 15.0
DEFAULT_DEPARTURE_SAMPLES = 12

DEFAULT_LEO_ALTITUDE_M = 250_000.0
DEFAULT_ISP_S = 320.0
DEFAULT_INSTRUMENT_MASS_KG = 143.5
DEFAULT_SATURN_PERIAPSIS_RADIUS_M = 62_330_000.0
DEFAULT_SATURN_PERIAPSIS_PROVENANCE = (
    "Pareto fixed input: nominal Saturn planet-to-D-ring corridor periapsis."
)


@dataclass(frozen=True)
class ParetoPoint:
    """One feasible decision pair and its three connected mission objectives."""

    departure_mjd2000: float
    earth_saturn_tof_years: float
    earth_saturn_arrival_mjd2000: float
    earth_departure_v_infinity_m_s: float
    saturn_arrival_v_infinity_m_s: float
    total_delta_v_m_s: float
    total_duration_days: float
    wet_mass_kg: float

    def __post_init__(self) -> None:
        values = (
            self.departure_mjd2000,
            self.earth_saturn_tof_years,
            self.earth_saturn_arrival_mjd2000,
            self.earth_departure_v_infinity_m_s,
            self.saturn_arrival_v_infinity_m_s,
            self.total_delta_v_m_s,
            self.total_duration_days,
            self.wet_mass_kg,
        )
        if not all(math.isfinite(float(value)) for value in values):
            raise ValueError("Pareto point values must be finite.")
        if any(
            value < 0.0
            for value in (
                self.earth_saturn_tof_years,
                self.earth_departure_v_infinity_m_s,
                self.saturn_arrival_v_infinity_m_s,
                self.total_delta_v_m_s,
                self.total_duration_days,
                self.wet_mass_kg,
            )
        ):
            raise ValueError("Pareto objectives and transfer magnitudes must be non-negative.")

    @property
    def objectives(self) -> tuple[float, float, float]:
        """Return minimization objectives in their canonical order."""
        return (self.total_delta_v_m_s, self.total_duration_days, self.wet_mass_kg)


@dataclass(frozen=True)
class ParetoSearchResult:
    """All feasible samples plus a deterministically ordered non-dominated front."""

    evaluated_points: tuple[ParetoPoint, ...]
    pareto_front: tuple[ParetoPoint, ...]

    @property
    def evaluated_count(self) -> int:
        return len(self.evaluated_points)

    @property
    def pareto_count(self) -> int:
        return len(self.pareto_front)


def _dominates(left: ParetoPoint, right: ParetoPoint) -> bool:
    return all(a <= b for a, b in zip(left.objectives, right.objectives, strict=True)) and any(
        a < b for a, b in zip(left.objectives, right.objectives, strict=True)
    )


def _front_order(point: ParetoPoint) -> tuple[float, ...]:
    return (
        point.total_duration_days,
        point.total_delta_v_m_s,
        point.wet_mass_kg,
        point.departure_mjd2000,
        point.earth_saturn_tof_years,
        point.earth_saturn_arrival_mjd2000,
        point.earth_departure_v_infinity_m_s,
        point.saturn_arrival_v_infinity_m_s,
    )


def extract_pareto_front(points: tuple[ParetoPoint, ...]) -> tuple[ParetoPoint, ...]:
    """Return all non-dominated points with explicit deterministic ordering."""
    if not isinstance(points, tuple):
        raise TypeError("points must be a tuple of ParetoPoint values.")
    if not all(isinstance(point, ParetoPoint) for point in points):
        raise TypeError("points must contain only ParetoPoint values.")

    front = [
        candidate
        for candidate in points
        if not any(_dominates(other, candidate) for other in points if other is not candidate)
    ]
    return tuple(sorted(front, key=_front_order))


def _required_trajectory_value(trajectory: TrajectoryResult, name: str) -> float:
    value = getattr(trajectory, name)
    if value is None:
        raise ValueError(f"Lambert trajectory must provide {name}.")
    converted = float(value)
    if not math.isfinite(converted):
        raise ValueError(f"Lambert trajectory {name} must be finite.")
    return converted


def _evaluate_trajectory(
    trajectory: TrajectoryResult,
    *,
    earth_mu_m3_s2: float,
    earth_leo_radius_m: float,
    instruments: pd.DataFrame,
    isp_s: float,
    saturn_periapsis_radius_m: float,
    saturn_staging_radius_m: float,
    titan_capture_altitude_m: float,
) -> ParetoPoint:
    departure_mjd2000 = _required_trajectory_value(trajectory, "departure_mjd2000")
    arrival_mjd2000 = _required_trajectory_value(trajectory, "arrival_mjd2000")
    tof_years = _required_trajectory_value(trajectory, "tof_years")
    departure_v_infinity = _required_trajectory_value(trajectory, "v_inf_depart")
    arrival_v_infinity = _required_trajectory_value(trajectory, "v_inf_arrival")

    earth_departure_delta_v = physics.delta_v_injection(
        departure_v_infinity,
        earth_mu_m3_s2,
        earth_leo_radius_m,
    )
    earth_budget = {
        "dV from LEO": earth_departure_delta_v,
        "dV DSM/Fly-By": 0.0,
    }
    connected = compute_earth_saturn_titan_mission(
        Leg(origin="Earth", destination="Saturn", trajectory=trajectory),
        saturn_periapsis_radius_m=saturn_periapsis_radius_m,
        saturn_periapsis_radius_provenance=DEFAULT_SATURN_PERIAPSIS_PROVENANCE,
        saturn_staging_radius_m=saturn_staging_radius_m,
        titan_capture_altitude_m=titan_capture_altitude_m,
    )
    delta_v_budget = compose_complete_dv_budget(
        earth_budget,
        connected.saturn_arrival_staging,
        connected.saturn_titan_transfer,
    )
    total_delta_v = delta_v_budget.total_m_s
    mass_budget = compute_mass_budget(total_delta_v, isp_s, instruments)

    final_trajectory = connected.mission.legs[-1].trajectory
    if final_trajectory is None:
        raise ValueError("Connected mission must provide a final trajectory.")
    final_arrival_mjd2000 = _required_trajectory_value(final_trajectory, "arrival_mjd2000")

    return ParetoPoint(
        departure_mjd2000=departure_mjd2000,
        earth_saturn_tof_years=tof_years,
        earth_saturn_arrival_mjd2000=arrival_mjd2000,
        earth_departure_v_infinity_m_s=departure_v_infinity,
        saturn_arrival_v_infinity_m_s=arrival_v_infinity,
        total_delta_v_m_s=total_delta_v,
        total_duration_days=final_arrival_mjd2000 - departure_mjd2000,
        wet_mass_kg=mass_budget["wet_mass_kg"],
    )


def compute_connected_pareto_front(
    *,
    launch_window_start: date = LOCKED_LAUNCH_WINDOW_START,
    launch_window_end: date = LOCKED_LAUNCH_WINDOW_END,
    n_departures: int = DEFAULT_DEPARTURE_SAMPLES,
    tof_min_years: float = EARTH_SATURN_TOF_MIN_YEARS,
    tof_max_years: float = EARTH_SATURN_TOF_MAX_YEARS,
    tof_step_days: float = EARTH_SATURN_TOF_STEP_DAYS,
    leo_altitude_m: float = DEFAULT_LEO_ALTITUDE_M,
    isp_s: float = DEFAULT_ISP_S,
    instrument_mass_kg: float = DEFAULT_INSTRUMENT_MASS_KG,
    saturn_periapsis_radius_m: float = DEFAULT_SATURN_PERIAPSIS_RADIUS_M,
    saturn_staging_radius_m: float = DEFAULT_SATURN_STAGING_RADIUS_M,
    titan_capture_altitude_m: float = DEFAULT_TITAN_CAPTURE_ALTITUDE_M,
) -> ParetoSearchResult:
    """Evaluate the fixed two-variable grid and extract its exact Pareto front."""
    if launch_window_start < LOCKED_LAUNCH_WINDOW_START:
        raise ValueError("launch_window_start is outside the locked search window.")
    if launch_window_end > LOCKED_LAUNCH_WINDOW_END:
        raise ValueError("launch_window_end is outside the locked search window.")
    if launch_window_end < launch_window_start:
        raise ValueError("launch_window_end must not precede launch_window_start.")
    if tof_min_years < EARTH_SATURN_TOF_MIN_YEARS:
        raise ValueError("tof_min_years is below the established 4-year bound.")
    if tof_max_years > EARTH_SATURN_TOF_MAX_YEARS:
        raise ValueError("tof_max_years exceeds the established 8-year bound.")

    earth = resolve_body("Earth")
    assert earth.pykep_body is not None
    earth_leo_radius = earth.pykep_body.get_radius() + float(leo_altitude_m)
    instruments = pd.DataFrame([{"Masse (kg)": float(instrument_mass_kg)}])

    trajectories = compute_lambert_leg(
        "Earth",
        "Saturn",
        launch_window_start,
        launch_window_end,
        n_departures=n_departures,
        tof_min_years=tof_min_years,
        tof_max_years=tof_max_years,
        tof_step_days=tof_step_days,
    )
    ordered_trajectories = sorted(
        trajectories,
        key=lambda trajectory: (
            _required_trajectory_value(trajectory, "departure_mjd2000"),
            _required_trajectory_value(trajectory, "tof_years"),
            _required_trajectory_value(trajectory, "arrival_mjd2000"),
            _required_trajectory_value(trajectory, "v_inf_depart"),
            _required_trajectory_value(trajectory, "v_inf_arrival"),
        ),
    )
    evaluated = tuple(
        _evaluate_trajectory(
            trajectory,
            earth_mu_m3_s2=earth.get_mu_self(),
            earth_leo_radius_m=earth_leo_radius,
            instruments=instruments,
            isp_s=isp_s,
            saturn_periapsis_radius_m=saturn_periapsis_radius_m,
            saturn_staging_radius_m=saturn_staging_radius_m,
            titan_capture_altitude_m=titan_capture_altitude_m,
        )
        for trajectory in ordered_trajectories
    )
    return ParetoSearchResult(
        evaluated_points=evaluated,
        pareto_front=extract_pareto_front(evaluated),
    )
