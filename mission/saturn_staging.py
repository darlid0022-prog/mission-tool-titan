"""Pure preliminary Saturn hyperbolic-arrival to staging-orbit model."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .arrival_staging import (
    DAYS_PER_JULIAN_YEAR,
    SECONDS_PER_DAY,
    StagingRadiusGuard,
    compute_arrival_to_staging,
)
from .arrival_staging import (
    METHOD as ARRIVAL_STAGING_METHOD,
)
from .constants import (
    F_RING_REFERENCE_RADIUS_M,
    JPL_SATURN_SYSTEM_SOURCE,
    SATURN_MU_M3_S2,
)
from .models import Event, Leg, TrajectoryResult

DEFAULT_SATURN_STAGING_RADIUS_M = 6.0e8
MIN_SATURN_STAGING_RADIUS_M = 4.8e8
D_RING_INNER_EDGE_RADIUS_M = 6.69e7
ALTERNATE_E_RING_OUTER_RADIUS_M = 4.82e8
METHOD = ARRIVAL_STAGING_METHOD
RING_CLEARANCE_STATUS = "unresolved"
TRANSFER_SAFETY_MARGIN_STATUS = "unestablished"
REPLACED_BUDGET_TERM = "dV Capture at Destination"


@dataclass(frozen=True)
class SaturnArrivalStagingResult:
    """Detailed typed result for the preliminary two-burn Saturn phase."""

    origin_state: str
    destination_state: str
    method: str
    source: str
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
    f_ring_radial_margin_m: float
    periapsis_below_d_ring_inner_edge_m: float
    staging_e_ring_radial_margin_m: float
    ring_clearance_status: str
    transfer_safety_margin_status: str
    periapsis_radius_provenance: str
    replaces_budget_term: str
    assumptions: tuple[str, ...]
    exclusions: tuple[str, ...]

    @property
    def time_of_flight_days(self) -> float:
        return self.time_of_flight_s / SECONDS_PER_DAY


def _require_finite_number(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise TypeError(f"{name} must be a real number in SI units.")
    converted = float(value)
    if not math.isfinite(converted):
        raise ValueError(f"{name} must be finite.")
    return converted


def compute_saturn_arrival_to_staging(
    arrival_v_infinity_m_s: float,
    periapsis_radius_m: float,
    staging_radius_m: float = DEFAULT_SATURN_STAGING_RADIUS_M,
    *,
    periapsis_radius_provenance: str,
) -> SaturnArrivalStagingResult:
    """Capture a Saturn hyperbolic arrival into an ellipse and circularise at apoapsis.

    Inputs and outputs use SI units. This energy-only model does not establish
    clearance through Saturn's ring plane and is not connected to a mission budget.
    """
    generic_result = compute_arrival_to_staging(
        parent_body="Saturn",
        parent_mu_m3_s2=SATURN_MU_M3_S2,
        arrival_v_infinity_m_s=arrival_v_infinity_m_s,
        periapsis_radius_m=periapsis_radius_m,
        staging_radius_m=staging_radius_m,
        source=JPL_SATURN_SYSTEM_SOURCE,
        periapsis_radius_provenance=periapsis_radius_provenance,
        staging_radius_guard=StagingRadiusGuard(
            minimum_radius_m=MIN_SATURN_STAGING_RADIUS_M,
            description="the preliminary outer E-ring guard",
        ),
    )

    return SaturnArrivalStagingResult(
        origin_state=generic_result.origin_state,
        destination_state=generic_result.destination_state,
        method=generic_result.method,
        source=generic_result.source,
        arrival_v_infinity_m_s=generic_result.arrival_v_infinity_m_s,
        periapsis_radius_m=generic_result.periapsis_radius_m,
        staging_radius_m=generic_result.staging_radius_m,
        transfer_semimajor_axis_m=generic_result.transfer_semimajor_axis_m,
        hyperbolic_periapsis_speed_m_s=generic_result.hyperbolic_periapsis_speed_m_s,
        transfer_periapsis_speed_m_s=generic_result.transfer_periapsis_speed_m_s,
        capture_to_ellipse_delta_v_m_s=generic_result.capture_to_ellipse_delta_v_m_s,
        transfer_apoapsis_speed_m_s=generic_result.transfer_apoapsis_speed_m_s,
        staging_circular_speed_m_s=generic_result.staging_circular_speed_m_s,
        staging_circularisation_delta_v_m_s=(generic_result.staging_circularisation_delta_v_m_s),
        total_delta_v_m_s=generic_result.total_delta_v_m_s,
        time_of_flight_s=generic_result.time_of_flight_s,
        f_ring_radial_margin_m=generic_result.periapsis_radius_m - F_RING_REFERENCE_RADIUS_M,
        periapsis_below_d_ring_inner_edge_m=(
            D_RING_INNER_EDGE_RADIUS_M - generic_result.periapsis_radius_m
        ),
        staging_e_ring_radial_margin_m=(
            generic_result.staging_radius_m - ALTERNATE_E_RING_OUTER_RADIUS_M
        ),
        ring_clearance_status=RING_CLEARANCE_STATUS,
        transfer_safety_margin_status=TRANSFER_SAFETY_MARGIN_STATUS,
        periapsis_radius_provenance=generic_result.periapsis_radius_provenance,
        replaces_budget_term=REPLACED_BUDGET_TERM,
        assumptions=(
            "Saturn is a point mass and both burns are tangential and impulsive.",
            "Capture targets an ellipse whose apoapsis is the circular staging radius.",
            "The two-body calculation is coplanar for energy accounting only.",
        ),
        exclusions=(
            "Ring-plane geometry, particle environment, and collision risk.",
            "Plane changes, oblateness, finite burns, perturbations, and corrections.",
            "Legacy circular Saturn capture, which this architecture replaces.",
        ),
    )


def adapt_saturn_arrival_staging_to_leg(
    result: SaturnArrivalStagingResult,
    *,
    capture_epoch_mjd2000: float | None = None,
) -> Leg:
    """Adapt a computed phase into the existing canonical mission-domain types."""
    if not isinstance(result, SaturnArrivalStagingResult):
        raise TypeError("result must be a SaturnArrivalStagingResult.")

    capture_epoch: float | None = None
    staging_epoch: float | None = None
    if capture_epoch_mjd2000 is not None:
        capture_epoch = _require_finite_number("capture_epoch_mjd2000", capture_epoch_mjd2000)
        staging_epoch = capture_epoch + result.time_of_flight_s / SECONDS_PER_DAY

    trajectory = TrajectoryResult(
        departure_mjd2000=capture_epoch,
        arrival_mjd2000=staging_epoch,
        tof_years=result.time_of_flight_s / (DAYS_PER_JULIAN_YEAR * SECONDS_PER_DAY),
        v_inf_depart=None,
        v_inf_arrival=result.arrival_v_infinity_m_s,
        delta_v=result.total_delta_v_m_s,
        method=result.method,
        notes=(
            f"{result.source}; ring clearance {result.ring_clearance_status}; "
            f"replaces budget term '{result.replaces_budget_term}'."
        ),
    )
    events = [
        Event(
            name="Saturn capture-to-ellipse",
            body="Saturn",
            event_type="capture",
            epoch=capture_epoch,
            notes="Impulsive capture directly into the staging-transfer ellipse.",
        ),
        Event(
            name="Saturn staging circularisation",
            body="Saturn",
            event_type="insertion",
            epoch=staging_epoch,
            notes="Impulsive circularisation at the staging radius.",
        ),
    ]
    return Leg(
        origin="Saturn",
        destination="Saturn",
        trajectory=trajectory,
        events=events,
        notes="Preliminary energy-only Saturn arrival-to-staging phase.",
    )
