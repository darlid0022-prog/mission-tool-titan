"""Physical ΔV primitives for impulsive injection and capture.

Conventions (documented explicitly for callers and tests):
- SI units: meters (m), seconds (s), meters per second (m/s).
- `mu` is the standard gravitational parameter in m^3/s^2.
- `r` is the orbital radius in m.
- `v_inf` is the hyperbolic excess speed in m/s (>= 0).

Functions:
- `delta_v_injection(v_inf, mu, r) -> float`
- `delta_v_capture(v_inf, mu, r) -> float`

Both functions compute the instantaneous impulsive ΔV required to
transition between a circular parking orbit and a hyperbolic approach/escape
characterized by `v_inf`, using the formula:

    v_circ = sqrt(mu / r)
    v_hyp  = sqrt(v_inf**2 + 2*mu / r)
    delta_v = v_hyp - v_circ

Input validation enforces: mu > 0, r > 0, v_inf >= 0.
"""

from __future__ import annotations

import math

from typing import Any


def _validate_inputs(v_inf: float, mu: float, r: float) -> None:
    if not isinstance(v_inf, (int, float)):
        raise ValueError("v_inf must be a number (m/s) and >= 0")
    if not isinstance(mu, (int, float)):
        raise ValueError("mu must be a positive number (m^3/s^2)")
    if not isinstance(r, (int, float)):
        raise ValueError("r must be a positive number (m)")

    if mu <= 0:
        raise ValueError("mu must be > 0")
    if r <= 0:
        raise ValueError("r must be > 0")
    if v_inf < 0:
        raise ValueError("v_inf must be >= 0")


def delta_v_injection(v_inf: float, mu: float, r: float) -> float:
    """Compute impulsive injection ΔV (m/s) from circular orbit to hyperbola.

    Parameters
    - v_inf: hyperbolic excess speed (m/s), must be >= 0
    - mu: gravitational parameter (m^3/s^2), must be > 0
    - r: orbital radius (m), must be > 0

    Returns
    - delta_v: required instantaneous ΔV in m/s
    """
    _validate_inputs(v_inf, mu, r)

    v_circ = math.sqrt(mu / r)
    v_hyp = math.sqrt(v_inf * v_inf + 2.0 * mu / r)
    return v_hyp - v_circ


def delta_v_capture(v_inf: float, mu: float, r: float) -> float:
    """Compute impulsive capture ΔV (m/s) from hyperbola to circular orbit.

    The formula is symmetric to injection for an impulsive maneuver at the
    same radius: ΔV = v_hyp - v_circ where v_hyp = sqrt(v_inf^2 + 2*mu/r).

    Parameters and units are identical to `delta_v_injection`.
    """
    _validate_inputs(v_inf, mu, r)

    v_hyp = math.sqrt(v_inf * v_inf + 2.0 * mu / r)
    v_circ = math.sqrt(mu / r)
    return v_hyp - v_circ
