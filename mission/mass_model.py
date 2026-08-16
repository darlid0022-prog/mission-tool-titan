"""Pure parametric spacecraft mass model calibrated against Hesperos."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .constants import G0_M_S2

HESPEROS_MODEL_VERSION = "hesperos_payload_scaled_v1"


class MassArchitectureInfeasibleError(ValueError):
    """Raised when dry propulsion mass and propellant mass cannot converge."""


def _finite_non_negative(name: str, value: float) -> float:
    converted = float(value)
    if not math.isfinite(converted) or converted < 0.0:
        raise ValueError(f"{name} must be finite and non-negative.")
    return converted


def _finite_positive(name: str, value: float) -> float:
    converted = float(value)
    if not math.isfinite(converted) or converted <= 0.0:
        raise ValueError(f"{name} must be finite and positive.")
    return converted


@dataclass(frozen=True)
class PayloadItem:
    """One payload item and its sizing resources."""

    name: str
    mass_kg: float
    max_power_w: float = 0.0
    data_rate_bps: float = 0.0

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Payload item name must not be empty.")
        _finite_non_negative("payload mass_kg", self.mass_kg)
        _finite_non_negative("payload max_power_w", self.max_power_w)
        _finite_non_negative("payload data_rate_bps", self.data_rate_bps)


@dataclass(frozen=True)
class Manoeuvre:
    """One chronological propulsive manoeuvre."""

    name: str
    delta_v_m_s: float
    isp_s: float

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Manoeuvre name must not be empty.")
        _finite_non_negative("manoeuvre delta_v_m_s", self.delta_v_m_s)
        _finite_positive("manoeuvre isp_s", self.isp_s)


@dataclass(frozen=True)
class ParametricBusCoefficients:
    """Payload-scaled Hesperos subsystem coefficients."""

    aocs_per_payload: float = 0.2197640118
    communications_per_payload: float = 0.2507374631
    data_handling_per_payload: float = 0.1983775811
    thermal_per_payload: float = 0.0195427729
    power_per_payload: float = 0.1858407080
    structure_per_payload: float = 0.9221976401
    propulsion_dry_per_propellant: float = 0.3483060525
    system_margin_fraction: float = 0.20

    def __post_init__(self) -> None:
        for name in (
            "aocs_per_payload",
            "communications_per_payload",
            "data_handling_per_payload",
            "thermal_per_payload",
            "power_per_payload",
            "structure_per_payload",
            "propulsion_dry_per_propellant",
            "system_margin_fraction",
        ):
            value = _finite_non_negative(name, getattr(self, name))
            if name == "system_margin_fraction" and value >= 1.0:
                raise ValueError("system_margin_fraction must be less than 1.")


@dataclass(frozen=True)
class SubsystemMasses:
    """Unmargined non-propulsion subsystem masses."""

    payload_kg: float
    aocs_kg: float
    communications_kg: float
    data_handling_kg: float
    thermal_kg: float
    power_kg: float
    structure_mechanisms_kg: float

    @property
    def fixed_unmargined_kg(self) -> float:
        return sum(
            (
                self.payload_kg,
                self.aocs_kg,
                self.communications_kg,
                self.data_handling_kg,
                self.thermal_kg,
                self.power_kg,
                self.structure_mechanisms_kg,
            )
        )


@dataclass(frozen=True)
class MassLedgerEntry:
    """Mass state across one manoeuvre."""

    name: str
    delta_v_m_s: float
    isp_s: float
    mass_before_kg: float
    mass_after_kg: float
    propellant_kg: float


@dataclass(frozen=True)
class ParametricMassResult:
    """Auditable result of one vehicle sizing calculation."""

    model_version: str
    complete: bool
    messages: tuple[str, ...]
    payload_power_w: float
    payload_data_rate_bps: float
    subsystems: SubsystemMasses
    propulsion_dry_mass_kg: float
    system_margin_kg: float
    dry_mass_kg: float
    propellant_mass_kg: float
    wet_mass_kg: float
    mass_ratio: float
    iterations: int
    manoeuvre_ledger: tuple[MassLedgerEntry, ...]


def _subsystem_masses(
    payload_mass_kg: float, coefficients: ParametricBusCoefficients
) -> SubsystemMasses:
    return SubsystemMasses(
        payload_kg=payload_mass_kg,
        aocs_kg=payload_mass_kg * coefficients.aocs_per_payload,
        communications_kg=payload_mass_kg * coefficients.communications_per_payload,
        data_handling_kg=payload_mass_kg * coefficients.data_handling_per_payload,
        thermal_kg=payload_mass_kg * coefficients.thermal_per_payload,
        power_kg=payload_mass_kg * coefficients.power_per_payload,
        structure_mechanisms_kg=payload_mass_kg * coefficients.structure_per_payload,
    )


def _reverse_manoeuvre_ledger(
    dry_mass_kg: float, manoeuvres: tuple[Manoeuvre, ...]
) -> tuple[float, tuple[MassLedgerEntry, ...]]:
    mass_after = dry_mass_kg
    reverse_entries: list[MassLedgerEntry] = []
    for manoeuvre in reversed(manoeuvres):
        exponent = manoeuvre.delta_v_m_s / (manoeuvre.isp_s * G0_M_S2)
        try:
            mass_before = mass_after * math.exp(exponent)
        except OverflowError as error:
            raise MassArchitectureInfeasibleError(
                f"Manoeuvre {manoeuvre.name!r} produces an infinite mass ratio."
            ) from error
        if not math.isfinite(mass_before):
            raise MassArchitectureInfeasibleError(
                f"Manoeuvre {manoeuvre.name!r} produces an infinite mass ratio."
            )
        reverse_entries.append(
            MassLedgerEntry(
                name=manoeuvre.name,
                delta_v_m_s=manoeuvre.delta_v_m_s,
                isp_s=manoeuvre.isp_s,
                mass_before_kg=mass_before,
                mass_after_kg=mass_after,
                propellant_kg=mass_before - mass_after,
            )
        )
        mass_after = mass_before
    return mass_after, tuple(reversed(reverse_entries))


def size_parametric_vehicle(
    payload: tuple[PayloadItem, ...],
    manoeuvres: tuple[Manoeuvre, ...],
    coefficients: ParametricBusCoefficients | None = None,
    *,
    relative_tolerance: float = 1e-10,
    max_iterations: int = 200,
) -> ParametricMassResult:
    """Size one vehicle using Hesperos ratios and a coupled propulsion model."""
    coefficients = coefficients or ParametricBusCoefficients()
    tolerance = _finite_positive("relative_tolerance", relative_tolerance)
    if isinstance(max_iterations, bool) or not isinstance(max_iterations, int):
        raise TypeError("max_iterations must be an integer.")
    if max_iterations <= 0:
        raise ValueError("max_iterations must be positive.")

    payload_mass = sum(item.mass_kg for item in payload)
    payload_power = sum(item.max_power_w for item in payload)
    payload_data_rate = sum(item.data_rate_bps for item in payload)
    subsystems = _subsystem_masses(payload_mass, coefficients)
    margin_factor = 1.0 + coefficients.system_margin_fraction

    messages: list[str] = []
    if not payload:
        messages.append("Payload catalogue is empty; mass result is incomplete.")

    propulsion_dry = 0.0
    previous_wet_mass = -1.0
    final_ledger: tuple[MassLedgerEntry, ...] = ()
    propellant_mass = 0.0
    dry_mass = 0.0

    for iteration in range(1, max_iterations + 1):
        unmargined_dry = subsystems.fixed_unmargined_kg + propulsion_dry
        dry_mass = unmargined_dry * margin_factor
        wet_mass, final_ledger = _reverse_manoeuvre_ledger(dry_mass, manoeuvres)
        propellant_mass = wet_mass - dry_mass
        next_propulsion_dry = coefficients.propulsion_dry_per_propellant * propellant_mass

        if not math.isfinite(next_propulsion_dry) or (
            previous_wet_mass >= 0.0 and wet_mass > previous_wet_mass * 10.0
        ):
            raise MassArchitectureInfeasibleError(
                "Propulsion dry mass and propellant mass diverge for this architecture."
            )

        scale = max(1.0, abs(next_propulsion_dry))
        if abs(next_propulsion_dry - propulsion_dry) <= tolerance * scale:
            propulsion_dry = next_propulsion_dry
            unmargined_dry = subsystems.fixed_unmargined_kg + propulsion_dry
            dry_mass = unmargined_dry * margin_factor
            wet_mass, final_ledger = _reverse_manoeuvre_ledger(dry_mass, manoeuvres)
            propellant_mass = wet_mass - dry_mass
            break

        previous_wet_mass = wet_mass
        propulsion_dry = next_propulsion_dry
    else:
        raise MassArchitectureInfeasibleError(
            "Propulsion dry mass and propellant mass did not converge within "
            f"{max_iterations} iterations."
        )

    system_margin = (
        subsystems.fixed_unmargined_kg + propulsion_dry
    ) * coefficients.system_margin_fraction
    mass_ratio = wet_mass / dry_mass if dry_mass > 0.0 else 1.0
    return ParametricMassResult(
        model_version=HESPEROS_MODEL_VERSION,
        complete=bool(payload),
        messages=tuple(messages),
        payload_power_w=payload_power,
        payload_data_rate_bps=payload_data_rate,
        subsystems=subsystems,
        propulsion_dry_mass_kg=propulsion_dry,
        system_margin_kg=system_margin,
        dry_mass_kg=dry_mass,
        propellant_mass_kg=propellant_mass,
        wet_mass_kg=wet_mass,
        mass_ratio=mass_ratio,
        iterations=iteration,
        manoeuvre_ledger=final_ledger,
    )
