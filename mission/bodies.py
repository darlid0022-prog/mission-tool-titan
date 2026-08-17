from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pykep as pk

from .constants import (
    CALLISTO_MU_M3_S2,
    DEIMOS_MU_M3_S2,
    EUROPA_MU_M3_S2,
    GANYMEDE_MU_M3_S2,
    IO_MU_M3_S2,
    PHOBOS_MU_M3_S2,
    CERES_MU_M3_S2,
    CERES_MEAN_RADIUS_M,
    PLUTO_MU_M3_S2,
    PLUTO_MEAN_RADIUS_M,
)

# The original body-resolution facade exposed this rounded Titan GM. Keep it
# separate from the more precise model constant so this compatibility layer
# remains bit-for-bit stable while mission physics continues using the JPL value.
_TITAN_LEGACY_RESOLUTION_MU_M3_S2 = 8.978138e12


@dataclass(frozen=True)
class CelestialBody:
    """Minimal abstraction for a celestial body used by the generic Lambert solver.

    Planets registered against a real PyKEP low-precision analytical ephemeris
    (`pk.udpla.jpl_lp`) support Lambert transfers. Moons are accepted as
    resolvable body names for compatibility and downstream (non-Lambert) use -
    for example capture delta-v at arrival - but their Lambert transfer
    propagation remains intentionally unimplemented, because this project does
    not yet model planet -> moon interplanetary-leg transfer physics as a
    single Lambert arc (see mission/moon_transfer.py for the dedicated,
    parent-body-centred transfer model used instead).
    """

    name: str
    pykep_body: Any | None = None
    mu_self: float | None = None
    supports_lambert: bool = True

    def eph(self, mjd2000):
        if self.pykep_body is None:
            raise NotImplementedError(
                f"Ephemeris for {self.name} is not implemented yet. "
                f"Lambert transfer modeling for {self.name} is intentionally disabled."
            )
        return self.pykep_body.eph(mjd2000)

    def get_mu_central_body(self) -> float:
        if self.pykep_body is not None:
            return self.pykep_body.get_mu_central_body()
        raise NotImplementedError(
            f"Central-body gravitational parameter for {self.name} is not defined."
        )

    def get_mu_self(self) -> float:
        """Return the body's own gravitational parameter for local manoeuvres."""
        if self.mu_self is not None:
            return self.mu_self
        if self.pykep_body is not None:
            return self.pykep_body.get_mu_self()
        raise NotImplementedError(f"Self gravitational parameter for {self.name} is not defined.")


def _build_jpl_lp_planet(name: str, jpl_lp_name: str) -> CelestialBody:
    """Build a Lambert-capable planet from PyKEP's low-precision ephemeris.

    Shared by every planet currently registered in SUPPORTED_BODIES (Earth,
    Saturn, and the newly added Mercury/Venus/Mars/Jupiter/Uranus/Neptune).
    Behaviour-preserving refactor: Earth and Saturn resolve to bit-identical
    CelestialBody values as before this helper existed (see the regression
    tests in tests/test_celestial_body_resolution.py).
    """
    planet = pk.planet(pk.udpla.jpl_lp(jpl_lp_name))
    return CelestialBody(
        name=name,
        pykep_body=planet,
        mu_self=planet.get_mu_self(),
        supports_lambert=True,
    )


def _build_artificial_moon(name: str, mu_self_m3_s2: float) -> CelestialBody:
    """Build a moon body with a known GM but no PyKEP ephemeris/Lambert support.

    Shared by every moon currently registered in SUPPORTED_BODIES (Titan, and
    the newly added Phobos/Deimos/Io/Europa/Ganymede/Callisto). Behaviour-
    preserving refactor for Titan: resolves to a bit-identical CelestialBody
    value as before this helper existed.
    """
    return CelestialBody(
        name=name,
        pykep_body=None,
        mu_self=mu_self_m3_s2,
        supports_lambert=False,
    )


def _build_earth() -> CelestialBody:
    return _build_jpl_lp_planet("Earth", "earth")


def _build_mercury() -> CelestialBody:
    return _build_jpl_lp_planet("Mercury", "mercury")


def _build_venus() -> CelestialBody:
    return _build_jpl_lp_planet("Venus", "venus")


def _build_mars() -> CelestialBody:
    return _build_jpl_lp_planet("Mars", "mars")


def _build_jupiter() -> CelestialBody:
    return _build_jpl_lp_planet("Jupiter", "jupiter")


def _build_saturn() -> CelestialBody:
    return _build_jpl_lp_planet("Saturn", "saturn")


def _build_uranus() -> CelestialBody:
    return _build_jpl_lp_planet("Uranus", "uranus")


def _build_neptune() -> CelestialBody:
    return _build_jpl_lp_planet("Neptune", "neptune")


def _build_titan() -> CelestialBody:
    # Titan is intentionally supported as a resolvable body name only.
    # The project does not yet model Saturn -> Titan transfer physics as a
    # single Lambert arc, so Lambert propagation remains disabled for that body.
    return _build_artificial_moon("Titan", _TITAN_LEGACY_RESOLUTION_MU_M3_S2)


def _build_phobos() -> CelestialBody:
    return _build_artificial_moon("Phobos", PHOBOS_MU_M3_S2)


def _build_deimos() -> CelestialBody:
    return _build_artificial_moon("Deimos", DEIMOS_MU_M3_S2)


def _build_io() -> CelestialBody:
    return _build_artificial_moon("Io", IO_MU_M3_S2)


def _build_europa() -> CelestialBody:
    return _build_artificial_moon("Europa", EUROPA_MU_M3_S2)


def _build_ganymede() -> CelestialBody:
    return _build_artificial_moon("Ganymede", GANYMEDE_MU_M3_S2)


def _build_callisto() -> CelestialBody:
    return _build_artificial_moon("Callisto", CALLISTO_MU_M3_S2)


def _build_ceres() -> CelestialBody:
    # Ceres is an independent small body (heliocentric) without a PyKEP
    # jpl_lp ephemeris in this project. We register it as an artificial-like
    # body (no Lambert support) with a published GM and mean radius.
    return CelestialBody(
        name="Ceres",
        pykep_body=None,
        mu_self=CERES_MU_M3_S2,
        supports_lambert=False,
    )


def _build_pluto() -> CelestialBody:
    # Pluto is similarly registered without a PyKEP ephemeris here; use the
    # published GM and mean radius constants for local manoeuvre calculations.
    return CelestialBody(
        name="Pluto",
        pykep_body=None,
        mu_self=PLUTO_MU_M3_S2,
        supports_lambert=False,
    )


SUPPORTED_BODIES = {
    "earth": _build_earth(),
    "mercury": _build_mercury(),
    "venus": _build_venus(),
    "mars": _build_mars(),
    "jupiter": _build_jupiter(),
    "saturn": _build_saturn(),
    "uranus": _build_uranus(),
    "neptune": _build_neptune(),
    "titan": _build_titan(),
    "phobos": _build_phobos(),
    "deimos": _build_deimos(),
    "io": _build_io(),
    "europa": _build_europa(),
    "ganymede": _build_ganymede(),
    "callisto": _build_callisto(),
    "ceres": _build_ceres(),
    "pluto": _build_pluto(),
}


def resolve_body(body_name: str) -> CelestialBody:
    """Resolve a supported body name to a small body abstraction."""
    if body_name is None:
        raise ValueError("Body name cannot be None.")

    name = str(body_name).strip()
    normalized = name.lower()

    try:
        return SUPPORTED_BODIES[normalized]
    except KeyError as exc:
        supported = ", ".join([body.name for body in SUPPORTED_BODIES.values()])
        raise ValueError(f"Unsupported body '{body_name}'. Supported bodies: {supported}.") from exc
