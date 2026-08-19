"""Pure English v0.3.0 display formatting.

These helpers accept raw values and return display strings only. Callers must
retain and continue calculating with the original values; no formatted value
is suitable as a scientific input.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime

from mission.ui_text import UI_UNITS


def _finite_number(value: float, *, name: str) -> float:
    if isinstance(value, bool):
        raise TypeError(f"{name} must be a real number.")
    converted = float(value)
    if not math.isfinite(converted):
        raise ValueError(f"{name} must be finite.")
    return converted


def _decimal_places(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("decimal_places must be an integer.")
    if not 0 <= value <= 9:
        raise ValueError("decimal_places must be between 0 and 9.")
    return value


def format_delta_v_m_s(value_m_s: float, *, decimal_places: int = 3) -> str:
    """Format propulsive delta-v in m/s without changing the raw value."""
    value = _finite_number(value_m_s, name="value_m_s")
    precision = _decimal_places(decimal_places)
    return f"{value:,.{precision}f} {UI_UNITS['metres_per_second']}"


def format_speed_m_s(value_m_s: float, *, decimal_places: int = 3) -> str:
    """Format a speed in m/s; the label determines whether it is v∞ or delta-v."""
    value = _finite_number(value_m_s, name="value_m_s")
    precision = _decimal_places(decimal_places)
    return f"{value:,.{precision}f} {UI_UNITS['metres_per_second']}"


def format_approximate_speed_km_s(
    value_m_s: float,
    *,
    decimal_places: int = 3,
) -> str:
    """Format an SI speed as an explicitly approximate km/s display value."""
    value = _finite_number(value_m_s, name="value_m_s")
    precision = _decimal_places(decimal_places)
    return f"approximately {value / 1_000.0:,.{precision}f} {UI_UNITS['kilometres_per_second']}"


def format_approximate_c3_km2_s2(
    value_m2_s2: float,
    *,
    decimal_places: int = 2,
) -> str:
    """Format raw C3 from m²/s² as an approximate km²/s² display value."""
    value = _finite_number(value_m2_s2, name="value_m2_s2")
    precision = _decimal_places(decimal_places)
    return (
        f"approximately {value / 1_000_000.0:,.{precision}f} "
        f"{UI_UNITS['square_kilometres_per_square_second']}"
    )


def format_distance_km(value_m: float, *, decimal_places: int = 0) -> str:
    """Format an internal SI distance as kilometres."""
    value = _finite_number(value_m, name="value_m")
    precision = _decimal_places(decimal_places)
    return f"{value / 1_000.0:,.{precision}f} {UI_UNITS['kilometres']}"


def format_duration_days(value_days: float, *, decimal_places: int = 1) -> str:
    """Format a duration already represented in days."""
    value = _finite_number(value_days, name="value_days")
    precision = _decimal_places(decimal_places)
    return f"{value:,.{precision}f} {UI_UNITS['days']}"


def format_datetime_utc(value: datetime) -> str:
    """Format an aware datetime as a civil UTC timestamp."""
    if not isinstance(value, datetime):
        raise TypeError("value must be a datetime.")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("value must be timezone-aware.")
    return value.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")
