import dataclasses
import json
import unittest
from datetime import UTC, date, datetime

import pandas as pd

import app_services
from mission.ui_session_state import (
    UI_MISSION_STATE_KEY,
    deserialize_ui_state,
    load_ui_state,
    serialize_ui_state,
    store_ui_state,
)
from mission.ui_state import (
    ActiveScenarioKind,
    CalculationErrorKind,
    CalculationStatus,
    MissionInputSnapshot,
    activate_cassini_historical_reference,
    apply_selected_candidate,
    begin_calculation,
    begin_new_search,
    calculation_failed,
    calculation_succeeded,
    initial_ui_state,
    launch_window_candidate_reference,
    return_to_baseline,
    select_candidate,
    update_draft_inputs,
)


def snapshot(token: str) -> MissionInputSnapshot:
    return MissionInputSnapshot(mission_query_token=token)


class TestCalculationStateTransitions(unittest.TestCase):
    def test_initial_state_has_no_result_and_baseline_is_active(self):
        state = initial_ui_state()
        self.assertEqual(state.calculation_status, CalculationStatus.NO_RESULT)
        self.assertIsNone(state.draft_inputs)
        self.assertIsNone(state.calculated_inputs)
        self.assertEqual(state.active_scenario.kind, ActiveScenarioKind.BASELINE)

    def test_draft_success_stale_and_restoration_after_new_success(self):
        first = snapshot("first-v2-token")
        second = snapshot("second-v2-token")
        calculated_at = datetime(2026, 8, 19, 8, 0, tzinfo=UTC)
        recalculated_at = datetime(2026, 8, 19, 9, 0, tzinfo=UTC)

        state = update_draft_inputs(initial_ui_state(), first)
        self.assertEqual(state.calculation_status, CalculationStatus.NO_RESULT)
        self.assertEqual(state.draft_inputs, first)

        state = begin_calculation(state)
        self.assertEqual(state.calculation_status, CalculationStatus.RUNNING)
        state = calculation_succeeded(state, calculated_at=calculated_at)
        self.assertEqual(state.calculation_status, CalculationStatus.CURRENT)
        self.assertEqual(state.calculated_inputs, first)
        self.assertEqual(state.calculated_at, calculated_at)

        state = update_draft_inputs(state, second)
        self.assertEqual(state.calculation_status, CalculationStatus.STALE)
        self.assertEqual(state.calculated_inputs, first)

        state = calculation_succeeded(begin_calculation(state), calculated_at=recalculated_at)
        self.assertEqual(state.calculation_status, CalculationStatus.CURRENT)
        self.assertEqual(state.draft_inputs, second)
        self.assertEqual(state.calculated_inputs, second)
        self.assertEqual(state.calculated_at, recalculated_at)

    def test_each_error_category_preserves_last_valid_result(self):
        calculated_at = datetime(2026, 8, 19, 8, 0, tzinfo=UTC)
        valid = snapshot("valid-v2-token")
        base = calculation_succeeded(
            begin_calculation(update_draft_inputs(initial_ui_state(), valid)),
            calculated_at=calculated_at,
        )
        for kind, expected_status in (
            (CalculationErrorKind.INPUT_ERROR, CalculationStatus.INPUT_ERROR),
            (CalculationErrorKind.NO_SOLUTION, CalculationStatus.NO_SOLUTION),
            (CalculationErrorKind.TECHNICAL_ERROR, CalculationStatus.TECHNICAL_ERROR),
        ):
            with self.subTest(kind=kind):
                failed = calculation_failed(base, kind=kind, message=f"{kind.value} message")
                self.assertEqual(failed.calculation_status, expected_status)
                self.assertEqual(failed.calculated_inputs, valid)
                self.assertEqual(failed.calculated_at, calculated_at)
                self.assertEqual(failed.last_error.kind, kind)

    def test_invalid_transitions_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "without draft"):
            begin_calculation(initial_ui_state())
        with self.assertRaisesRegex(ValueError, "running calculation"):
            calculation_succeeded(
                update_draft_inputs(initial_ui_state(), snapshot("draft-v2-token")),
                calculated_at=datetime.now(UTC),
            )
        with self.assertRaisesRegex(ValueError, "No selected candidate"):
            apply_selected_candidate(initial_ui_state())
        with self.assertRaisesRegex(ValueError, "launch-window candidate"):
            select_candidate(initial_ui_state(), initial_ui_state().active_scenario)
        with self.assertRaisesRegex(TypeError, "CalculationErrorKind"):
            calculation_failed(
                initial_ui_state(),
                kind="unexpected",  # type: ignore[arg-type]
                message="invalid transition",
            )


class TestActiveScenarioTransitions(unittest.TestCase):
    def setUp(self):
        self.candidate = launch_window_candidate_reference(
            scenario_id="candidate-42",
            source_search_id="search-2028-2032-fast",
        )

    def test_selection_does_not_activate_candidate(self):
        state = select_candidate(initial_ui_state(), self.candidate)
        self.assertEqual(state.selected_candidate, self.candidate)
        self.assertEqual(state.active_scenario.kind, ActiveScenarioKind.BASELINE)

    def test_application_is_explicit(self):
        state = apply_selected_candidate(select_candidate(initial_ui_state(), self.candidate))
        self.assertEqual(state.active_scenario, self.candidate)

    def test_new_search_clears_selection_but_preserves_applied_candidate(self):
        applied = apply_selected_candidate(select_candidate(initial_ui_state(), self.candidate))
        searched = begin_new_search(applied)
        self.assertIsNone(searched.selected_candidate)
        self.assertEqual(searched.active_scenario, self.candidate)
        self.assertEqual(
            searched.active_scenario.source_search_id,
            "search-2028-2032-fast",
        )

    def test_return_to_baseline_is_explicit(self):
        applied = apply_selected_candidate(select_candidate(initial_ui_state(), self.candidate))
        returned = return_to_baseline(applied)
        self.assertEqual(returned.active_scenario.kind, ActiveScenarioKind.BASELINE)

    def test_cassini_activation_is_a_distinct_historical_reference(self):
        state = activate_cassini_historical_reference(initial_ui_state())
        self.assertEqual(
            state.active_scenario.kind,
            ActiveScenarioKind.CASSINI_HISTORICAL_REFERENCE,
        )
        self.assertIn("historical reference", state.active_scenario.source_label.lower())


class TestPrimitiveSessionStateAdapter(unittest.TestCase):
    def test_round_trip_contains_no_scientific_or_dataframe_objects(self):
        candidate = launch_window_candidate_reference(
            scenario_id="candidate-7",
            source_search_id="search-old",
        )
        state = apply_selected_candidate(
            select_candidate(
                calculation_succeeded(
                    begin_calculation(
                        update_draft_inputs(initial_ui_state(), snapshot("calculated-v2-token"))
                    ),
                    calculated_at=datetime(2026, 8, 19, 10, 0, tzinfo=UTC),
                ),
                candidate,
            )
        )
        payload = serialize_ui_state(state)
        json.dumps(payload)
        self.assertEqual(deserialize_ui_state(payload), state)

        session_state: dict[str, object] = {}
        store_ui_state(session_state, state)
        self.assertIsInstance(session_state[UI_MISSION_STATE_KEY], dict)
        self.assertEqual(load_ui_state(session_state), state)

        def assert_primitive(value: object) -> None:
            self.assertNotIsInstance(value, pd.DataFrame)
            self.assertFalse(dataclasses.is_dataclass(value))
            if isinstance(value, dict):
                for nested in value.values():
                    assert_primitive(nested)
            elif isinstance(value, list | tuple):
                for nested in value:
                    assert_primitive(nested)
            else:
                self.assertIsInstance(value, str | int | float | bool | type(None))

        assert_primitive(session_state[UI_MISSION_STATE_KEY])

    def test_existing_v2_mission_link_round_trips_through_input_snapshot(self):
        inputs = app_services.MissionSetupInputs(
            destination="Saturn",
            selected_moon="Titan",
            departure_type="LEO",
            leo_altitude_km=250.0,
            saturn_periapsis_radius_km=62_330.0,
            saturn_staging_radius_km=600_000.0,
            titan_capture_altitude_km=1_500.0,
            launch_window_start=date(2026, 6, 1),
            launch_window_end=date(2027, 6, 1),
            isp_s=320.0,
            instruments_df=pd.DataFrame(
                [
                    {
                        "Instrument": "Science payload",
                        "Cible": "Orbiter",
                        "Masse (kg)": 143.5,
                        "Puissance (W)": 323.0,
                        "Débit (bps)": 0.0,
                    }
                ]
            ),
        )
        query = app_services.encode_mission_setup_query(inputs)
        state = update_draft_inputs(
            initial_ui_state(),
            MissionInputSnapshot(query[app_services.MISSION_QUERY_PARAM]),
        )
        restored_query = {app_services.MISSION_QUERY_PARAM: state.draft_inputs.mission_query_token}
        restored = app_services.decode_mission_setup_query(restored_query)
        self.assertEqual(restored.destination, inputs.destination)
        self.assertEqual(restored.launch_window_start, inputs.launch_window_start)
        self.assertEqual(restored.connected_saturn_periapsis_radius_km, 150_000.0)
        pd.testing.assert_frame_equal(restored.instruments_df, inputs.instruments_df)


if __name__ == "__main__":
    unittest.main()
