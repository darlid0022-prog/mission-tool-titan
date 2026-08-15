import unittest
from datetime import date
from unittest.mock import patch

from app_services import PHYSICS_MODEL_VERSION, compute_cached_trajectory


class TestCachedTrajectoryService(unittest.TestCase):
    def setUp(self):
        compute_cached_trajectory.clear()

    def tearDown(self):
        compute_cached_trajectory.clear()

    @staticmethod
    def _args(*, capture_altitude_km=2000.0):
        return (
            PHYSICS_MODEL_VERSION,
            "Saturn",
            "Direct",
            date(2026, 8, 15),
            date(2026, 8, 15),
            250.0,
            capture_altitude_km,
        )

    @patch("app_services.compute_trajectory")
    def test_identical_orbital_inputs_call_pykep_path_once(self, compute_mock):
        compute_mock.return_value = {"dv_total": 123.0}

        first = compute_cached_trajectory(*self._args())
        second = compute_cached_trajectory(*self._args())

        self.assertEqual(first, second)
        self.assertEqual(compute_mock.call_count, 1)

    @patch("app_services.compute_trajectory")
    def test_changed_orbital_input_recomputes_trajectory(self, compute_mock):
        compute_mock.return_value = {"dv_total": 123.0}

        compute_cached_trajectory(*self._args())
        compute_cached_trajectory(*self._args(capture_altitude_km=3000.0))

        self.assertEqual(compute_mock.call_count, 2)

    def test_rejects_an_unknown_physics_model_version(self):
        with self.assertRaisesRegex(ValueError, "Unsupported physics model version"):
            compute_cached_trajectory("obsolete-model", *self._args()[1:])
