"""Presentation adapters over existing scientific result contracts.

This module may derive display quantities from authoritative raw outputs, but
must not solve or modify a trajectory. It deliberately has no PyKEP import.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from mission.models import TrajectoryResult


@dataclass(frozen=True)
class LambertDeparturePresentation:
    """Raw, unrounded departure conditions for presentation and export."""

    earth_v_infinity_m_s: float
    c3_m2_s2: float


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
