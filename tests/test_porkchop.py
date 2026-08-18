import math
import unittest
from datetime import date

from mission import physics
from mission.leg_solver import compute_lambert_leg
from mission.porkchop import PorkchopGrid, compute_porkchop_grid, minimum_delta_v


class TestPorkchopGridShape(unittest.TestCase):
    def test_grid_shape_matches_the_independently_stepped_date_windows(self):
        grid = compute_porkchop_grid(
            "Mars",
            date(2026, 1, 1),
            date(2026, 3, 1),
            date(2026, 6, 1),
            date(2026, 10, 1),
            departure_step_days=20.0,
            arrival_step_days=30.0,
        )

        # Jan 1 -> Mar 1, 2026 (not a leap year) spans 59 days: floor(59/20) + 1 = 3
        # departure epochs. Jun 1 -> Oct 1, 2026 spans 122 days: floor(122/30) + 1 = 5
        # arrival epochs.
        self.assertEqual(len(grid.departure_epochs_mjd2000), 3)
        self.assertEqual(len(grid.arrival_epochs_mjd2000), 5)
        self.assertEqual(len(grid.delta_v_grid_m_s), 3)
        for row in grid.delta_v_grid_m_s:
            self.assertEqual(len(row), 5)
        self.assertEqual(grid.total_cell_count, 3 * 5)
        self.assertEqual(grid.origin, "Earth")
        self.assertEqual(grid.destination, "Mars")

    def test_departure_and_arrival_epochs_are_strictly_increasing(self):
        grid = compute_porkchop_grid(
            "Mars",
            date(2026, 1, 1),
            date(2026, 4, 1),
            date(2026, 6, 1),
            date(2027, 1, 1),
            departure_step_days=15.0,
            arrival_step_days=20.0,
        )

        departures = grid.departure_epochs_mjd2000
        arrivals = grid.arrival_epochs_mjd2000
        self.assertTrue(all(b > a for a, b in zip(departures, departures[1:])))
        self.assertTrue(all(b > a for a, b in zip(arrivals, arrivals[1:])))


class TestPorkchopGridInvalidCells(unittest.TestCase):
    def test_arrival_not_after_departure_is_marked_nan_not_raised(self):
        # Overlapping windows guarantee some (departure, arrival) pairs have
        # arrival <= departure - geometrically impossible, must be NaN.
        grid = compute_porkchop_grid(
            "Mars",
            date(2026, 1, 1),
            date(2026, 6, 1),
            date(2026, 1, 1),
            date(2026, 6, 1),
            departure_step_days=15.0,
            arrival_step_days=15.0,
        )

        self.assertLess(grid.valid_cell_count, grid.total_cell_count)
        found_impossible_pair_nan = False
        for departure, row in zip(grid.departure_epochs_mjd2000, grid.delta_v_grid_m_s):
            for arrival, value in zip(grid.arrival_epochs_mjd2000, row):
                if arrival <= departure:
                    self.assertTrue(math.isnan(value))
                    found_impossible_pair_nan = True
        self.assertTrue(found_impossible_pair_nan)

    def test_minimum_delta_v_ignores_nan_cells(self):
        grid = compute_porkchop_grid(
            "Mars",
            date(2026, 1, 1),
            date(2026, 6, 1),
            date(2026, 1, 1),
            date(2026, 6, 1),
            departure_step_days=15.0,
            arrival_step_days=15.0,
        )

        best = minimum_delta_v(grid)
        self.assertIsNotNone(best)
        delta_v, departure_mjd2000, arrival_mjd2000 = best
        self.assertTrue(math.isfinite(delta_v))
        self.assertGreater(arrival_mjd2000, departure_mjd2000)

    def test_minimum_delta_v_is_none_when_every_cell_is_impossible(self):
        # Arrival window entirely before the departure window: every pair has
        # arrival < departure, so the whole grid is NaN.
        grid = compute_porkchop_grid(
            "Mars",
            date(2027, 1, 1),
            date(2027, 2, 1),
            date(2026, 1, 1),
            date(2026, 2, 1),
            departure_step_days=15.0,
            arrival_step_days=15.0,
        )

        self.assertEqual(grid.valid_cell_count, 0)
        self.assertIsNone(minimum_delta_v(grid))


class TestPorkchopGridPlausibility(unittest.TestCase):
    """Real (unmocked) PyKEP Lambert solves - checks order-of-magnitude only,
    matching the task's own framing ("plausible for a Hohmann-like transfer"),
    not exact values that would be brittle to date-window/step choices."""

    def test_mars_minimum_delta_v_is_hohmann_like_order_of_magnitude(self):
        grid = compute_porkchop_grid(
            "Mars",
            date(2026, 1, 1),
            date(2026, 12, 1),
            date(2026, 6, 1),
            date(2028, 6, 1),
            departure_step_days=20.0,
            arrival_step_days=30.0,
        )

        best = minimum_delta_v(grid)
        self.assertIsNotNone(best)
        delta_v_m_s = best[0]
        # A single-impulse Earth(LEO)->Mars(low circular capture) transfer is a
        # few km/s: well above LEO orbital speed noise, well below an outer-
        # planet-scale transfer.
        self.assertGreater(delta_v_m_s, 3_000.0)
        self.assertLess(delta_v_m_s, 12_000.0)

    def test_saturn_minimum_delta_v_is_plausible_order_of_magnitude(self):
        grid = compute_porkchop_grid(
            "Saturn",
            date(2026, 1, 1),
            date(2026, 12, 1),
            date(2026, 6, 1),
            date(2028, 6, 1),
            departure_step_days=20.0,
            arrival_step_days=30.0,
        )

        best = minimum_delta_v(grid)
        self.assertIsNotNone(best)
        delta_v_m_s = best[0]
        # Direct single-impulse circular capture deep in Saturn's gravity well
        # is expensive (tens of km/s) - this is precisely why real missions use
        # staged capture or gravity assists instead; still well below an
        # unphysical value, and clearly above the Mars-scale case above.
        self.assertGreater(delta_v_m_s, 15_000.0)
        self.assertLess(delta_v_m_s, 45_000.0)


class TestPorkchopReusesLegSolver(unittest.TestCase):
    """The porkchop grid must reuse compute_lambert_leg's Lambert-solving
    primitive, not a re-derived copy: for the same departure/arrival pair,
    the two paths must agree exactly on v-infinity, and the porkchop delta-v
    must equal physics.delta_v_injection/delta_v_capture applied to it."""

    def test_single_cell_grid_matches_compute_lambert_leg_exactly(self):
        leg_results = compute_lambert_leg(
            "Earth",
            "Mars",
            date(2026, 6, 1),
            date(2026, 6, 1),
            n_departures=1,
            tof_min_years=0.5,
            tof_max_years=0.5,
        )
        self.assertEqual(len(leg_results), 1)
        leg = leg_results[0]
        assert leg.departure_mjd2000 is not None
        assert leg.arrival_mjd2000 is not None
        assert leg.v_inf_depart is not None
        assert leg.v_inf_arrival is not None

        grid = compute_porkchop_grid(
            "Mars",
            leg.departure_mjd2000,
            leg.departure_mjd2000,
            leg.arrival_mjd2000,
            leg.arrival_mjd2000,
            departure_step_days=1.0,
            arrival_step_days=1.0,
        )

        self.assertEqual(grid.valid_cell_count, 1)
        actual_delta_v = grid.delta_v_grid_m_s[0][0]
        self.assertTrue(math.isfinite(actual_delta_v))

        from mission.bodies import resolve_body

        earth = resolve_body("Earth")
        mars = resolve_body("Mars")
        assert earth.pykep_body is not None
        assert mars.pykep_body is not None
        expected_delta_v = physics.delta_v_injection(
            leg.v_inf_depart,
            earth.get_mu_self(),
            earth.pykep_body.get_radius() + grid.leo_altitude_m,
        ) + physics.delta_v_capture(
            leg.v_inf_arrival,
            mars.get_mu_self(),
            mars.pykep_body.get_radius() + grid.capture_altitude_m,
        )
        self.assertAlmostEqual(actual_delta_v, expected_delta_v, delta=1e-6)


class TestPorkchopGridValidation(unittest.TestCase):
    def test_rejects_an_arrival_window_ending_before_it_starts(self):
        with self.assertRaisesRegex(ValueError, "end must not precede"):
            compute_porkchop_grid(
                "Mars",
                date(2026, 1, 1),
                date(2026, 3, 1),
                date(2026, 6, 1),
                date(2026, 5, 1),
            )

    def test_rejects_a_non_positive_step(self):
        with self.assertRaisesRegex(ValueError, "step_days must be"):
            compute_porkchop_grid(
                "Mars",
                date(2026, 1, 1),
                date(2026, 3, 1),
                date(2026, 6, 1),
                date(2026, 8, 1),
                departure_step_days=0.0,
            )

    def test_rejects_a_moon_destination_not_supported_by_the_lambert_solver(self):
        with self.assertRaisesRegex(NotImplementedError, "Titan"):
            compute_porkchop_grid(
                "Titan",
                date(2026, 1, 1),
                date(2026, 3, 1),
                date(2026, 6, 1),
                date(2026, 8, 1),
            )

    def test_dataclass_rejects_a_grid_with_mismatched_row_length(self):
        with self.assertRaisesRegex(ValueError, "one value per arrival epoch"):
            PorkchopGrid(
                origin="Earth",
                destination="Mars",
                departure_epochs_mjd2000=(0.0, 1.0),
                arrival_epochs_mjd2000=(10.0, 11.0),
                delta_v_grid_m_s=((1.0, 2.0), (3.0,)),
                leo_altitude_m=250_000.0,
                capture_altitude_m=2_000_000.0,
            )

    def test_minimum_delta_v_rejects_a_non_grid_argument(self):
        with self.assertRaisesRegex(TypeError, "must be a PorkchopGrid"):
            minimum_delta_v(object())


if __name__ == "__main__":
    unittest.main()
