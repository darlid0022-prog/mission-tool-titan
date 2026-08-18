import math
import unittest

from mission.connected_physics import (
    compute_connected_first_order_chain,
    compute_earth_saturn_hohmann,
    compute_saturn_capture_to_titan_orbit,
)
from mission.constants import (
    F_RING_REFERENCE_RADIUS_M,
    NOMINAL_SATURN_PERIAPSIS_RADIUS_M,
    SATURN_EQUATORIAL_RADIUS_M,
    SATURN_MU_M3_S2,
    TITAN_MEAN_ORBIT_RADIUS_M,
)
from mission.dv_budget import compose_complete_dv_budget

# Tight deterministic tolerances verify analytical implementation equivalence;
# they do not claim millimetre-per-second trajectory fidelity.
ABS_TOL_M_S = 1e-6
ABS_TOL_S = 1e-6


class TestEarthSaturnHohmann(unittest.TestCase):
    def test_nominal_analytical_values(self):
        result = compute_earth_saturn_hohmann()

        self.assertAlmostEqual(result.departure_v_infinity_m_s, 10_288.580691, delta=ABS_TOL_M_S)
        self.assertAlmostEqual(result.arrival_v_infinity_m_s, 5_442.813670, delta=ABS_TOL_M_S)
        self.assertAlmostEqual(result.time_of_flight_s, 190_806_258.332587, delta=ABS_TOL_S)


class TestSaturnHyperbolaAndCapture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.chain = compute_connected_first_order_chain()
        cls.hyperbola = cls.chain.saturn_hyperbola
        cls.ellipse = cls.chain.saturn_capture

    def test_hyperbolic_elements_and_energy(self):
        self.assertGreater(self.hyperbola.specific_energy_j_kg, 0.0)
        self.assertLess(self.hyperbola.semimajor_axis_m, 0.0)
        self.assertGreater(self.hyperbola.eccentricity, 1.0)
        self.assertAlmostEqual(self.hyperbola.periapsis_radius_m, 150_000_000.0)
        reconstructed = (
            self.hyperbola.periapsis_speed_m_s**2 / 2.0
            - SATURN_MU_M3_S2 / self.hyperbola.periapsis_radius_m
        )
        # Independent reconstruction differs only by IEEE-754 operation order
        # (~2.4e-8 J/kg on a 1.48e7 J/kg value).
        self.assertAlmostEqual(
            reconstructed, self.hyperbola.specific_energy_j_kg, delta=1e-7
        )

    def test_ellipse_geometry_and_negative_energy(self):
        self.assertLess(self.ellipse.specific_energy_j_kg, 0.0)
        self.assertEqual(self.ellipse.periapsis_radius_m, NOMINAL_SATURN_PERIAPSIS_RADIUS_M)
        self.assertEqual(self.ellipse.apoapsis_radius_m, TITAN_MEAN_ORBIT_RADIUS_M)
        self.assertAlmostEqual(
            self.ellipse.semimajor_axis_m * (1.0 - self.ellipse.eccentricity),
            self.ellipse.periapsis_radius_m,
            delta=1e-7,
        )
        self.assertAlmostEqual(
            self.ellipse.semimajor_axis_m * (1.0 + self.ellipse.eccentricity),
            self.ellipse.apoapsis_radius_m,
            delta=1e-7,
        )

    def test_burns_are_speed_differences_at_the_same_points(self):
        self.assertEqual(
            self.ellipse.capture_delta_v_m_s,
            self.hyperbola.periapsis_speed_m_s - self.ellipse.periapsis_speed_m_s,
        )
        self.assertEqual(
            self.ellipse.circularisation_delta_v_m_s,
            self.ellipse.circular_speed_at_apoapsis_m_s - self.ellipse.apoapsis_speed_m_s,
        )

    def test_nominal_values(self):
        self.assertAlmostEqual(self.hyperbola.periapsis_speed_m_s, 23_138.142472, delta=ABS_TOL_M_S)
        self.assertAlmostEqual(math.degrees(self.hyperbola.turn_angle_rad), 127.051578, delta=1e-6)
        self.assertAlmostEqual(self.ellipse.capture_delta_v_m_s, 1_914.314514, delta=ABS_TOL_M_S)
        self.assertAlmostEqual(
            self.ellipse.circularisation_delta_v_m_s, 2_966.182265, delta=ABS_TOL_M_S
        )
        self.assertAlmostEqual(self.ellipse.total_delta_v_m_s, 4_880.496779, delta=ABS_TOL_M_S)

    def test_geometry_and_unit_guards(self):
        v_inf = self.chain.heliocentric.arrival_v_infinity_m_s
        invalid_periapses = (
            SATURN_EQUATORIAL_RADIUS_M,
            F_RING_REFERENCE_RADIUS_M,
            150_000.0,  # a likely accidental kilometre value passed as metres
        )
        for periapsis in invalid_periapses:
            with self.subTest(periapsis=periapsis), self.assertRaises(ValueError):
                compute_saturn_capture_to_titan_orbit(v_inf, periapsis_radius_m=periapsis)
        with self.assertRaisesRegex(ValueError, "apoapsis"):
            compute_saturn_capture_to_titan_orbit(
                v_inf,
                periapsis_radius_m=NOMINAL_SATURN_PERIAPSIS_RADIUS_M,
                apoapsis_radius_m=NOMINAL_SATURN_PERIAPSIS_RADIUS_M,
            )

    def test_lambert_and_baseline_paths_share_identical_saturn_burns(self):
        arrival_v_infinity_m_s = 5_740.9001396773365
        shared = compute_connected_first_order_chain(
            arrival_v_infinity_m_s=arrival_v_infinity_m_s,
            periapsis_radius_m=NOMINAL_SATURN_PERIAPSIS_RADIUS_M,
            apoapsis_radius_m=TITAN_MEAN_ORBIT_RADIUS_M,
        )
        direct_hyperbola, direct_capture = compute_saturn_capture_to_titan_orbit(
            arrival_v_infinity_m_s,
            periapsis_radius_m=NOMINAL_SATURN_PERIAPSIS_RADIUS_M,
            apoapsis_radius_m=TITAN_MEAN_ORBIT_RADIUS_M,
        )

        self.assertEqual(shared.saturn_hyperbola, direct_hyperbola)
        self.assertEqual(shared.saturn_capture, direct_capture)
        self.assertEqual(shared.saturn_capture.periapsis_radius_m, 150_000_000.0)
        self.assertEqual(shared.saturn_capture.apoapsis_radius_m, 1_221_870_000.0)


class TestConnectedBudget(unittest.TestCase):
    def test_total_is_exact_sum_and_excludes_redundant_terms(self):
        chain = compute_connected_first_order_chain()
        budget = compose_complete_dv_budget(
            {"dV from LEO": 7_000.0, "dV DSM/Fly-By": 12.0},
            connected_result=chain,
        )

        self.assertEqual(budget.saturn_titan_departure_m_s, 0.0)
        self.assertEqual(budget.titan_capture_m_s, 0.0)
        self.assertNotIn("Saturn staging to Titan transfer", budget.as_dict())
        self.assertNotIn("Titan circular capture", budget.as_dict())
        self.assertEqual(budget.total_m_s, sum(budget.as_dict().values()))
        self.assertEqual(
            budget.total_m_s,
            7_000.0 + 12.0 + chain.saturn_capture.capture_delta_v_m_s
            + chain.saturn_capture.circularisation_delta_v_m_s,
        )


if __name__ == "__main__":
    unittest.main()
