import unittest

from mission.pareto import compute_connected_pareto_front
from mission.pareto_plot import build_pareto_front_figure, select_pareto_highlights


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
                self.assertIn("Wet mass", trace.hovertemplate)
                self.assertIn("Earth → Saturn TOF", trace.hovertemplate)
                self.assertIn("Earth departure date", trace.hovertemplate)
                self.assertEqual(len(trace.customdata), len(trace.x))


if __name__ == "__main__":
    unittest.main()
