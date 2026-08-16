import unittest

from mission.pareto import (
    ParetoPoint,
    compute_connected_pareto_front,
    extract_pareto_front,
)

LOCKED_DEPARTURE_MJD2000 = 9_681.181818181818
LOCKED_TOF_YEARS = 7.819301848049317
LOCKED_DEPARTURE_V_INFINITY_M_S = 10_432.306468285773


def point(*, departure: float, tof: float, delta_v: float, duration: float, mass: float):
    return ParetoPoint(
        departure_mjd2000=departure,
        earth_saturn_tof_years=tof,
        earth_saturn_arrival_mjd2000=departure + duration,
        earth_departure_v_infinity_m_s=10_000.0,
        saturn_arrival_v_infinity_m_s=6_000.0,
        total_delta_v_m_s=delta_v,
        total_duration_days=duration,
        wet_mass_kg=mass,
    )


class TestParetoExtraction(unittest.TestCase):
    def test_known_dominated_points_are_excluded(self):
        fast = point(departure=1.0, tof=4.0, delta_v=12.0, duration=4.0, mass=12.0)
        efficient = point(departure=2.0, tof=7.0, delta_v=7.0, duration=7.0, mass=7.0)
        dominated = point(departure=3.0, tof=8.0, delta_v=13.0, duration=8.0, mass=13.0)

        front = extract_pareto_front((dominated, efficient, fast))

        self.assertEqual(front, (fast, efficient))
        self.assertNotIn(dominated, front)


class TestConnectedParetoSearch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.first = compute_connected_pareto_front()
        cls.second = compute_connected_pareto_front()

    def test_front_is_non_empty_and_search_is_deterministic(self):
        self.assertEqual(self.first.evaluated_count, 1_176)
        self.assertEqual(self.first.pareto_count, 38)
        self.assertEqual(self.first, self.second)

    def test_locked_departure_v_infinity_optimum_is_evaluated_and_near_front(self):
        matches = tuple(
            point
            for point in self.first.evaluated_points
            if point.departure_mjd2000 == LOCKED_DEPARTURE_MJD2000
            and point.earth_saturn_tof_years == LOCKED_TOF_YEARS
            and point.earth_departure_v_infinity_m_s == LOCKED_DEPARTURE_V_INFINITY_M_S
        )
        self.assertEqual(len(matches), 1)
        locked = matches[0]
        self.assertNotIn(locked, self.first.pareto_front)

        dominating_front_points = tuple(
            point
            for point in self.first.pareto_front
            if all(a <= b for a, b in zip(point.objectives, locked.objectives, strict=True))
            and any(a < b for a, b in zip(point.objectives, locked.objectives, strict=True))
        )
        self.assertGreater(len(dominating_front_points), 0)
        minimum_delta_v = min(
            dominating_front_points,
            key=lambda point: point.total_delta_v_m_s,
        )
        self.assertAlmostEqual(
            locked.total_delta_v_m_s - minimum_delta_v.total_delta_v_m_s,
            3.2536144272344245,
            delta=1e-12,
        )
        self.assertEqual(
            locked.total_duration_days - minimum_delta_v.total_duration_days,
            30.0,
        )

    def test_every_front_point_is_non_dominated(self):
        for candidate in self.first.pareto_front:
            with self.subTest(candidate=candidate):
                self.assertFalse(
                    any(
                        all(
                            a <= b
                            for a, b in zip(other.objectives, candidate.objectives, strict=True)
                        )
                        and any(
                            a < b
                            for a, b in zip(other.objectives, candidate.objectives, strict=True)
                        )
                        for other in self.first.evaluated_points
                        if other is not candidate
                    )
                )


if __name__ == "__main__":
    unittest.main()
