"""Pure English v0.3.0 display formatting.

These helpers accept raw values and return display strings only. Callers must
retain and continue calculating with the original values; no formatted value
is suitable as a scientific input.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime

from mission.ui_text import UI_UNITS

DEFAULT_DURATION_TOLERANCE_DAYS = 1e-3


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


def format_mass_kg(value_kg: float, *, decimal_places: int = 0) -> str:
    """Format an existing mass-model output in kilograms."""
    value = _finite_number(value_kg, name="value_kg")
    precision = _decimal_places(decimal_places)
    return f"{value:,.{precision}f} {UI_UNITS['kilograms']}"


def format_datetime_utc(value: datetime) -> str:
    """Format an aware datetime as a civil UTC timestamp."""
    if not isinstance(value, datetime):
        raise TypeError("value must be a datetime.")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("value must be timezone-aware.")
    return value.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")


def format_short_date_utc(value: datetime) -> str:
    """Format an aware datetime as a bare civil UTC date (no time-of-day)."""
    if not isinstance(value, datetime):
        raise TypeError("value must be a datetime.")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("value must be timezone-aware.")
    return value.astimezone(UTC).date().isoformat()


@dataclass(frozen=True)
class DurationBreakdown:
    """Display-only decomposition of one already-computed total duration.

    Every field here is copied from raw, already-validated day counts the
    caller computed elsewhere (a Lambert leg's own MJD2000 difference, and
    the existing Saturn capture ellipse's own periapsis-to-apoapsis time of
    flight) - this dataclass never re-derives a duration and never solves a
    trajectory. `__post_init__` only checks that the three numbers the
    caller supplied are already mutually consistent to within tolerance; it
    is a presentation-layer sanity guard, not a source of truth.
    """

    total_days: float
    interplanetary_days: float
    saturn_phase_days: float
    tolerance_days: float

    def __post_init__(self) -> None:
        for name in ("total_days", "interplanetary_days", "saturn_phase_days", "tolerance_days"):
            _finite_number(getattr(self, name), name=name)
        if self.tolerance_days < 0.0:
            raise ValueError("tolerance_days must be non-negative.")
        residual = self.total_days - (self.interplanetary_days + self.saturn_phase_days)
        if abs(residual) > self.tolerance_days:
            raise ValueError(
                "Duration breakdown is inconsistent: total_days "
                f"({self.total_days!r}) does not equal interplanetary_days + "
                f"saturn_phase_days ({self.interplanetary_days!r} + "
                f"{self.saturn_phase_days!r}) within tolerance_days "
                f"({self.tolerance_days!r}); residual={residual!r}."
            )

    @property
    def synthesis_text(self) -> str:
        """One-line summary: total only, one decimal, no hedging word."""
        return f"{self.total_days:,.1f} {UI_UNITS['days']} complete"

    @property
    def detail_text(self) -> str:
        """Full three-decimal breakdown; "approximately" only qualifies the
        Saturn capture-ellipse component, never the complete total or the
        interplanetary leg (both are exact differences of validated epochs).
        """
        return (
            f"{self.total_days:,.3f} = {self.interplanetary_days:,.3f} + "
            f"approximately {self.saturn_phase_days:,.3f} {UI_UNITS['days']}"
        )


def build_duration_breakdown(
    *,
    total_days: float,
    interplanetary_days: float,
    saturn_phase_days: float,
    tolerance_days: float = DEFAULT_DURATION_TOLERANCE_DAYS,
) -> DurationBreakdown:
    """Validate and package an existing total/interplanetary/Saturn-phase split.

    Raises ValueError if the three supplied day counts are not mutually
    consistent within `tolerance_days` - this is the "coherence guard": it
    never adjusts a value to make the equation hold, it only refuses to
    display a breakdown that does not already hold.
    """
    return DurationBreakdown(
        total_days=total_days,
        interplanetary_days=interplanetary_days,
        saturn_phase_days=saturn_phase_days,
        tolerance_days=tolerance_days,
    )
