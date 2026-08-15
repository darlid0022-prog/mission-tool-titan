from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pykep as pk


@dataclass(frozen=True)
class CelestialBody:
    """Minimal abstraction for a celestial body used by the generic Lambert solver.

    Earth and Saturn use real PyKEP ephemerides. Titan is accepted as a supported
    body name for compatibility and resolution checks, but its Lambert transfer
    propagation remains intentionally unimplemented because the project does not yet
    model Saturn -> Titan transfer physics.
    """

    name: str
    pykep_body: Any | None = None
    mu_self: float | None = None
    supports_lambert: bool = True

    def eph(self, mjd2000):
        if self.pykep_body is None:
            raise NotImplementedError(
                f"Ephemeris for {self.name} is not implemented yet. "
                "Lambert transfer modeling for Titan is intentionally disabled."
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


def _build_earth() -> CelestialBody:
    planet = pk.planet(pk.udpla.jpl_lp("earth"))
    return CelestialBody(
        name="Earth",
        pykep_body=planet,
        mu_self=planet.get_mu_self(),
        supports_lambert=True,
    )


def _build_saturn() -> CelestialBody:
    planet = pk.planet(pk.udpla.jpl_lp("saturn"))
    return CelestialBody(
        name="Saturn",
        pykep_body=planet,
        mu_self=planet.get_mu_self(),
        supports_lambert=True,
    )


def _build_titan() -> CelestialBody:
    # Titan is intentionally supported as a resolvable body name only.
    # The project does not yet model Saturn -> Titan transfer physics, so
    # Lambert propagation remains disabled for that body.
    return CelestialBody(
        name="Titan",
        pykep_body=None,
        mu_self=8.978138e12,
        supports_lambert=False,
    )


SUPPORTED_BODIES = {
    "earth": _build_earth(),
    "saturn": _build_saturn(),
    "titan": _build_titan(),
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
