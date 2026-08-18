import unittest

from mission.pareto import compute_connected_pareto_front
from mission.pareto_plot import (
    build_pareto_front_figure,
    build_pareto_table,
    select_pareto_highlights,
)


class TestParetoFrontFigure(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = compute_connected_pareto_front()
        cls.highlights = select_pareto_highlights(cls.result)
        cls.figure = build_pareto_front_figure(cls.result)

    def test_highlights_locked_baseline_and_minimum_delta_v_point(self):
        self.assertAlmostEqual(
            self.highlights.baseline.earth_saturn_tof_years * 365.25,
            2_856.0,
            delta=1e-9,
        )
        self.assertAlmostEqual(
            self.highlights.delta_v_optimum.earth_saturn_tof_years * 365.25,
            2_826.0,
            delta=1e-9,
        )
        self.assertEqual(
            self.highlights.baseline.total_delta_v_m_s
            - self.highlights.delta_v_optimum.total_delta_v_m_s,
            3.2536144272344245,
        )

    def test_figure_contains_38_front_points_plus_the_baseline(self):
        traces = {trace.meta["role"]: trace for trace in self.figure.data}

        self.assertEqual(
            len(traces["pareto_front"].x) + len(traces["Minimum connected delta-v"].x),
            38,
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


class TestParetoTable(unittest.TestCase):
    """Accessible data-table alternative to the Pareto chart (see pages/optimization.py)."""

    @classmethod
    def setUpClass(cls):
        cls.result = compute_connected_pareto_front()
        cls.figure = build_pareto_front_figure(cls.result)
        cls.table = build_pareto_table(cls.figure)

    def test_table_row_count_matches_the_chart_exactly(self):
        self.assertEqual(len(self.table), sum(len(trace.x) for trace in self.figure.data))
        self.assertEqual(len(self.table), 39)

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
