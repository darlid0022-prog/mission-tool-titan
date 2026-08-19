import unittest

from mission.pareto import ParetoPoint, compute_connected_pareto_front
from mission.pareto_plot import (
    build_pareto_front_figure,
    build_pareto_table,
    select_pareto_highlights,
)
from mission.ui_format import build_baseline_comparison_caption
from mission.ui_text import UI_TEXT


def _point(**overrides) -> ParetoPoint:
    """TEST FIXTURE ONLY - a hand-built point, never engine output."""
    fields = dict(
        departure_mjd2000=9_681.0,
        earth_saturn_tof_years=2_856.0 / 365.25,
        earth_saturn_arrival_mjd2000=9_681.0 + 2_856.0,
        earth_departure_v_infinity_m_s=10_432.3,
        saturn_arrival_v_infinity_m_s=6_490.7,
        total_delta_v_m_s=12_530.653,
        total_duration_days=2_859.354,
        wet_mass_kg=12_137.5,
    )
    fields.update(overrides)
    return ParetoPoint(**fields)


class TestParetoFrontFigure(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = compute_connected_pareto_front()
        cls.highlights = select_pareto_highlights(cls.result)
        cls.figure = build_pareto_front_figure(cls.result)

    def test_highlights_are_both_anchored_to_the_2856_day_reference_leg(self):
        self.assertAlmostEqual(
            self.highlights.baseline.earth_saturn_tof_years * 365.25,
            2_856.0,
            delta=1e-9,
        )
        self.assertAlmostEqual(
            self.highlights.delta_v_optimum.earth_saturn_tof_years * 365.25,
            2_856.0,
            delta=1e-9,
        )

    def test_the_comparison_caption_correctly_reports_whatever_the_real_relationship_is(self):
        # baseline (locked minimum departure v-infinity) and delta_v_optimum
        # (minimum total delta-v) are selected by DIFFERENT criteria over
        # different candidate sets (select_pareto_highlights) - their
        # coincidence is a property of today's data, not a design invariant.
        # This does NOT hardcode "they must be equal": whichever relationship
        # the real data actually has, the pure caption function must report
        # it correctly - see docs/audit_science_budget_v030.md, wording-and-
        # scope batch §2.5b.
        caption = build_baseline_comparison_caption(
            self.highlights.baseline, self.highlights.delta_v_optimum
        )
        if self.highlights.baseline == self.highlights.delta_v_optimum:
            self.assertEqual(caption, UI_TEXT["pareto_baseline_is_sampled_minimum"])
        else:
            self.assertIn("more", caption)
            self.assertNotEqual(caption, UI_TEXT["pareto_baseline_is_sampled_minimum"])

    def test_figure_contains_34_front_points_plus_the_baseline(self):
        traces = {trace.meta["role"]: trace for trace in self.figure.data}

        self.assertEqual(
            len(traces["pareto_front"].x) + len(traces["Minimum connected delta-v"].x),
            34,
        )
        self.assertEqual(len(traces["Current mission baseline"].x), 1)
        self.assertEqual(len(self.figure.data), 3)

    def test_hover_data_contains_all_required_mission_values(self):
        for trace in self.figure.data:
            with self.subTest(trace=trace.name):
                self.assertIn("Connected delta-v", trace.hovertemplate)
                self.assertIn("Total mission duration", trace.hovertemplate)
                self.assertIn("Simplified wet mass", trace.hovertemplate)
                self.assertIn("Earth → Saturn TOF", trace.hovertemplate)
                self.assertIn("Earth departure date", trace.hovertemplate)
                self.assertEqual(len(trace.customdata), len(trace.x))


class TestBaselineComparisonCaption(unittest.TestCase):
    """Pure-function coverage of both branches of build_baseline_comparison_caption,
    with hand-built points - no page-level seam added to pages/optimization.py
    to make this testable (docs/audit_science_budget_v030.md, wording-and-scope
    batch §2.5c)."""

    def test_coinciding_points_produce_the_coincidence_caption(self):
        same_point = _point()
        caption = build_baseline_comparison_caption(same_point, same_point)
        self.assertEqual(caption, UI_TEXT["pareto_baseline_is_sampled_minimum"])
        self.assertIn("distinct criteria", caption)
        self.assertIn("can diverge", caption)

    def test_differing_points_produce_the_numeric_comparison(self):
        baseline = _point(
            total_delta_v_m_s=12_530.653,
            total_duration_days=2_859.354,
            wet_mass_kg=12_137.5,
        )
        optimum = _point(
            total_delta_v_m_s=12_000.0,
            total_duration_days=2_800.0,
            wet_mass_kg=12_000.0,
        )
        caption = build_baseline_comparison_caption(baseline, optimum)
        self.assertNotEqual(caption, UI_TEXT["pareto_baseline_is_sampled_minimum"])
        self.assertIn("530.653 m/s more", caption)
        self.assertIn("59 more days", caption)
        self.assertIn("137.500 kg more", caption)

    def test_a_baseline_below_the_optimum_still_reports_correctly(self):
        # The optimum is, by construction, the minimum delta-v point of its
        # own front - but this function takes two arbitrary points, so it
        # must not assume the difference is always non-negative.
        baseline = _point(total_delta_v_m_s=11_000.0)
        optimum = _point(total_delta_v_m_s=12_000.0)
        caption = build_baseline_comparison_caption(baseline, optimum)
        self.assertIn("-1000.000 m/s more", caption)


class TestParetoTable(unittest.TestCase):
    """Accessible data-table alternative to the Pareto chart (see pages/optimization.py)."""

    @classmethod
    def setUpClass(cls):
        cls.result = compute_connected_pareto_front()
        cls.figure = build_pareto_front_figure(cls.result)
        cls.table = build_pareto_table(cls.figure)

    def test_table_row_count_matches_the_chart_exactly(self):
        self.assertEqual(len(self.table), sum(len(trace.x) for trace in self.figure.data))
        self.assertEqual(len(self.table), 35)

    def test_table_columns_are_labeled_with_units(self):
        self.assertEqual(
            list(self.table.columns),
            [
                "Role",
                "Total delta-v (m/s)",
                "Total duration (days)",
                "Wet mass (kg)",
                "Earth → Saturn TOF (days)",
                "Earth departure date",
                "Departure MJD2000",
            ],
        )

    def test_table_includes_both_highlighted_reference_rows(self):
        roles = set(self.table["Role"])
        self.assertIn("Minimum connected delta-v", roles)
        self.assertIn("Current mission baseline", roles)
        self.assertEqual((self.table["Role"] == "Minimum connected delta-v").sum(), 1)
        self.assertEqual((self.table["Role"] == "Current mission baseline").sum(), 1)

    def test_table_values_match_the_baseline_trace_exactly(self):
        baseline_trace = next(t for t in self.figure.data if t.name == "Current mission baseline")
        baseline_row = self.table[self.table["Role"] == "Current mission baseline"].iloc[0]
        self.assertEqual(baseline_row["Total delta-v (m/s)"], baseline_trace.x[0])
        self.assertEqual(baseline_row["Total duration (days)"], baseline_trace.y[0])
        self.assertEqual(baseline_row["Wet mass (kg)"], baseline_trace.customdata[0][0])

    def test_rejects_a_non_figure_argument(self):
        with self.assertRaisesRegex(TypeError, "must be a plotly"):
            build_pareto_table(object())


if __name__ == "__main__":
    unittest.main()
