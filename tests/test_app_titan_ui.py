import unittest
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from mission.models import Leg, TrajectoryResult

APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


class TestSaturnTitanUi(unittest.TestCase):
    @staticmethod
    def _earth_saturn_leg():
        return Leg(
            origin="Earth",
            destination="Saturn",
            trajectory=TrajectoryResult(
                departure_mjd2000=9_681.181818181818,
                arrival_mjd2000=12_537.181818181829,
                tof_years=7.82,
                v_inf_depart=10_432.306468285773,
                v_inf_arrival=6_490.744714263188,
                method="lambert",
            ),
        )

    @staticmethod
    def _run_app():
        earth_saturn_result = {
            "note": "Test Earth-to-Saturn result",
            "dv_budget": {
                "dV from LEO": 1_000.0,
                "dV DSM/Fly-By": 0.0,
                "dV Capture at Destination": 999_999.0,
            },
            "dv_total": 1_000.0,
            "earth_saturn_leg": TestSaturnTitanUi._earth_saturn_leg(),
        }
        with patch("app_services.compute_cached_trajectory", return_value=earth_saturn_result):
            return AppTest.from_file(APP_PATH).run(timeout=30)

    def test_preliminary_section_displays_nominal_results_and_source(self):
        app = self._run_app()

        self.assertFalse(app.exception)
        self.assertTrue(
            any(heading.value == "Saturn → Titan — preliminary model" for heading in app.header)
        )
        metrics = {metric.label: metric.value for metric in app.metric}
        self.assertEqual(metrics["Departure delta-v from staging orbit"], "1,257.6 m/s")
        self.assertEqual(metrics["Titan-relative v∞ (non-propulsive)"], "1,049.8 m/s")
        self.assertEqual(metrics["Titan capture delta-v"], "862.7 m/s")
        self.assertEqual(metrics["Saturn → Titan modeled delta-v"], "2,120.3 m/s")
        self.assertEqual(metrics["Saturn → Titan time of flight"], "5.133 days")
        self.assertTrue(any("JPL SAT441" in caption.value for caption in app.caption))

    def test_connected_total_and_default_mass_outputs_are_non_zero(self):
        app = self._run_app()

        self.assertFalse(app.exception)
        metrics = {metric.label: metric.value for metric in app.metric}
        self.assertEqual(metrics["Sum of budgeted delta-v values"], "9903 m/s")
        for label in ("Dry mass", "Propellant mass", "Total wet mass"):
            self.assertNotEqual(metrics[label], "0.0 kg", msg=label)
        self.assertFalse(
            any(widget.label == "Saturn capture altitude (km)" for widget in app.number_input)
        )
        self.assertTrue(
            any(
                "does not yet represent a complete spacecraft bus" in warning.value
                for warning in app.warning
            )
        )

    def test_arrival_to_staging_section_displays_nominal_results_and_ring_status(self):
        app = self._run_app()

        self.assertFalse(app.exception)
        self.assertTrue(
            any(
                heading.value == "Saturn arrival → staging orbit — preliminary model"
                for heading in app.header
            )
        )
        metrics = {metric.label: metric.value for metric in app.metric}
        self.assertEqual(metrics["Capture-to-ellipse delta-v"], "2,280.8 m/s")
        self.assertEqual(metrics["Staging circularization delta-v"], "4,501.6 m/s")
        self.assertEqual(metrics["Arrival-to-staging total delta-v"], "6,782.4 m/s")
        self.assertEqual(metrics["Periapsis-to-apoapsis time"], "1.125 days")
        self.assertEqual(metrics["Periapsis below D-ring inner edge"], "4,570 km")
        self.assertEqual(metrics["Staging orbit beyond E-ring edge"], "+118,000 km")
        self.assertTrue(
            any(
                "Planet–ring corridor at periapsis" in warning.value
                and "Cassini's 2017 Grand Finale" in warning.value
                and "three-dimensional ring-plane geometry" in warning.value
                for warning in app.warning
            )
        )

    def test_complete_budget_is_connected_to_mass_sizing_without_legacy_capture(self):
        mass_result = {
            "instrument_mass_kg": 0.0,
            "dry_mass_kg": 1.0,
            "propellant_mass_kg": 0.0,
            "wet_mass_kg": 1.0,
        }
        with patch("app_services.compute_cached_trajectory") as trajectory_mock:
            trajectory_mock.return_value = {
                "note": "Test Earth-to-Saturn result",
                "dv_budget": {
                    "dV from LEO": 1_000.0,
                    "dV DSM/Fly-By": 0.0,
                    "dV Capture at Destination": 999_999.0,
                },
                "dv_total": 1_000.0,
                "earth_saturn_leg": self._earth_saturn_leg(),
            }
            with patch("mission.sizing.compute_mass_budget", return_value=mass_result) as mass_mock:
                app = AppTest.from_file(APP_PATH).run(timeout=30)

        self.assertFalse(app.exception)
        self.assertEqual(trajectory_mock.call_count, 1)
        self.assertEqual(mass_mock.call_count, 1)
        expected_total = 1_000.0 + 6_782.353909 + 2_120.301028
        self.assertAlmostEqual(mass_mock.call_args.args[0], expected_total, delta=1e-3)
        self.assertNotEqual(mass_mock.call_args.args[0], 1_000.0 + 999_999.0)


if __name__ == "__main__":
    unittest.main()
