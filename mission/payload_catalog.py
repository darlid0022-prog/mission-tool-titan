"""Structured, editable instrument catalogue for the Science payload table.

This module intentionally ships **no fabricated mass, power, or data-rate
values**. Every catalogue entry is a named placeholder slot (mass_kg = 0.0,
power_w = 0.0, data_rate_bps = 0.0) inspired by the kind of instrument an
Orbiter or a Lander bound for Titan typically carries (imaging, spectrometry,
fields & particles, atmospheric science, surface science). The instrument
*names* are public knowledge; the *numeric values* are not invented here.

This mirrors the original mission-design spreadsheet's own instructions
("Get this data from similar instruments on board other satellites") - the
user is expected to fill in real, sourced figures for the instruments they
actually select, exactly as they would in that spreadsheet's Science sheet.

Do not add non-zero mass_kg / power_w / data_rate_bps to this file without a
documented, traceable source (see the project's own rule: "aucune
modification des valeurs de référence sans justification").
"""

from __future__ import annotations

from dataclasses import dataclass

PLACEHOLDER_SOURCE = (
    "To be completed by the user - add a documented reference "
    "(e.g. a flown analogous instrument) before using this row for sizing."
)


@dataclass(frozen=True)
class CatalogInstrument:
    """One named, editable instrument slot with no assumed numeric value."""

    name: str
    target: str
    category: str
    mass_kg: float = 0.0
    power_w: float = 0.0
    data_rate_bps: float = 0.0
    source: str = PLACEHOLDER_SOURCE

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Catalogue instrument name must not be empty.")
        if self.target not in ("Orbiter", "Lander"):
            raise ValueError("Catalogue instrument target must be 'Orbiter' or 'Lander'.")
        if not self.category.strip():
            raise ValueError("Catalogue instrument category must not be empty.")
        for field_name in ("mass_kg", "power_w", "data_rate_bps"):
            value = getattr(self, field_name)
            if value < 0.0:
                raise ValueError(f"Catalogue instrument {field_name} must be non-negative.")

    @property
    def label(self) -> str:
        """Multiselect-friendly label, e.g. 'Orbiter - Magnetometer (Fields & Particles)'."""
        return f"{self.target} - {self.name} ({self.category})"


ORBITER_INSTRUMENT_CATALOG: tuple[CatalogInstrument, ...] = (
    CatalogInstrument("Narrow/wide-angle camera suite", "Orbiter", "Imaging"),
    CatalogInstrument("Visible/IR mapping spectrometer", "Orbiter", "Spectrometry"),
    CatalogInstrument("UV spectrograph", "Orbiter", "Spectrometry"),
    CatalogInstrument("Magnetometer", "Orbiter", "Fields & Particles"),
    CatalogInstrument("Ion & neutral mass spectrometer", "Orbiter", "Fields & Particles"),
    CatalogInstrument("Energetic particle detector", "Orbiter", "Fields & Particles"),
    CatalogInstrument("Radio & plasma wave sensor", "Orbiter", "Fields & Particles"),
    CatalogInstrument("Radar sounder / altimeter", "Orbiter", "Remote Sensing"),
    CatalogInstrument(
        "Radio science subsystem (uses telecom hardware)", "Orbiter", "Radio Science"
    ),
)

LANDER_INSTRUMENT_CATALOG: tuple[CatalogInstrument, ...] = (
    CatalogInstrument("Descent imager / spectral radiometer", "Lander", "Imaging"),
    CatalogInstrument("Atmospheric structure instrument", "Lander", "Atmospheric Science"),
    CatalogInstrument("Gas chromatograph mass spectrometer", "Lander", "Atmospheric Science"),
    CatalogInstrument("Aerosol collector & pyrolyser", "Lander", "Atmospheric Science"),
    CatalogInstrument("Doppler wind experiment", "Lander", "Atmospheric Science"),
    CatalogInstrument("Surface science package", "Lander", "Surface Science"),
    CatalogInstrument("Seismometer / geophysics package", "Lander", "Surface Science"),
)

FULL_INSTRUMENT_CATALOG: tuple[CatalogInstrument, ...] = (
    ORBITER_INSTRUMENT_CATALOG + LANDER_INSTRUMENT_CATALOG
)


def catalog_by_label() -> dict[str, CatalogInstrument]:
    """Map every catalogue entry's multiselect label back to its instrument."""
    return {instrument.label: instrument for instrument in FULL_INSTRUMENT_CATALOG}


def catalog_row(instrument: CatalogInstrument) -> dict[str, object]:
    """Convert one catalogue instrument into a Science-payload table row."""
    return {
        "Instrument": instrument.name,
        "Cible": instrument.target,
        "Masse (kg)": instrument.mass_kg,
        "Puissance (W)": instrument.power_w,
        "Débit (bps)": instrument.data_rate_bps,
    }
