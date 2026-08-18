import unittest
from datetime import datetime, timezone

from launch_window_plot import (
    CANDIDATE_TABLE_COLUMNS,
    build_candidates_chart,
    build_candidates_dataframe,
)
from launch_window_service import LaunchWindowCandidate


def _candidate(rank: int, delta_v_total_m_s: float = 6_763.6) -> LaunchWindowCandidate:
    return LaunchWindowCandidate(
        rank=rank,
        departure_datetime=datetime(2026, 7, rank, 12, 0, tzinfo=timezone.utc),
        saturn_arrival_datetime=datetime(2033, 9, 1, 6, 0, tzinfo=timezone.utc),
        scenario_end_datetime=datetime(2033, 9, 20, 0, 0, tzinfo=timezone.utc),
        time_of_flight_days=2_618.75 + rank,
        c3_km2_s2=98.4,
        v_infinity_earth_m_s=10_432.3,
        v_infinity_saturn_m_s=6_490.7,
        delta_v_departure_m_s=3_620.1,
        delta_v_capture_m_s=2_280.8,
        delta_v_titan_circularization_m_s=862.7,
        delta_v_total_m_s=delta_v_total_m_s,
    )


class TestBuildCandidatesDataframe(unittest.TestCase):
    def test_one_row_per_candidate_with_the_expected_columns(self):
        candidates = (_candidate(1), _candidate(2))
        table = build_candidates_dataframe(candidates, selected_rank=1)
        self.assertEqual(len(table), 2)
        self.assertEqual(list(table.columns), list(CANDIDATE_TABLE_COLUMNS))

    def test_selected_column_marks_only_the_selected_rank(self):
        candidates = (_candidate(1), _candidate(2), _candidate(3))
        table = build_candidates_dataframe(candidates, selected_rank=2)
        selected_flags = dict(zip(table["Rank"], table["Selected"], strict=True))
        self.assertEqual(selected_flags, {1: False, 2: True, 3: False})

    def test_pareto_optimal_column_matches_the_chart_highlighted_ranks(self):
        candidates = (_candidate(1), _candidate(2), _candidate(3))
        table = build_candidates_dataframe(
            candidates, selected_rank=1, pareto_candidate_ranks=(1, 3)
        )
        pareto_flags = dict(zip(table["Rank"], table["Pareto optimal"], strict=True))
        self.assertEqual(pareto_flags, {1: True, 2: False, 3: True})

    def test_pareto_optimal_column_is_all_false_when_no_ranks_given(self):
        candidates = (_candidate(1), _candidate(2))
        table = build_candidates_dataframe(candidates, selected_rank=1)
        self.assertFalse(table["Pareto optimal"].any())

    def test_rejects_non_candidate_input(self):
        with self.assertRaisesRegex(TypeError, "LaunchWindowCandidate"):
            build_candidates_dataframe((object(),), selected_rank=None)


class TestBuildCandidatesChart(unittest.TestCase):
    def test_one_trace_for_regular_candidates_plus_a_highlight_for_the_selection(self):
        candidates = (_candidate(1), _candidate(2))
        figure = build_candidates_chart(candidates, selected_rank=2)
        roles = {trace.meta["role"] for trace in figure.data}
        self.assertEqual(roles, {"candidates", "selected"})
        selected_trace = next(t for t in figure.data if t.meta["role"] == "selected")
        self.assertEqual(len(selected_trace.x), 1)

    def test_axis_titles_never_mix_two_measures_on_one_axis(self):
        figure = build_candidates_chart((_candidate(1),), selected_rank=1)
        self.assertEqual(figure.layout.xaxis.title.text, "Time of flight (days)")
        self.assertEqual(figure.layout.yaxis.title.text, "Delta-v total (m/s)")

    def test_pareto_ranks_render_as_a_distinct_trace(self):
        candidates = (_candidate(1), _candidate(2), _candidate(3))
        figure = build_candidates_chart(
            candidates, selected_rank=3, pareto_candidate_ranks=(1, 2)
        )
        roles = {trace.meta["role"] for trace in figure.data}
        self.assertEqual(roles, {"candidates", "pareto", "selected"})
        pareto_trace = next(t for t in figure.data if t.meta["role"] == "pareto")
        self.assertEqual(len(pareto_trace.x), 2)

    def test_no_pareto_ranks_means_no_pareto_trace(self):
        figure = build_candidates_chart((_candidate(1),), selected_rank=1)
        roles = {trace.meta["role"] for trace in figure.data}
        self.assertNotIn("pareto", roles)

    def test_rejects_an_empty_candidate_tuple(self):
        with self.assertRaisesRegex(ValueError, "non-empty"):
            build_candidates_chart((), selected_rank=None)


if __name__ == "__main__":
    unittest.main()
