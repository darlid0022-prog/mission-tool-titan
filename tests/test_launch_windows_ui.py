"""UI-level tests for the launch-window search page (pages/launch_windows.py).

Every service used below is a TEST FIXTURE ONLY - a plain object satisfying
launch_window_service.LaunchWindowSearchService, named and commented as such,
injected by patching launch_window_service.get_launch_window_service. None
of these fixtures are reachable from the running application: with no patch
active, get_launch_window_service() returns None and the page shows its
"engine not connected" state (covered separately below).
"""

import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

import app_services
from launch_window_engine_adapter import scenario_to_candidate
from launch_window_service import (
    LaunchWindowCandidate,
    LaunchWindowSearchError,
    LaunchWindowSearchResult,
)
from mission.launch_search import evaluate_launch_scenario
from mission.models import Leg, TrajectoryResult

APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


def _earth_saturn_result() -> dict:
    """Minimal compute_cached_trajectory() stand-in for Mission setup's own
    render - only needed by tests that must have a configured mission before
    exercising the "send to 3D" action.
    """
    return {
        "note": "Test Earth-to-Saturn result",
        "dv_budget": {
            "dV from LEO": 1_000.0,
            "dV DSM/Fly-By": 0.0,
            "dV Capture at Destination": 999_999.0,
        },
        "dv_total": 1_000.0,
        "earth_saturn_leg": Leg(
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
        ),
    }


def _make_candidate(rank: int, **overrides: object) -> LaunchWindowCandidate:
    """TEST FIXTURE ONLY - a hand-built candidate, never engine output."""
    kwargs = dict(
        rank=rank,
        departure_datetime=datetime(2026, 7, rank, 12, 0, tzinfo=timezone.utc),
        saturn_arrival_datetime=datetime(2033, 9, 1, 6, 0, tzinfo=timezone.utc),
        scenario_end_datetime=datetime(2033, 9, 20, 0, 0, tzinfo=timezone.utc),
        time_of_flight_days=2_618.75,
        c3_km2_s2=98.4,
        v_infinity_earth_m_s=10_432.3,
        v_infinity_saturn_m_s=6_490.7,
        delta_v_departure_m_s=3_620.1,
        delta_v_capture_m_s=2_280.8,
        delta_v_titan_circularization_m_s=862.7,
        delta_v_total_m_s=6_763.6 - rank * 10.0,
    )
    kwargs.update(overrides)
    return LaunchWindowCandidate(**kwargs)


class _FixtureLaunchWindowService:
    """TEST FIXTURE ONLY. Returns a fixed set of canned candidates and
    records the last request it received, so tests can assert the page
    built the request correctly (objective/resolution/etc.)."""

    def __init__(self, candidate_count: int = 3):
        self.candidate_count = candidate_count
        self.last_request = None

    def search(self, request):
        self.last_request = request
        candidates = tuple(_make_candidate(rank) for rank in range(1, self.candidate_count + 1))
        return LaunchWindowSearchResult(
            request=request,
            candidates=candidates,
            engine_name="test-fixture-v0",
            assumptions=("Patched-conic Lambert only.",),
        )


class _EmptyFixtureLaunchWindowService:
    """TEST FIXTURE ONLY. Always reports zero candidates found."""

    def search(self, request):
        return LaunchWindowSearchResult(request=request, candidates=(), engine_name="test-fixture-v0")


class _ErrorFixtureLaunchWindowService:
    """TEST FIXTURE ONLY. Always raises, simulating an engine failure."""

    def search(self, request):
        raise LaunchWindowSearchError("simulated engine failure")


def _run_to_launch_windows(app: AppTest) -> AppTest:
    app.run(timeout=30)
    return app.switch_page("pages/launch_windows.py").run(timeout=30)


def _submit_search(app: AppTest) -> AppTest:
    submit = next(b for b in app.button if b.label == "Find launch windows")
    return submit.click().run(timeout=30)


class TestEngineNotConnectedState(unittest.TestCase):
    def test_page_shows_an_explicit_not_connected_notice_with_no_service_patched(self):
        with patch("launch_window_service.get_launch_window_service", return_value=None):
            app = _run_to_launch_windows(AppTest.from_file(APP_PATH))

        self.assertFalse(app.exception)
        self.assertTrue(
            any("No launch-window search engine is connected yet" in i.value for i in app.info)
        )

    def test_clicking_find_while_disconnected_does_not_crash_and_stays_explicit(self):
        with patch("launch_window_service.get_launch_window_service", return_value=None):
            app = _run_to_launch_windows(AppTest.from_file(APP_PATH))
            app = _submit_search(app)

        self.assertFalse(app.exception)
        self.assertTrue(
            any("Cannot search: no launch-window search engine is connected" in i.value for i in app.info)
        )
        self.assertFalse(app.dataframe)


class TestInitialState(unittest.TestCase):
    def test_no_search_run_yet_shows_the_initial_prompt(self):
        with patch(
            "launch_window_service.get_launch_window_service",
            return_value=_FixtureLaunchWindowService(),
        ):
            app = _run_to_launch_windows(AppTest.from_file(APP_PATH))

        self.assertFalse(app.exception)
        self.assertTrue(
            any("No search has been run yet" in i.value for i in app.info)
        )


class TestDateValidation(unittest.TestCase):
    def test_rejects_an_end_date_not_after_the_start_date(self):
        with patch(
            "launch_window_service.get_launch_window_service",
            return_value=_FixtureLaunchWindowService(),
        ):
            app = _run_to_launch_windows(AppTest.from_file(APP_PATH))
            start = next(d for d in app.date_input if d.label == "Search window start")
            end = next(d for d in app.date_input if d.label == "Search window end")
            end.set_value(start.value)
            app = _submit_search(app)

        self.assertFalse(app.exception)
        self.assertTrue(
            any("search_window_end" in e.value for e in app.error)
        )
        self.assertNotIn("launch_window_result", app.session_state)

    def test_rejects_a_maximum_time_of_flight_below_the_minimum(self):
        with patch(
            "launch_window_service.get_launch_window_service",
            return_value=_FixtureLaunchWindowService(),
        ):
            app = _run_to_launch_windows(AppTest.from_file(APP_PATH))
            min_tof = next(
                n for n in app.number_input if n.label == "Minimum time of flight (days)"
            )
            max_tof = next(
                n for n in app.number_input if n.label == "Maximum time of flight (days)"
            )
            min_tof.set_value(3_000.0)
            max_tof.set_value(1_000.0)
            app = _submit_search(app)

        self.assertFalse(app.exception)
        self.assertTrue(any("max_time_of_flight_days" in e.value for e in app.error))


class TestObjectiveChange(unittest.TestCase):
    def test_changing_the_objective_selectbox_changes_the_submitted_request(self):
        service = _FixtureLaunchWindowService()
        with patch("launch_window_service.get_launch_window_service", return_value=service):
            app = _run_to_launch_windows(AppTest.from_file(APP_PATH))
            objective = next(s for s in app.selectbox if s.label == "Objective")
            self.assertEqual(objective.value, "Minimum delta-v")
            objective.set_value("Minimum C3")
            app = _submit_search(app)

        self.assertFalse(app.exception)
        self.assertEqual(service.last_request.objective, "min_c3")


class TestLoadingState(unittest.TestCase):
    def test_a_successful_search_shows_a_status_element_that_resolves_to_complete(self):
        with patch(
            "launch_window_service.get_launch_window_service",
            return_value=_FixtureLaunchWindowService(candidate_count=2),
        ):
            app = _run_to_launch_windows(AppTest.from_file(APP_PATH))
            app = _submit_search(app)

        self.assertFalse(app.exception)
        self.assertEqual(len(app.status), 1)
        self.assertEqual(app.status[0].state, "complete")
        self.assertIn("2 candidate(s)", app.status[0].label)


class TestNoResultState(unittest.TestCase):
    def test_zero_candidates_shows_a_warning_and_no_results_table(self):
        with patch(
            "launch_window_service.get_launch_window_service",
            return_value=_EmptyFixtureLaunchWindowService(),
        ):
            app = _run_to_launch_windows(AppTest.from_file(APP_PATH))
            app = _submit_search(app)

        self.assertFalse(app.exception)
        self.assertTrue(
            any("No launch-window candidates were found" in w.value for w in app.warning)
        )
        self.assertFalse(app.dataframe)


class TestServiceErrorState(unittest.TestCase):
    def test_a_raised_search_error_shows_an_explicit_error_status(self):
        with patch(
            "launch_window_service.get_launch_window_service",
            return_value=_ErrorFixtureLaunchWindowService(),
        ):
            app = _run_to_launch_windows(AppTest.from_file(APP_PATH))
            app = _submit_search(app)

        self.assertFalse(app.exception)
        self.assertEqual(len(app.status), 1)
        self.assertEqual(app.status[0].state, "error")
        self.assertIn("simulated engine failure", app.status[0].label)
        self.assertNotIn("launch_window_result", app.session_state)


class TestCandidateSelection(unittest.TestCase):
    def test_selecting_a_different_candidate_updates_the_highlighted_metrics_and_table(self):
        with patch(
            "launch_window_service.get_launch_window_service",
            return_value=_FixtureLaunchWindowService(candidate_count=3),
        ):
            app = _run_to_launch_windows(AppTest.from_file(APP_PATH))
            app = _submit_search(app)
            selector = next(s for s in app.selectbox if s.label == "Selected candidate")
            self.assertEqual(selector.value, 1)
            selector.set_value(2).run(timeout=30)

        self.assertFalse(app.exception)
        metrics = {m.label: m.value for m in app.metric}
        # rank 2's delta_v_total_m_s = 6763.6 - 2*10 = 6743.6
        self.assertEqual(metrics["Delta-v total"], "6,743.6 m/s")
        table = next(d for d in app.dataframe if "Rank" in d.value.columns).value
        selected_flags = dict(zip(table["Rank"], table["Selected"], strict=True))
        self.assertEqual(selected_flags, {1: False, 2: True, 3: False})


class TestSendSelectionTo3D(unittest.TestCase):
    def test_without_a_configured_mission_shows_a_prompt_instead_of_the_button(self):
        with patch(
            "launch_window_service.get_launch_window_service",
            return_value=_FixtureLaunchWindowService(candidate_count=1),
        ):
            app = AppTest.from_file(APP_PATH)
            app.run(timeout=30)
            # Simulate a session that never rendered Mission setup's own
            # (auto-storing) form: remove what the default-page run just stored.
            if app_services.MISSION_SETUP_STATE_KEY in app.session_state:
                del app.session_state[app_services.MISSION_SETUP_STATE_KEY]
            app = app.switch_page("pages/launch_windows.py").run(timeout=30)
            app = _submit_search(app)

        self.assertFalse(app.exception)
        self.assertFalse(
            any(b.label == "Send selected candidate to 3D view" for b in app.button)
        )
        self.assertTrue(
            any("Configure and calculate a mission on the Mission setup page first" in i.value for i in app.info)
        )

    def test_sending_the_selection_narrows_the_launch_window_and_opens_the_3d_page(self):
        with (
            patch(
                "launch_window_service.get_launch_window_service",
                return_value=_FixtureLaunchWindowService(candidate_count=1),
            ),
            patch("app_services.compute_cached_trajectory", return_value=_earth_saturn_result()),
        ):
            app = AppTest.from_file(APP_PATH)
            app.run(timeout=30)
            app = app.switch_page("pages/launch_windows.py").run(timeout=30)
            app = _submit_search(app)
            send_button = next(
                b for b in app.button if b.label == "Send selected candidate to 3D view"
            )
            app = send_button.click().run(timeout=30)

        self.assertFalse(app.exception)
        updated_inputs = app.session_state[app_services.MISSION_SETUP_STATE_KEY]
        self.assertEqual(updated_inputs.launch_window_start, date(2026, 7, 1))
        self.assertEqual(updated_inputs.launch_window_end, date(2026, 7, 2))
        self.assertEqual(updated_inputs.trajectory_type, app_services.TRAJECTORY_TYPE_DIRECT)
        self.assertTrue(
            any(
                h.value == "Complete mission trajectory — interactive 3D view"
                for h in app.header
            )
        )

    def test_selected_engine_segments_render_as_two_separate_3d_scenes(self):
        scenario = evaluate_launch_scenario(10_407.0, 12_427.0, sample_count=8)
        candidate = scenario_to_candidate(scenario, rank=1)

        class _ScientificFixtureService:
            def search(self, request):
                return LaunchWindowSearchResult(
                    request=request,
                    candidates=(candidate,),
                    engine_name="scientific-adapter-fixture",
                    pareto_candidate_ranks=(1,),
                )

        with (
            patch(
                "launch_window_service.get_launch_window_service",
                return_value=_ScientificFixtureService(),
            ),
            patch("app_services.compute_cached_trajectory", return_value=_earth_saturn_result()),
        ):
            app = AppTest.from_file(APP_PATH)
            app.run(timeout=30)
            app = app.switch_page("pages/launch_windows.py").run(timeout=30)
            app = _submit_search(app)
            send_button = next(
                button
                for button in app.button
                if button.label == "Send selected candidate to 3D view"
            )
            app = send_button.click().run(timeout=30)

        self.assertFalse(app.exception)
        self.assertEqual(len(app.get("plotly_chart")), 2)
        self.assertTrue(
            any(
                header.value == "Earth → Saturn (heliocentric)"
                for header in app.subheader
            )
        )
        self.assertTrue(
            any(
                header.value == "Saturn capture (Saturn-centred)"
                for header in app.subheader
            )
        )


class TestStaleResultsClearOnScenarioChange(unittest.TestCase):
    def test_a_new_search_replaces_the_previous_scenarios_values(self):
        first_service = _FixtureLaunchWindowService(candidate_count=1)
        with patch("launch_window_service.get_launch_window_service", return_value=first_service):
            app = _run_to_launch_windows(AppTest.from_file(APP_PATH))
            app = _submit_search(app)
        first_metrics = {m.label: m.value for m in app.metric}
        self.assertEqual(first_metrics["Delta-v total"], "6,753.6 m/s")

        second_candidate = _make_candidate(1, delta_v_total_m_s=1_234.5)

        class _SecondFixtureService:
            """TEST FIXTURE ONLY - a differently-scoped scenario's result."""

            def search(self, request):
                return LaunchWindowSearchResult(
                    request=request,
                    candidates=(second_candidate,),
                    engine_name="test-fixture-v0",
                )

        with patch(
            "launch_window_service.get_launch_window_service",
            return_value=_SecondFixtureService(),
        ):
            objective = next(s for s in app.selectbox if s.label == "Objective")
            objective.set_value("Minimum duration")
            app = _submit_search(app)

        self.assertFalse(app.exception)
        second_metrics = {m.label: m.value for m in app.metric}
        self.assertEqual(second_metrics["Delta-v total"], "1,234.5 m/s")
        self.assertNotEqual(second_metrics["Delta-v total"], first_metrics["Delta-v total"])


class TestUnitsAndLabels(unittest.TestCase):
    def test_table_columns_and_metric_labels_carry_the_required_fields_and_units(self):
        with patch(
            "launch_window_service.get_launch_window_service",
            return_value=_FixtureLaunchWindowService(candidate_count=1),
        ):
            app = _run_to_launch_windows(AppTest.from_file(APP_PATH))
            app = _submit_search(app)

        self.assertFalse(app.exception)
        table = next(d for d in app.dataframe if "Rank" in d.value.columns).value
        self.assertEqual(
            list(table.columns),
            [
                "Rank",
                "Selected",
                "Launch date (UTC)",
                "Launch time (UTC)",
                "Saturn arrival (UTC)",
                "Scenario end (UTC)",
                "Time of flight (days)",
                "Time of flight (years)",
                "C3 (km²/s²)",
                "v∞ Earth (m/s)",
                "v∞ Saturn (m/s)",
                "Delta-v departure (m/s)",
                "Delta-v capture (m/s)",
                "Delta-v Titan circularization (m/s)",
                "Delta-v total (m/s)",
            ],
        )
        metric_labels = {m.label for m in app.metric}
        for expected_label in (
            "Best launch date/time (UTC)",
            "Saturn arrival (UTC)",
            "Scenario end (UTC)",
            "Duration",
            "C3",
            "v∞ Earth",
            "v∞ Saturn",
            "Delta-v departure",
            "Delta-v capture",
            "Delta-v Titan circularization",
            "Delta-v total",
        ):
            self.assertIn(expected_label, metric_labels)
        self.assertTrue(
            any(
                "does not guarantee a phased encounter with Titan" in w.value
                for w in app.warning
            )
        )


class TestPageRendersWithoutException(unittest.TestCase):
    def test_page_renders_cleanly_with_no_service_connected(self):
        app = _run_to_launch_windows(AppTest.from_file(APP_PATH))
        self.assertFalse(app.exception)


if __name__ == "__main__":
    unittest.main()
