"""Typed orchestration of the preliminary Earth-to-Saturn-to-Titan chain."""

from __future__ import annotations

from dataclasses import dataclass

from .models import Leg, Mission
from .moon_transfer import (
    DEFAULT_TITAN_CAPTURE_ALTITUDE_M,
    SaturnTitanTransferResult,
    adapt_saturn_titan_transfer_to_leg,
    compute_saturn_titan_transfer,
)
from .saturn_staging import (
    DEFAULT_SATURN_STAGING_RADIUS_M,
    SaturnArrivalStagingResult,
    adapt_saturn_arrival_staging_to_leg,
    compute_saturn_arrival_to_staging,
)


@dataclass(frozen=True)
class EarthSaturnTitanMissionResult:
    """Full canonical mission plus the two independently inspectable Saturn studies."""

    mission: Mission
    saturn_arrival_staging: SaturnArrivalStagingResult
    saturn_titan_transfer: SaturnTitanTransferResult


def compute_earth_saturn_titan_mission(
    earth_saturn_leg: Leg,
    *,
    saturn_periapsis_radius_m: float,
    saturn_periapsis_radius_provenance: str,
    saturn_staging_radius_m: float = DEFAULT_SATURN_STAGING_RADIUS_M,
    titan_capture_altitude_m: float = DEFAULT_TITAN_CAPTURE_ALTITUDE_M,
) -> EarthSaturnTitanMissionResult:
    """Connect validated phase models without changing their physical calculations.

    The supplied Earth-to-Saturn leg remains unchanged. Its Saturn arrival v-infinity
    feeds the arrival-to-staging study, whose final circular radius is then used as
    the departure radius of the Saturn-to-Titan study.
    """
    if not isinstance(earth_saturn_leg, Leg):
        raise TypeError("earth_saturn_leg must be a Leg.")
    if earth_saturn_leg.origin != "Earth" or earth_saturn_leg.destination != "Saturn":
        raise ValueError("earth_saturn_leg must connect Earth to Saturn.")
    earth_saturn_trajectory = earth_saturn_leg.trajectory
    if earth_saturn_trajectory is None:
        raise ValueError("earth_saturn_leg must contain a TrajectoryResult.")
    arrival_v_infinity = earth_saturn_trajectory.v_inf_arrival
    if arrival_v_infinity is None:
        raise ValueError("earth_saturn_leg must provide Saturn arrival v-infinity.")
    departure_epoch = earth_saturn_trajectory.departure_mjd2000
    arrival_epoch = earth_saturn_trajectory.arrival_mjd2000
    if (
        departure_epoch is not None
        and arrival_epoch is not None
        and departure_epoch > arrival_epoch
    ):
        raise ValueError("earth_saturn_leg arrival epoch must not precede its departure epoch.")

    staging_study = compute_saturn_arrival_to_staging(
        arrival_v_infinity_m_s=arrival_v_infinity,
        periapsis_radius_m=saturn_periapsis_radius_m,
        staging_radius_m=saturn_staging_radius_m,
        periapsis_radius_provenance=saturn_periapsis_radius_provenance,
    )
    staging_leg = adapt_saturn_arrival_staging_to_leg(
        staging_study,
        capture_epoch_mjd2000=earth_saturn_trajectory.arrival_mjd2000,
    )

    titan_study = compute_saturn_titan_transfer(
        saturn_staging_radius_m=staging_study.staging_radius_m,
        titan_capture_altitude_m=titan_capture_altitude_m,
    )
    assert staging_leg.trajectory is not None
    titan_leg = adapt_saturn_titan_transfer_to_leg(
        titan_study,
        departure_epoch_mjd2000=staging_leg.trajectory.arrival_mjd2000,
    )

    legs = [earth_saturn_leg, staging_leg, titan_leg]
    mission = Mission(
        name="Earth -> Saturn -> Titan",
        legs=legs,
        events=[event for leg in legs for event in leg.events],
        notes=(
            "Connected preliminary chain. Phase delta-v values remain explicit and can "
            "be composed into the global propulsive and mass budgets."
        ),
    )
    return EarthSaturnTitanMissionResult(
        mission=mission,
        saturn_arrival_staging=staging_study,
        saturn_titan_transfer=titan_study,
    )
