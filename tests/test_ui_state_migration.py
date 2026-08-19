from datetime import UTC, date, datetime

import pandas as pd
import pytest

import app_services
from mission.ui_session_state import UI_MISSION_STATE_KEY, serialize_ui_state
from mission.ui_state import ActiveScenarioKind, initial_ui_state
from mission.ui_state_migration import UiStateMigrationError, initialize_or_migrate_ui_state


def test_empty_legacy_session_initializes_baseline_atomically() -> None:
    session: dict[str, object] = {}
    state = initialize_or_migrate_ui_state(session)
    assert state.active_scenario.kind is ActiveScenarioKind.BASELINE
    assert set(session) == {UI_MISSION_STATE_KEY}


def test_migration_is_idempotent_and_preserves_existing_v030_payload() -> None:
    payload = serialize_ui_state(initial_ui_state())
    session: dict[str, object] = {UI_MISSION_STATE_KEY: payload}
    first = initialize_or_migrate_ui_state(session)
    second = initialize_or_migrate_ui_state(session)
    assert first == second == initial_ui_state()
    assert session[UI_MISSION_STATE_KEY] is payload


def test_restored_v2_inputs_are_preserved_without_rounding() -> None:
    inputs = app_services.MissionSetupInputs(
        destination="Saturn",
        selected_moon="Titan",
        departure_type="LEO",
        leo_altitude_km=250.125,
        saturn_periapsis_radius_km=62_330.25,
        saturn_staging_radius_km=600_000.5,
        titan_capture_altitude_km=1_500.75,
        launch_window_start=date(2026, 6, 1),
        launch_window_end=date(2027, 6, 1),
        isp_s=320.125,
        instruments_df=pd.DataFrame(
            [
                {
                    "Instrument": "Science",
                    "Cible": "Orbiter",
                    "Masse (kg)": 143.5,
                    "Puissance (W)": 323.0,
                    "Débit (bps)": 0.0,
                }
            ]
        ),
    )
    session: dict[str, object] = {app_services.MISSION_SETUP_STATE_KEY: inputs}
    state = initialize_or_migrate_ui_state(session, migrated_at=datetime(2026, 1, 1, tzinfo=UTC))
    assert state.calculated_inputs is not None
    assert (
        state.calculated_inputs.mission_query_token
        == app_services.encode_mission_setup_query(inputs)[app_services.MISSION_QUERY_PARAM]
    )
    restored = app_services.decode_mission_setup_query(
        {app_services.MISSION_QUERY_PARAM: state.calculated_inputs.mission_query_token}
    )
    assert restored.leo_altitude_km == inputs.leo_altitude_km
    assert restored.isp_s == inputs.isp_s


def test_invalid_v030_payload_is_controlled_and_not_replaced() -> None:
    invalid = {"schema_version": 999}
    session: dict[str, object] = {UI_MISSION_STATE_KEY: invalid}
    with pytest.raises(UiStateMigrationError, match="Invalid v0.3 UI state"):
        initialize_or_migrate_ui_state(session)
    assert session[UI_MISSION_STATE_KEY] is invalid
