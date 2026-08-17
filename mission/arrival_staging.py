"""Pure, body-agnostic hyperbolic-arrival to staging-orbit model."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .models import Event, Leg, TrajectoryResult

SECONDS_PER_DAY = 86_400.0
DAYS_PER_JULIAN_YEAR = 365.25
METHOD = "hyperbolic_capture_to_elliptic_staging"


@dataclass(frozen=True)
class StagingRadiusGuard:
    """Optional body-specific lower bound for a circular staging radius."""

    minimum_radius_m: float
    description: str


@dataclass(frozen=True)
class ArrivalStagingResult:
    """Typed result shared by arrival-to-staging studies for any parent body."""

    parent_body: str
    origin_state: str
    destination_state: str
    method: str
    source: str
    parent_mu_m3_s2: float
    arrival_v_infinity_m_s: float
    periapsis_radius_m: float
    staging_radius_m: float
    transfer_semimajor_axis_m: float
    hyperbolic_periapsis_speed_m_s: float
    transfer_periapsis_speed_m_s: float
    capture_to_ellipse_delta_v_m_s: float
    transfer_apoapsis_speed_m_s: float
    staging_circular_speed_m_s: float
    staging_circularisation_delta_v_m_s: float
    total_delta_v_m_s: float
    time_of_flight_s: float
    periapsis_radius_provenance: str
    assumptions: tuple[str, ...]
    exclusions: tuple[str, ...]

    @property
    def time_of_flight_days(self) -> float:
        return self.time_of_flight_s / SECONDS_PER_DAY


def _require_non_empty_string(name: str, value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string.")
    return value.strip()


def _require_finite_number(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise TypeError(f"{name} must be a real number in SI units.")
    converted = float(value)
    if not math.isfinite(converted):
        raise ValueError(f"{name} must be finite.")
    return converted


def _validate_non_negative_finite_outputs(values: dict[str, float]) -> None:
    for name, value in values.items():
        if not math.isfinite(value) or value < 0.0:
            raise ArithmeticError(f"Computed {name} must be finite and non-negative.")


def compute_arrival_to_staging(
    *,
    parent_body: str,
    parent_mu_m3_s2: float,
    arrival_v_infinity_m_s: float,
    periapsis_radius_m: float,
    staging_radius_m: float,
    source: str,
    periapsis_radius_provenance: str,
    staging_radius_guard: StagingRadiusGuard | None = None,
) -> ArrivalStagingResult:
    """Capture a hyperbolic arrival into an ellipse and circularise at apoapsis.

    All numeric inputs and outputs use SI units. Body-specific geometry or
    environmental constraints are supplied as an optional staging-radius guard;
    the two-body energy equations themselves remain body agnostic.
    """
    body = _require_non_empty_string("parent_body", parent_body)
    source_name = _require_non_empty_string("source", source)
    mu = _require_finite_number("parent_mu_m3_s2", parent_mu_m3_s2)
    v_infinity = _require_finite_number("arrival_v_infinity_m_s", arrival_v_infinity_m_s)
    periapsis = _require_finite_number("periapsis_radius_m", periapsis_radius_m)
    staging = _require_finite_number("staging_radius_m", staging_radius_m)

    if mu <= 0.0:
        raise ValueError("parent_mu_m3_s2 must be positive.")
    if v_infinity < 0.0:
        raise ValueError("arrival_v_infinity_m_s must be non-negative.")
    if periapsis <= 0.0:
        raise ValueError("periapsis_radius_m must be positive.")
    if staging_radius_guard is not None:
        if not isinstance(staging_radius_guard, StagingRadiusGuard):
            raise TypeError("staging_radius_guard must be a StagingRadiusGuard or None.")
        minimum_staging_radius = _require_finite_number(
            "staging_radius_guard.minimum_radius_m",
            staging_radius_guard.minimum_radius_m,
        )
        guard_description = _require_non_empty_string(
            "staging_radius_guard.description",
            staging_radius_guard.description,
        )
        if minimum_staging_radius <= 0.0:
            raise ValueError("staging_radius_guard.minimum_radius_m must be positive.")
        if staging <= minimum_staging_radius:
            raise ValueError(
                "staging_radius_m must be greater than "
                f"{guard_description} ({minimum_staging_radius:.0f} m)."
            )
    if staging <= periapsis:
        raise ValueError("staging_radius_m must be greater than periapsis_radius_m.")
    provenance = _require_non_empty_string(
        "periapsis_radius_provenance",
        periapsis_radius_provenance,
    )

    semimajor_axis = (periapsis + staging) / 2.0
    hyperbolic_periapsis_speed = math.sqrt(v_infinity**2 + 2.0 * mu / periapsis)
    transfer_periapsis_speed = math.sqrt(mu * (2.0 / periapsis - 1.0 / semimajor_axis))
    capture_to_ellipse_delta_v = hyperbolic_periapsis_speed - transfer_periapsis_speed

    transfer_apoapsis_speed = math.sqrt(mu * (2.0 / staging - 1.0 / semimajor_axis))
    staging_circular_speed = math.sqrt(mu / staging)
    staging_circularisation_delta_v = staging_circular_speed - transfer_apoapsis_speed
    total_delta_v = capture_to_ellipse_delta_v + staging_circularisation_delta_v
    time_of_flight = math.pi * math.sqrt(semimajor_axis**3 / mu)

    _validate_non_negative_finite_outputs(
        {
            "transfer_semimajor_axis_m": semimajor_axis,
            "hyperbolic_periapsis_speed_m_s": hyperbolic_periapsis_speed,
            "transfer_periapsis_speed_m_s": transfer_periapsis_speed,
            "capture_to_ellipse_delta_v_m_s": capture_to_ellipse_delta_v,
            "transfer_apoapsis_speed_m_s": transfer_apoapsis_speed,
            "staging_circular_speed_m_s": staging_circular_speed,
            "staging_circularisation_delta_v_m_s": staging_circularisation_delta_v,
            "total_delta_v_m_s": total_delta_v,
            "time_of_flight_s": time_of_flight,
        }
    )

    return ArrivalStagingResult(
        parent_body=body,
        origin_state=f"{body} hyperbolic arrival",
        destination_state=f"{body} staging circular orbit",
        method=METHOD,
        source=source_name,
        parent_mu_m3_s2=mu,
        arrival_v_infinity_m_s=v_infinity,
        periapsis_radius_m=periapsis,
        staging_radius_m=staging,
        transfer_semimajor_axis_m=semimajor_axis,
        hyperbolic_periapsis_speed_m_s=hyperbolic_periapsis_speed,
        transfer_periapsis_speed_m_s=transfer_periapsis_speed,
        capture_to_ellipse_delta_v_m_s=capture_to_ellipse_delta_v,
        transfer_apoapsis_speed_m_s=transfer_apoapsis_speed,
        staging_circular_speed_m_s=staging_circular_speed,
        staging_circularisation_delta_v_m_s=staging_circularisation_delta_v,
        total_delta_v_m_s=total_delta_v,
        time_of_flight_s=time_of_flight,
        periapsis_radius_provenance=provenance,
        assumptions=(
            f"{body} is a point mass and both burns are tangential and impulsive.",
            "Capture targets an ellipse whose apoapsis is the circular staging radius.",
            "The two-body calculation is coplanar for energy accounting only.",
        ),
        exclusions=(
            "Body-specific collision, atmosphere, ring, and radiation hazards.",
            "Plane changes, oblateness, finite burns, perturbations, and corrections.",
        ),
    )


def adapt_arrival_staging_to_leg(
    result: ArrivalStagingResult,
    *,
    capture_epoch_mjd2000: float | None = None,
) -> Leg:
    """Adapt a generic arrival-to-staging result to canonical mission types."""
    if not isinstance(result, ArrivalStagingResult):
        raise TypeError("result must be an ArrivalStagingResult.")

    capture_epoch: float | None = None
    staging_epoch: float | None = None
    if capture_epoch_mjd2000 is not None:
        capture_epoch = _require_finite_number("capture_epoch_mjd2000", capture_epoch_mjd2000)
        staging_epoch = capture_epoch + result.time_of_flight_days

    trajectory = TrajectoryResult(
        departure_mjd2000=capture_epoch,
        arrival_mjd2000=staging_epoch,
        tof_years=result.time_of_flight_s / (DAYS_PER_JULIAN_YEAR * SECONDS_PER_DAY),
        v_inf_depart=None,
        v_inf_arrival=result.arrival_v_infinity_m_s,
        delta_v=result.total_delta_v_m_s,
        method=result.method,
        notes=f"{result.source}; body-agnostic arrival-to-staging energy model.",
    )
    events = [
        Event(
            name=f"{result.parent_body} capture-to-ellipse",
            body=result.parent_body,
            event_type="capture",
            epoch=capture_epoch,
            notes="Impulsive capture directly into the staging-transfer ellipse.",
        ),
        Event(
            name=f"{result.parent_body} staging circularisation",
            body=result.parent_body,
            event_type="insertion",
            epoch=staging_epoch,
            notes="Impulsive circularisation at the staging radius.",
        ),
    ]
    return Leg(
        origin=result.parent_body,
        destination=result.parent_body,
        trajectory=trajectory,
        events=events,
        notes=f"Preliminary energy-only {result.parent_body} arrival-to-staging phase.",
    )
