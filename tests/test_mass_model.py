import math
import unittest

from mission.constants import G0_M_S2
from mission.mass_model import (
    HESPEROS_MODEL_VERSION,
    Manoeuvre,
    MassArchitectureInfeasibleError,
    ParametricBusCoefficients,
    PayloadItem,
    size_parametric_vehicle,
)


class TestParametricMassModel(unittest.TestCase):
    def setUp(self):
        self.hesperos_payload = (PayloadItem("Hesperos payload", 271.2, 551.4),)

    def test_hesperos_coefficients_reproduce_published_subsystems(self):
        result = size_parametric_vehicle(self.hesperos_payload, ())

        self.assertEqual(result.model_version, HESPEROS_MODEL_VERSION)
        self.assertAlmostEqual(result.subsystems.payload_kg, 271.2, places=8)
        self.assertAlmostEqual(result.subsystems.aocs_kg, 59.6, places=7)
        self.assertAlmostEqual(result.subsystems.communications_kg, 68.0, places=7)
        self.assertAlmostEqual(result.subsystems.data_handling_kg, 53.8, places=7)
        self.assertAlmostEqual(result.subsystems.thermal_kg, 5.3, places=7)
        self.assertAlmostEqual(result.subsystems.power_kg, 50.4, places=7)
        self.assertAlmostEqual(result.subsystems.structure_mechanisms_kg, 250.1, places=7)
        self.assertAlmostEqual(result.subsystems.fixed_unmargined_kg, 758.4, places=7)

    def test_zero_delta_v_has_no_propellant_or_propulsion_dry_mass(self):
        result = size_parametric_vehicle(
            self.hesperos_payload,
            (Manoeuvre("Coast correction", 0.0, 320.0),),
        )

        self.assertEqual(result.propellant_mass_kg, 0.0)
        self.assertEqual(result.propulsion_dry_mass_kg, 0.0)
        self.assertEqual(result.wet_mass_kg, result.dry_mass_kg)
        self.assertAlmostEqual(result.dry_mass_kg, 758.4 * 1.2, places=7)

    def test_payload_scaling_preserves_hesperos_non_propulsion_composition(self):
        baseline = size_parametric_vehicle(self.hesperos_payload, ())
        doubled = size_parametric_vehicle(
            (PayloadItem("Double Hesperos payload", 542.4, 1_102.8),),
            (),
        )

        self.assertAlmostEqual(
            doubled.subsystems.fixed_unmargined_kg,
            2.0 * baseline.subsystems.fixed_unmargined_kg,
            places=7,
        )
        self.assertAlmostEqual(
            doubled.subsystems.structure_mechanisms_kg,
            2.0 * baseline.subsystems.structure_mechanisms_kg,
            places=7,
        )
        self.assertAlmostEqual(doubled.dry_mass_kg, 2.0 * baseline.dry_mass_kg, places=7)
        self.assertAlmostEqual(
            doubled.subsystems.structure_mechanisms_kg / doubled.subsystems.fixed_unmargined_kg,
            250.1 / 758.4,
            places=9,
        )

    def test_feasible_coupled_solution_matches_independent_closed_form(self):
        coefficients = ParametricBusCoefficients(propulsion_dry_per_propellant=0.12)
        delta_v = 1_000.0
        isp = 320.0
        result = size_parametric_vehicle(
            self.hesperos_payload,
            (Manoeuvre("Reference burn", delta_v, isp),),
            coefficients,
        )

        ratio = math.exp(delta_v / (isp * G0_M_S2))
        fixed = result.subsystems.fixed_unmargined_kg
        margin_factor = 1.0 + coefficients.system_margin_fraction
        expected_dry = (
            margin_factor
            * fixed
            / (1.0 - margin_factor * coefficients.propulsion_dry_per_propellant * (ratio - 1.0))
        )
        expected_propellant = expected_dry * (ratio - 1.0)

        self.assertAlmostEqual(result.dry_mass_kg, expected_dry, places=6)
        self.assertAlmostEqual(result.propellant_mass_kg, expected_propellant, places=6)
        self.assertAlmostEqual(
            result.propulsion_dry_mass_kg,
            coefficients.propulsion_dry_per_propellant * expected_propellant,
            places=6,
        )

    def test_mixed_isp_ledger_preserves_chronological_order(self):
        manoeuvres = (
            Manoeuvre("Departure", 250.0, 320.0),
            Manoeuvre("Capture", 150.0, 290.0),
        )
        result = size_parametric_vehicle(
            self.hesperos_payload,
            manoeuvres,
            ParametricBusCoefficients(propulsion_dry_per_propellant=0.05),
        )

        self.assertEqual(
            tuple(entry.name for entry in result.manoeuvre_ledger),
            ("Departure", "Capture"),
        )
        departure, capture = result.manoeuvre_ledger
        self.assertAlmostEqual(departure.mass_after_kg, capture.mass_before_kg, places=9)
        self.assertAlmostEqual(capture.mass_after_kg, result.dry_mass_kg, places=9)
        self.assertAlmostEqual(
            sum(entry.propellant_kg for entry in result.manoeuvre_ledger),
            result.propellant_mass_kg,
            places=9,
        )

    def test_direct_titan_chemical_architecture_is_reported_infeasible(self):
        with self.assertRaisesRegex(MassArchitectureInfeasibleError, "diverge|did not converge"):
            size_parametric_vehicle(
                self.hesperos_payload,
                (Manoeuvre("Direct mission", 16_284.134, 320.0),),
            )

    def test_empty_payload_is_explicitly_incomplete(self):
        result = size_parametric_vehicle((), ())

        self.assertFalse(result.complete)
        self.assertIn("empty", result.messages[0])
        self.assertEqual(result.wet_mass_kg, 0.0)

    def test_rejects_invalid_inputs(self):
        with self.assertRaisesRegex(ValueError, "mass_kg"):
            PayloadItem("Invalid", -1.0)
        with self.assertRaisesRegex(ValueError, "isp_s"):
            Manoeuvre("Invalid", 1.0, 0.0)
        with self.assertRaisesRegex(ValueError, "less than 1"):
            ParametricBusCoefficients(system_margin_fraction=1.0)
        with self.assertRaisesRegex(ValueError, "max_iterations"):
            size_parametric_vehicle(self.hesperos_payload, (), max_iterations=0)


if __name__ == "__main__":
    unittest.main()
