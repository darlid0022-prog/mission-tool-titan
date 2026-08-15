"""Preliminary spacecraft mass-sizing calculations."""

import numpy as np
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
    instrument_mass = float(instruments_df["Masse (kg)"].fillna(0).sum())

    # Placeholder subsystem model retained from the original Streamlit page.
    subsystems_mass = instrument_mass
    dry_mass_before_margin = subsystems_mass * (1 + harness_frac + structure_frac)
    dry_mass = dry_mass_before_margin * (1 + margin_frac)

    if dv_total > 0 and isp_s > 0:
        mass_ratio = np.exp(dv_total / (isp_s * g0))
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
