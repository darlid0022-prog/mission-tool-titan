"""Isolated single-stage feasibility study for the connected mission."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .constants import G0_M_S2
from .mass_model import (
    HESPEROS_MODEL_VERSION,
    Manoeuvre,
    MassArchitectureInfeasibleError,
    ParametricBusCoefficients,
    PayloadItem,
    size_parametric_vehicle,
)


@dataclass(frozen=True)
class SingleStageFeasibilityResult:
    """Outcome of applying the calibrated model to one equivalent mission burn."""

    required_delta_v_m_s: float
    maximum_feasible_delta_v_m_s: float
    threshold_exceedance_factor: float
    is_feasible: bool
    model_version: str
    model_message: str


def evaluate_single_stage_chemical_feasibility(
    required_delta_v_m_s: float,
    isp_s: float,
    payload: tuple[PayloadItem, ...],
    coefficients: ParametricBusCoefficients | None = None,
) -> SingleStageFeasibilityResult:
    """Run the calibrated model and report its analytical convergence boundary."""
    required_delta_v = float(required_delta_v_m_s)
    specific_impulse = float(isp_s)
    if not math.isfinite(required_delta_v) or required_delta_v < 0.0:
        raise ValueError("required_delta_v_m_s must be finite and non-negative.")
    if not math.isfinite(specific_impulse) or specific_impulse <= 0.0:
        raise ValueError("isp_s must be finite and positive.")

    active_coefficients = coefficients or ParametricBusCoefficients()
    dry_coupling = (
        1.0 + active_coefficients.system_margin_fraction
    ) * active_coefficients.propulsion_dry_per_propellant
    if dry_coupling == 0.0:
        maximum_feasible_delta_v = math.inf
    else:
        maximum_feasible_delta_v = specific_impulse * G0_M_S2 * math.log1p(1.0 / dry_coupling)

    try:
        size_parametric_vehicle(
            payload,
            (Manoeuvre("Complete connected mission", required_delta_v, specific_impulse),),
            active_coefficients,
        )
    except MassArchitectureInfeasibleError as error:
        is_feasible = False
        model_message = str(error)
    else:
        is_feasible = True
        model_message = "The calibrated single-stage mass solution converged."

    exceedance_factor = (
        required_delta_v / maximum_feasible_delta_v
        if math.isfinite(maximum_feasible_delta_v) and maximum_feasible_delta_v > 0.0
        else 0.0
    )
    return SingleStageFeasibilityResult(
        required_delta_v_m_s=required_delta_v,
        maximum_feasible_delta_v_m_s=maximum_feasible_delta_v,
        threshold_exceedance_factor=exceedance_factor,
        is_feasible=is_feasible,
        model_version=HESPEROS_MODEL_VERSION,
        model_message=model_message,
    )
