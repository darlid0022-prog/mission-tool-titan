"""Canonical propulsive delta-v aggregation for the complete Titan chain."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .moon_transfer import SaturnTitanTransferResult
from .saturn_staging import SaturnArrivalStagingResult


@dataclass(frozen=True)
class MissionDeltaVBudget:
    """Propulsive mission terms with the obsolete Saturn capture removed."""

    earth_departure_m_s: float
    dsm_flyby_m_s: float
    saturn_capture_to_ellipse_m_s: float
    saturn_staging_circularisation_m_s: float
    saturn_titan_departure_m_s: float
    titan_capture_m_s: float

    @property
    def total_m_s(self) -> float:
        return sum(self.as_dict().values())

    def as_dict(self) -> dict[str, float]:
        return {
            "Earth departure injection": self.earth_departure_m_s,
            "DSM / fly-by corrections": self.dsm_flyby_m_s,
            "Saturn capture to transfer ellipse": self.saturn_capture_to_ellipse_m_s,
            "Saturn staging circularization": self.saturn_staging_circularisation_m_s,
            "Saturn staging to Titan transfer": self.saturn_titan_departure_m_s,
            "Titan circular capture": self.titan_capture_m_s,
        }


def _require_non_negative_finite(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise TypeError(f"{name} must be a real delta-v in m/s.")
    converted = float(value)
    if not math.isfinite(converted) or converted < 0.0:
        raise ValueError(f"{name} must be finite and non-negative.")
    return converted


def compose_complete_dv_budget(
    earth_saturn_budget: dict[str, float],
    saturn_arrival_staging: SaturnArrivalStagingResult,
    saturn_titan_transfer: SaturnTitanTransferResult,
) -> MissionDeltaVBudget:
    """Compose real burns and replace, rather than add, legacy Saturn capture."""
    if not isinstance(earth_saturn_budget, dict):
        raise TypeError("earth_saturn_budget must be a dict.")
    if not isinstance(saturn_arrival_staging, SaturnArrivalStagingResult):
        raise TypeError("saturn_arrival_staging must be a SaturnArrivalStagingResult.")
    if not isinstance(saturn_titan_transfer, SaturnTitanTransferResult):
        raise TypeError("saturn_titan_transfer must be a SaturnTitanTransferResult.")

    try:
        earth_departure = earth_saturn_budget["dV from LEO"]
        dsm_flyby = earth_saturn_budget["dV DSM/Fly-By"]
    except KeyError as error:
        raise ValueError(
            f"Earth-to-Saturn budget is missing required term: {error.args[0]}"
        ) from error

    return MissionDeltaVBudget(
        earth_departure_m_s=_require_non_negative_finite("earth departure", earth_departure),
        dsm_flyby_m_s=_require_non_negative_finite("DSM / fly-by", dsm_flyby),
        saturn_capture_to_ellipse_m_s=saturn_arrival_staging.capture_to_ellipse_delta_v_m_s,
        saturn_staging_circularisation_m_s=(
            saturn_arrival_staging.staging_circularisation_delta_v_m_s
        ),
        saturn_titan_departure_m_s=saturn_titan_transfer.departure_delta_v_m_s,
        titan_capture_m_s=saturn_titan_transfer.capture_delta_v_m_s,
    )
