import unittest

import pandas as pd

from mission.sizing import compute_mass_budget


class TestMassBudget(unittest.TestCase):
    def test_zero_delta_v_requires_no_propellant(self):
        instruments = pd.DataFrame({"Masse (kg)": [10.0, 5.0]})

        result = compute_mass_budget(0.0, 320.0, instruments)

        self.assertEqual(result["instrument_mass_kg"], 15.0)
        self.assertEqual(result["propellant_mass_kg"], 0.0)
        self.assertEqual(result["wet_mass_kg"], result["dry_mass_kg"])

    def test_instrument_mass_changes_only_sizing_inputs(self):
        light = pd.DataFrame({"Masse (kg)": [10.0]})
        heavy = pd.DataFrame({"Masse (kg)": [20.0]})

        light_result = compute_mass_budget(1000.0, 320.0, light)
        heavy_result = compute_mass_budget(1000.0, 320.0, heavy)

        self.assertEqual(heavy_result["dry_mass_kg"], 2 * light_result["dry_mass_kg"])
        self.assertEqual(heavy_result["wet_mass_kg"], 2 * light_result["wet_mass_kg"])


if __name__ == "__main__":
    unittest.main()
