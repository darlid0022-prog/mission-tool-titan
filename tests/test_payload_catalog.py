"""Tests for the structured, zero-value instrument catalogue."""

import unittest

from mission.payload_catalog import (
    FULL_INSTRUMENT_CATALOG,
    LANDER_INSTRUMENT_CATALOG,
    ORBITER_INSTRUMENT_CATALOG,
    CatalogInstrument,
    catalog_by_label,
    catalog_row,
)


class TestCatalogInstrument(unittest.TestCase):
    def test_rejects_empty_name(self) -> None:
        with self.assertRaises(ValueError):
            CatalogInstrument("  ", "Orbiter", "Imaging")

    def test_rejects_invalid_target(self) -> None:
        with self.assertRaises(ValueError):
            CatalogInstrument("Camera", "Rover", "Imaging")

    def test_rejects_empty_category(self) -> None:
        with self.assertRaises(ValueError):
            CatalogInstrument("Camera", "Orbiter", "  ")

    def test_rejects_negative_values(self) -> None:
        with self.assertRaises(ValueError):
            CatalogInstrument("Camera", "Orbiter", "Imaging", mass_kg=-1.0)

    def test_label_format(self) -> None:
        instrument = CatalogInstrument("Magnetometer", "Orbiter", "Fields & Particles")
        self.assertEqual(instrument.label, "Orbiter - Magnetometer (Fields & Particles)")


class TestCatalogContents(unittest.TestCase):
    def test_catalogues_are_non_empty(self) -> None:
        self.assertGreater(len(ORBITER_INSTRUMENT_CATALOG), 0)
        self.assertGreater(len(LANDER_INSTRUMENT_CATALOG), 0)

    def test_full_catalog_is_union_of_orbiter_and_lander(self) -> None:
        self.assertEqual(
            FULL_INSTRUMENT_CATALOG,
            ORBITER_INSTRUMENT_CATALOG + LANDER_INSTRUMENT_CATALOG,
        )

    def test_orbiter_entries_target_orbiter(self) -> None:
        for instrument in ORBITER_INSTRUMENT_CATALOG:
            self.assertEqual(instrument.target, "Orbiter")

    def test_lander_entries_target_lander(self) -> None:
        for instrument in LANDER_INSTRUMENT_CATALOG:
            self.assertEqual(instrument.target, "Lander")

    def test_no_fabricated_numeric_values(self) -> None:
        """Every shipped catalogue entry must be a zero-value placeholder."""
        for instrument in FULL_INSTRUMENT_CATALOG:
            self.assertEqual(instrument.mass_kg, 0.0)
            self.assertEqual(instrument.power_w, 0.0)
            self.assertEqual(instrument.data_rate_bps, 0.0)

    def test_names_are_unique(self) -> None:
        names = [instrument.name for instrument in FULL_INSTRUMENT_CATALOG]
        self.assertEqual(len(names), len(set(names)))

    def test_labels_are_unique(self) -> None:
        labels = [instrument.label for instrument in FULL_INSTRUMENT_CATALOG]
        self.assertEqual(len(labels), len(set(labels)))


class TestCatalogHelpers(unittest.TestCase):
    def test_catalog_by_label_round_trips(self) -> None:
        mapping = catalog_by_label()
        self.assertEqual(len(mapping), len(FULL_INSTRUMENT_CATALOG))
        for instrument in FULL_INSTRUMENT_CATALOG:
            self.assertIs(mapping[instrument.label], instrument)

    def test_catalog_row_shape(self) -> None:
        instrument = CatalogInstrument("Camera", "Orbiter", "Imaging")
        row = catalog_row(instrument)
        self.assertEqual(
            row,
            {
                "Instrument": "Camera",
                "Cible": "Orbiter",
                "Masse (kg)": 0.0,
                "Puissance (W)": 0.0,
                "Débit (bps)": 0.0,
            },
        )

    def test_catalog_row_matches_science_table_columns(self) -> None:
        expected_columns = {"Instrument", "Cible", "Masse (kg)", "Puissance (W)", "Débit (bps)"}
        for instrument in FULL_INSTRUMENT_CATALOG:
            self.assertEqual(set(catalog_row(instrument).keys()), expected_columns)


if __name__ == "__main__":
    unittest.main()
