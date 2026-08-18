"""Canonical propulsive delta-v aggregation for the complete Titan chain."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .connected_physics import ConnectedFirstOrderResult, compute_connected_first_order_chain
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
            "Saturn capture to 150,000 × 1,221,870 km ellipse": (
                self.saturn_capture_to_ellipse_m_s
            ),
            "Saturn circularization at Titan orbital radius": (
                self.saturn_staging_circularisation_m_s
            ),
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
    saturn_arrival_staging: SaturnArrivalStagingResult | None = None,
    saturn_titan_transfer: SaturnTitanTransferResult | None = None,
    *,
    connected_result: ConnectedFirstOrderResult | None = None,
) -> MissionDeltaVBudget:
    """Compose the authoritative first-order chain without redundant burns.

    The two legacy study arguments remain accepted for source compatibility,
    but their 600,000 km departure and Titan-capture burns are deliberately not
    included. ``connected_result`` is the sole authority for Saturn burns.
    """
    if not isinstance(earth_saturn_budget, dict):
        raise TypeError("earth_saturn_budget must be a dict.")
    if saturn_arrival_staging is not None and not isinstance(
        saturn_arrival_staging, SaturnArrivalStagingResult
    ):
        raise TypeError("saturn_arrival_staging must be a SaturnArrivalStagingResult or None.")
    if saturn_titan_transfer is not None and not isinstance(
        saturn_titan_transfer, SaturnTitanTransferResult
    ):
        raise TypeError("saturn_titan_transfer must be a SaturnTitanTransferResult or None.")
    chain = connected_result or compute_connected_first_order_chain()
    if not isinstance(chain, ConnectedFirstOrderResult):
        raise TypeError("connected_result must be a ConnectedFirstOrderResult or None.")

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
        saturn_capture_to_ellipse_m_s=chain.saturn_capture.capture_delta_v_m_s,
        saturn_staging_circularisation_m_s=(
            chain.saturn_capture.circularisation_delta_v_m_s
        ),
        saturn_titan_departure_m_s=0.0,
        titan_capture_m_s=0.0,
    )
