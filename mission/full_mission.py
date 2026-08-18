"""Typed orchestration of preliminary Earth-to-destination mission chains."""

from __future__ import annotations

from dataclasses import dataclass

from .connected_physics import ConnectedFirstOrderResult, compute_connected_first_order_chain
from .arrival_staging import (
    ArrivalStagingResult,
    StagingRadiusGuard,
    adapt_arrival_staging_to_leg,
    compute_arrival_to_staging,
)
from .models import Leg, Mission, TrajectoryResult
from .moon_transfer import (
    DEFAULT_TITAN_CAPTURE_ALTITUDE_M,
    SaturnTitanTransferResult,
    adapt_saturn_titan_transfer_to_leg,
    compute_saturn_titan_transfer,
)
from .parent_moon_transfer import (
    ParentMoonTransferResult,
    adapt_parent_moon_transfer_to_leg,
    compute_parent_to_moon_transfer,
)
from .saturn_staging import (
    DEFAULT_SATURN_STAGING_RADIUS_M,
    SaturnArrivalStagingResult,
    adapt_saturn_arrival_staging_to_leg,
    compute_saturn_arrival_to_staging,
)


def _validate_earth_leg(earth_leg: Leg, destination_planet: str) -> TrajectoryResult:
    """Validate an Earth-departure leg shared by every mission-building path."""
    if not isinstance(earth_leg, Leg):
        raise TypeError("earth_leg must be a Leg.")
    if earth_leg.origin != "Earth" or earth_leg.destination != destination_planet:
        raise ValueError(f"earth_leg must connect Earth to {destination_planet}.")
    earth_trajectory = earth_leg.trajectory
    if earth_trajectory is None:
        raise ValueError("earth_leg must contain a TrajectoryResult.")
    if earth_trajectory.v_inf_arrival is None:
        raise ValueError(f"earth_leg must provide {destination_planet} arrival v-infinity.")
    departure_epoch = earth_trajectory.departure_mjd2000
    arrival_epoch = earth_trajectory.arrival_mjd2000
    if (
        departure_epoch is not None
        and arrival_epoch is not None
        and departure_epoch > arrival_epoch
    ):
        raise ValueError("earth_leg arrival epoch must not precede its departure epoch.")
    return earth_trajectory


def _assemble_earth_destination_mission(
    destination_planet: str,
    moon: str | None,
    legs: list[Leg],
) -> Mission:
    """Build the canonical Mission shared by every planet/moon destination."""
    if moon is None:
        name = f"Earth -> {destination_planet}"
        notes = "Direct single-leg planetary arrival; no staging or capture maneuver is modeled yet."
    else:
        name = f"Earth -> {destination_planet} -> {moon}"
        notes = (
            "Connected preliminary chain. Phase delta-v values remain explicit and can "
            "be composed into the global propulsive and mass budgets."
        )
    return Mission(
        name=name,
        legs=legs,
        events=[event for leg in legs for event in leg.events],
        notes=notes,
    )


@dataclass(frozen=True)
class EarthDestinationMissionResult:
    """Generic Earth-departure mission plus its optional arrival/moon studies.

    `arrival_staging` and `moon_transfer` are populated only when the mission
    includes a moon leg (see MOON_DESTINATIONS in mission/capabilities.py); a
    plain single-leg PLANET_DESTINATIONS arrival leaves both None.
    """

    mission: Mission
    arrival_staging: ArrivalStagingResult | None
    moon_transfer: ParentMoonTransferResult | None


def compute_earth_destination_mission(
    earth_leg: Leg,
    *,
    destination_planet: str,
    moon: str | None = None,
    parent_mu_m3_s2: float | None = None,
    parent_periapsis_radius_m: float | None = None,
    parent_periapsis_radius_provenance: str | None = None,
    parent_staging_radius_m: float | None = None,
    parent_staging_radius_guard: StagingRadiusGuard | None = None,
    parent_source: str | None = None,
    moon_mu_m3_s2: float | None = None,
    moon_radius_m: float | None = None,
    moon_orbit_radius_m: float | None = None,
    moon_capture_altitude_m: float | None = None,
    moon_source: str | None = None,
) -> EarthDestinationMissionResult:
    """Assemble an Earth-departure mission to any destination in capabilities.py.

    `earth_leg` is the already-solved Earth-to-`destination_planet` Lambert leg
    (see mission/leg_solver.py); `destination_planet` must match its
    `destination`.

    Passing `moon=None` builds the PLANET_DESTINATIONS case: a single-leg
    mission with no staging or capture maneuver modeled yet.

    Passing a `moon` name builds the MOON_DESTINATIONS case: it additionally
    chains the generic hyperbolic-arrival-to-staging model
    (`arrival_staging.compute_arrival_to_staging`) and the generic
    parent-to-moon Hohmann transfer model
    (`parent_moon_transfer.compute_parent_to_moon_transfer`) - the same
    architecture the Saturn/Titan facades below (`compute_saturn_arrival_to_staging`,
    `compute_saturn_titan_transfer`) are themselves built on - which requires
    every `parent_*`/`moon_*` keyword parameter describing that specific pair.
    """
    earth_trajectory = _validate_earth_leg(earth_leg, destination_planet)

    if moon is None:
        mission = _assemble_earth_destination_mission(destination_planet, None, [earth_leg])
        return EarthDestinationMissionResult(mission=mission, arrival_staging=None, moon_transfer=None)

    required = {
        "parent_mu_m3_s2": parent_mu_m3_s2,
        "parent_periapsis_radius_m": parent_periapsis_radius_m,
        "parent_periapsis_radius_provenance": parent_periapsis_radius_provenance,
        "parent_staging_radius_m": parent_staging_radius_m,
        "parent_source": parent_source,
        "moon_mu_m3_s2": moon_mu_m3_s2,
        "moon_radius_m": moon_radius_m,
        "moon_orbit_radius_m": moon_orbit_radius_m,
        "moon_capture_altitude_m": moon_capture_altitude_m,
        "moon_source": moon_source,
    }
    missing = [name for name, value in required.items() if value is None]
    if missing:
        raise ValueError(f"A moon destination ({moon}) requires: {', '.join(missing)}.")

    staging_study = compute_arrival_to_staging(
        parent_body=destination_planet,
        parent_mu_m3_s2=parent_mu_m3_s2,
        arrival_v_infinity_m_s=earth_trajectory.v_inf_arrival,
        periapsis_radius_m=parent_periapsis_radius_m,
        staging_radius_m=parent_staging_radius_m,
        source=parent_source,
        periapsis_radius_provenance=parent_periapsis_radius_provenance,
        staging_radius_guard=parent_staging_radius_guard,
    )
    staging_leg = adapt_arrival_staging_to_leg(
        staging_study,
        capture_epoch_mjd2000=earth_trajectory.arrival_mjd2000,
    )

    moon_study = compute_parent_to_moon_transfer(
        parent_body=destination_planet,
        moon_body=moon,
        parent_mu_m3_s2=parent_mu_m3_s2,
        moon_mu_m3_s2=moon_mu_m3_s2,
        moon_radius_m=moon_radius_m,
        parent_staging_radius_m=staging_study.staging_radius_m,
        moon_orbit_radius_m=moon_orbit_radius_m,
        moon_capture_altitude_m=moon_capture_altitude_m,
        source=moon_source,
    )
    assert staging_leg.trajectory is not None
    moon_leg = adapt_parent_moon_transfer_to_leg(
        moon_study,
        departure_epoch_mjd2000=staging_leg.trajectory.arrival_mjd2000,
    )

    mission = _assemble_earth_destination_mission(
        destination_planet, moon, [earth_leg, staging_leg, moon_leg]
    )
    return EarthDestinationMissionResult(
        mission=mission,
        arrival_staging=staging_study,
        moon_transfer=moon_study,
    )


@dataclass(frozen=True)
class EarthSaturnTitanMissionResult:
    """Full canonical mission plus the two independently inspectable Saturn studies."""

    mission: Mission
    saturn_arrival_staging: SaturnArrivalStagingResult
    saturn_titan_transfer: SaturnTitanTransferResult
    connected_first_order: ConnectedFirstOrderResult


def compute_earth_saturn_titan_mission(
    earth_saturn_leg: Leg,
    *,
    saturn_periapsis_radius_m: float,
    saturn_periapsis_radius_provenance: str,
    saturn_staging_radius_m: float = DEFAULT_SATURN_STAGING_RADIUS_M,
    titan_capture_altitude_m: float = DEFAULT_TITAN_CAPTURE_ALTITUDE_M,
) -> EarthSaturnTitanMissionResult:
    """Legacy Earth -> Saturn -> Titan facade, thin around compute_earth_destination_mission.

    Connect validated phase models without changing their physical calculations.
    The supplied Earth-to-Saturn leg remains unchanged. Its Saturn arrival v-infinity
    feeds the arrival-to-staging study, whose final circular radius is then used as
    the departure radius of the Saturn-to-Titan study.

    This keeps calling the decorated Saturn/Titan-specific studies
    (`compute_saturn_arrival_to_staging`, `compute_saturn_titan_transfer`) directly,
    so their extra ring-margin fields and Saturn/Titan-specific guards remain exactly
    as before this generalization; only the Earth-leg validation and Mission-assembly
    boilerplate are now shared with compute_earth_destination_mission above (the same
    pattern mission/saturn_staging.py uses to wrap mission/arrival_staging.py).
    """
    earth_saturn_trajectory = _validate_earth_leg(earth_saturn_leg, "Saturn")
    arrival_v_infinity = earth_saturn_trajectory.v_inf_arrival
    assert arrival_v_infinity is not None

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

    mission = _assemble_earth_destination_mission(
        "Saturn", "Titan", [earth_saturn_leg, staging_leg, titan_leg]
    )
    return EarthSaturnTitanMissionResult(
        mission=mission,
        saturn_arrival_staging=staging_study,
        saturn_titan_transfer=titan_study,
        connected_first_order=compute_connected_first_order_chain(),
    )
