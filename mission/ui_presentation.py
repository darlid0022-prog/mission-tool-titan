"""Presentation adapters over existing scientific result contracts.

This module may derive display quantities from authoritative raw outputs, but
must not solve or modify a trajectory. It deliberately has no PyKEP import.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from mission.models import TrajectoryResult

LAST_VALID_MISSION_BUNDLE_STATE_KEY = "mission_last_valid_bundle_v030"


@dataclass(frozen=True)
class LambertDeparturePresentation:
    """Raw, unrounded departure conditions for presentation and export."""

    earth_v_infinity_m_s: float
    c3_m2_s2: float


@dataclass(frozen=True)
class MissionBudgetPresentation:
    """Raw values already produced by one active scientific scenario.

    The object is deliberately display-only: it stores no formatted strings
    and performs no trajectory, propulsion, or mass calculation.
    """

    earth_v_infinity_m_s: float | None
    c3_m2_s2: float | None
    earth_injection_m_s: float
    saturn_capture_m_s: float | None
    saturn_circularization_m_s: float | None
    connected_total_m_s: float
    dry_mass_kg: float | None = None
    propellant_mass_kg: float | None = None
    wet_mass_kg: float | None = None

    @property
    def saturn_subtotal_m_s(self) -> float | None:
        if self.saturn_capture_m_s is None or self.saturn_circularization_m_s is None:
            return None
        return self.saturn_capture_m_s + self.saturn_circularization_m_s


def build_lambert_departure_presentation(
    trajectory: TrajectoryResult,
) -> LambertDeparturePresentation:
    """Derive C3 from the active Lambert result's retained Earth v∞ magnitude.

    The adapter consumes the existing scalar magnitude only. It performs no
    ephemeris lookup, Lambert solve, trajectory propagation, or rounding.
    """
    if not isinstance(trajectory, TrajectoryResult):
        raise TypeError("trajectory must be a TrajectoryResult.")
    if trajectory.method != "lambert":
        raise ValueError("trajectory must be an authoritative Lambert result.")
    if trajectory.v_inf_depart is None:
        raise ValueError("Lambert departure v∞ is unavailable.")
    earth_v_infinity_m_s = float(trajectory.v_inf_depart)
    if not math.isfinite(earth_v_infinity_m_s) or earth_v_infinity_m_s < 0.0:
        raise ValueError("Lambert departure v∞ must be finite and non-negative.")
    return LambertDeparturePresentation(
        earth_v_infinity_m_s=earth_v_infinity_m_s,
        c3_m2_s2=earth_v_infinity_m_s**2,
    )


def build_mission_budget_presentation(
    *,
    trajectory: TrajectoryResult,
    earth_injection_m_s: float,
    connected_total_m_s: float,
    saturn_capture_m_s: float | None = None,
    saturn_circularization_m_s: float | None = None,
    dry_mass_kg: float | None = None,
    propellant_mass_kg: float | None = None,
    wet_mass_kg: float | None = None,
) -> MissionBudgetPresentation:
    """Adapt an already-calculated mission bundle without invoking a solver."""
    departure = (
        build_lambert_departure_presentation(trajectory)
        if trajectory.method == "lambert"
        else None
    )
    return MissionBudgetPresentation(
        earth_v_infinity_m_s=(
            departure.earth_v_infinity_m_s
            if departure is not None
            else trajectory.v_inf_depart
        ),
        c3_m2_s2=departure.c3_m2_s2 if departure is not None else None,
        earth_injection_m_s=float(earth_injection_m_s),
        saturn_capture_m_s=(
            float(saturn_capture_m_s) if saturn_capture_m_s is not None else None
        ),
        saturn_circularization_m_s=(
            float(saturn_circularization_m_s)
            if saturn_circularization_m_s is not None
            else None
        ),
        connected_total_m_s=float(connected_total_m_s),
        dry_mass_kg=float(dry_mass_kg) if dry_mass_kg is not None else None,
        propellant_mass_kg=(
            float(propellant_mass_kg) if propellant_mass_kg is not None else None
        ),
        wet_mass_kg=float(wet_mass_kg) if wet_mass_kg is not None else None,
    )


def build_candidate_budget_presentation(
    *,
    earth_v_infinity_m_s: float,
    c3_km2_s2: float,
    earth_injection_m_s: float,
    saturn_capture_m_s: float,
    saturn_circularization_m_s: float,
    connected_total_m_s: float,
) -> MissionBudgetPresentation:
    """Copy launch-search outputs, converting only the declared C3 unit."""
    return MissionBudgetPresentation(
        earth_v_infinity_m_s=float(earth_v_infinity_m_s),
        c3_m2_s2=float(c3_km2_s2) * 1_000_000.0,
        earth_injection_m_s=float(earth_injection_m_s),
        saturn_capture_m_s=float(saturn_capture_m_s),
        saturn_circularization_m_s=float(saturn_circularization_m_s),
        connected_total_m_s=float(connected_total_m_s),
    )
