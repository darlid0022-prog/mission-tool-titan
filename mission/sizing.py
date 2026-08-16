"""Preliminary spacecraft mass-sizing calculations."""

import math

import pandas as pd


def compute_mass_budget(
    dv_total: float,
    isp_s: float,
    instruments_df: pd.DataFrame,
    harness_frac: float = 0.10,
    structure_frac: float = 0.20,
    margin_frac: float = 0.20,
) -> dict[str, float]:
    """Estimate dry, propellant, and wet mass from the current inputs."""
    g0 = 9.80665
    if not math.isfinite(float(dv_total)) or dv_total < 0:
        raise ValueError("dv_total must be finite and non-negative.")
    if not math.isfinite(float(isp_s)) or isp_s <= 0:
        raise ValueError("isp_s must be finite and positive.")
    instrument_mass = float(instruments_df["Masse (kg)"].fillna(0).sum())

    # Placeholder subsystem model retained from the original Streamlit page.
    subsystems_mass = instrument_mass
    dry_mass_before_margin = subsystems_mass * (1 + harness_frac + structure_frac)
    dry_mass = dry_mass_before_margin * (1 + margin_frac)

    if dv_total > 0 and isp_s > 0:
        exponent = dv_total / (isp_s * g0)
        try:
            mass_ratio = math.exp(exponent)
        except OverflowError as error:
            raise ValueError(
                "The requested delta-v and Isp produce an infinite mass ratio."
            ) from error
        if not math.isfinite(mass_ratio):
            raise ValueError("The requested delta-v and Isp produce an infinite mass ratio.")
        wet_mass = dry_mass * mass_ratio
        propellant_mass = wet_mass - dry_mass
    else:
        wet_mass = dry_mass
        propellant_mass = 0.0

    return {
        "instrument_mass_kg": instrument_mass,
        "dry_mass_kg": float(dry_mass),
        "propellant_mass_kg": float(propellant_mass),
        "wet_mass_kg": float(wet_mass),
    }
