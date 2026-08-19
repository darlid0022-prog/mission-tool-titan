import math
import unittest
from datetime import datetime, timedelta, timezone

from mission.models import TrajectoryResult
from mission.ui_format import (
    format_approximate_c3_km2_s2,
    format_approximate_speed_km_s,
    format_datetime_utc,
    format_delta_v_m_s,
    format_distance_km,
    format_duration_days,
    format_mass_kg,
    format_speed_m_s,
)
from mission.ui_presentation import (
    build_candidate_budget_presentation,
    build_lambert_departure_presentation,
)


class TestV030UiFormatting(unittest.TestCase):
    def test_required_baseline_delta_v_strings(self):
        self.assertEqual(format_delta_v_m_s(7_381.480), "7,381.480 m/s")
        self.assertEqual(format_delta_v_m_s(2_182.991), "2,182.991 m/s")
        self.assertEqual(format_delta_v_m_s(2_966.182), "2,966.182 m/s")
        self.assertEqual(format_delta_v_m_s(5_149.173), "5,149.173 m/s")
        self.assertEqual(format_delta_v_m_s(12_530.653), "12,530.653 m/s")

    def test_departure_condition_formats_are_distinct_from_delta_v(self):
        self.assertEqual(
            format_approximate_speed_km_s(10_432.306468285753),
            "approximately 10.432 km/s",
        )
        self.assertEqual(
            format_approximate_c3_km2_s2(108_833_018.248),
            "approximately 108.83 km²/s²",
        )
        self.assertEqual(format_speed_m_s(10_432.306468285753), "10,432.306 m/s")
        self.assertEqual(format_mass_kg(12_138.4), "12,138 kg")

    def test_distance_duration_and_utc_formats(self):
        self.assertEqual(format_distance_km(150_000_000.0), "150,000 km")
        self.assertEqual(format_duration_days(2_856.0), "2,856.0 days")
        local_time = datetime(
            2034,
            4,
            29,
            6,
            30,
            tzinfo=timezone(timedelta(hours=2)),
        )
        self.assertEqual(format_datetime_utc(local_time), "2034-04-29 04:30 UTC")

    def test_formatters_reject_non_finite_values_and_invalid_precision(self):
        with self.assertRaisesRegex(ValueError, "finite"):
            format_delta_v_m_s(math.inf)
        with self.assertRaisesRegex(ValueError, "between 0 and 9"):
            format_delta_v_m_s(1.0, decimal_places=10)
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            format_datetime_utc(datetime(2030, 1, 1))


class TestLambertDeparturePresentation(unittest.TestCase):
    BASELINE_EARTH_V_INFINITY_M_S = 10_432.306468285753

    def test_c3_is_exact_square_of_active_lambert_v_infinity(self):
        trajectory = TrajectoryResult(
            v_inf_depart=self.BASELINE_EARTH_V_INFINITY_M_S,
            method="lambert",
        )
        presentation = build_lambert_departure_presentation(trajectory)
        self.assertEqual(
            presentation.c3_m2_s2,
            presentation.earth_v_infinity_m_s**2,
        )
        self.assertEqual(
            presentation.earth_v_infinity_m_s,
            self.BASELINE_EARTH_V_INFINITY_M_S,
        )

    def test_baseline_c3_display_is_expected_value_without_hard_coding_raw_c3(self):
        presentation = build_lambert_departure_presentation(
            TrajectoryResult(
                v_inf_depart=self.BASELINE_EARTH_V_INFINITY_M_S,
                method="lambert",
            )
        )
        self.assertEqual(
            format_approximate_c3_km2_s2(presentation.c3_m2_s2),
            "approximately 108.83 km²/s²",
        )

    def test_adapter_rejects_non_lambert_or_missing_departure_state(self):
        with self.assertRaisesRegex(ValueError, "authoritative Lambert"):
            build_lambert_departure_presentation(
                TrajectoryResult(v_inf_depart=1.0, method="cassini_historical_vvejga")
            )
        with self.assertRaisesRegex(ValueError, "unavailable"):
            build_lambert_departure_presentation(TrajectoryResult(method="lambert"))

    def test_candidate_budget_adapter_copies_raw_burns_and_total(self):
        values = build_candidate_budget_presentation(
            earth_v_infinity_m_s=10_500.0,
            c3_km2_s2=110.25,
            earth_injection_m_s=7_400.0,
            saturn_capture_m_s=2_100.0,
            saturn_circularization_m_s=3_000.0,
            connected_total_m_s=12_500.0,
        )
        self.assertEqual(values.c3_m2_s2, 110_250_000.0)
        self.assertEqual(values.earth_injection_m_s, 7_400.0)
        self.assertEqual(values.saturn_subtotal_m_s, 5_100.0)
        self.assertEqual(values.connected_total_m_s, 12_500.0)


if __name__ == "__main__":
    unittest.main()
