import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


class TestSaturnTitanUi(unittest.TestCase):
    @staticmethod
    def _run_app():
        earth_saturn_result = {
            "note": "Test Earth-to-Saturn result",
            "dv_budget": {"Earth departure": 1_000.0},
            "dv_total": 1_000.0,
        }
        with patch("app_services.compute_cached_trajectory", return_value=earth_saturn_result):
            return AppTest.from_file(APP_PATH).run(timeout=30)

    def test_preliminary_section_displays_nominal_results_and_source(self):
        app = self._run_app()

        self.assertFalse(app.exception)
        self.assertTrue(
            any(heading.value == "Saturne → Titan — modèle préliminaire" for heading in app.header)
        )
        metrics = {metric.label: metric.value for metric in app.metric}
        self.assertEqual(metrics["ΔV de départ depuis l'orbite d'attente"], "1,257.6 m/s")
        self.assertEqual(metrics["v∞ relatif à Titan (non propulsif)"], "1,049.8 m/s")
        self.assertEqual(metrics["ΔV de capture à Titan"], "862.7 m/s")
        self.assertEqual(metrics["ΔV total modélisé (partiel)"], "2,120.3 m/s")
        self.assertEqual(metrics["Temps de vol Saturne → Titan"], "5.133 jours")
        self.assertTrue(any("JPL SAT441" in caption.value for caption in app.caption))

    def test_missing_staging_phase_is_visible_and_mass_budget_stays_earth_saturn_only(self):
        mass_result = {
            "instrument_mass_kg": 0.0,
            "dry_mass_kg": 1.0,
            "propellant_mass_kg": 0.0,
            "wet_mass_kg": 1.0,
        }
        with patch("app_services.compute_cached_trajectory") as trajectory_mock:
            trajectory_mock.return_value = {
                "note": "Test Earth-to-Saturn result",
                "dv_budget": {"Earth departure": 1_000.0},
                "dv_total": 1_000.0,
            }
            with patch("mission.sizing.compute_mass_budget", return_value=mass_result) as mass_mock:
                app = AppTest.from_file(APP_PATH).run(timeout=30)

        self.assertFalse(app.exception)
        self.assertTrue(
            any(
                "n'est pas modélisée" in warning.value
                and "pas ajoutés au budget global" in warning.value
                for warning in app.warning
            )
        )
        self.assertEqual(trajectory_mock.call_count, 1)
        self.assertEqual(mass_mock.call_count, 1)
        self.assertEqual(mass_mock.call_args.args[0], 1_000.0)


if __name__ == "__main__":
    unittest.main()
