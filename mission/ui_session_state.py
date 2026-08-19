"""Primitive-only session-state adapter for :mod:`mission.ui_state`.

The current pages keep using their established keys until lot 3. Migration
must be atomic: translate legacy MissionSetupInputs/candidate objects into the
snapshots and references defined here, write this one payload, then stop
writing the legacy active-scenario keys. Until that cut-over, this adapter is
deliberately not invoked by page-rendering code, avoiding two active sources
of truth.
"""

from __future__ import annotations

from collections.abc import MutableMapping
from datetime import datetime

from mission.ui_state import (
    ActiveScenarioKind,
    CalculationErrorKind,
    CalculationStatus,
    MissionInputSnapshot,
    MissionUiState,
    PresentationError,
    ScenarioReference,
    initial_ui_state,
)

UI_MISSION_STATE_KEY = "mission_ui_state_v030"
UI_MISSION_STATE_SCHEMA_VERSION = 1


def _snapshot_payload(snapshot: MissionInputSnapshot | None) -> dict[str, object] | None:
    if snapshot is None:
        return None
    return {
        "schema_version": snapshot.schema_version,
        "mission_query_token": snapshot.mission_query_token,
    }


def _scenario_payload(reference: ScenarioReference) -> dict[str, object]:
    return {
        "kind": reference.kind.value,
        "scenario_id": reference.scenario_id,
        "source_label": reference.source_label,
        "source_search_id": reference.source_search_id,
    }


def serialize_ui_state(state: MissionUiState) -> dict[str, object]:
    """Return a payload containing only dict/list/string/int/None primitives."""
    if not isinstance(state, MissionUiState):
        raise TypeError("state must be a MissionUiState.")
    return {
        "schema_version": UI_MISSION_STATE_SCHEMA_VERSION,
        "draft_inputs": _snapshot_payload(state.draft_inputs),
        "calculated_inputs": _snapshot_payload(state.calculated_inputs),
        "calculation_status": state.calculation_status.value,
        "active_scenario": _scenario_payload(state.active_scenario),
        "selected_candidate": (
            _scenario_payload(state.selected_candidate)
            if state.selected_candidate is not None
            else None
        ),
        "calculated_at": state.calculated_at.isoformat() if state.calculated_at else None,
        "last_error": (
            {"kind": state.last_error.kind.value, "message": state.last_error.message}
            if state.last_error is not None
            else None
        ),
    }


def _snapshot_from_payload(value: object) -> MissionInputSnapshot | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("Mission-input snapshot payload must be a mapping.")
    return MissionInputSnapshot(
        mission_query_token=str(value.get("mission_query_token", "")),
        schema_version=int(value.get("schema_version", 0)),
    )


def _scenario_from_payload(value: object) -> ScenarioReference:
    if not isinstance(value, dict):
        raise ValueError("Scenario payload must be a mapping.")
    source_search_id = value.get("source_search_id")
    return ScenarioReference(
        kind=ActiveScenarioKind(str(value.get("kind", ""))),
        scenario_id=str(value.get("scenario_id", "")),
        source_label=str(value.get("source_label", "")),
        source_search_id=(str(source_search_id) if source_search_id is not None else None),
    )


def deserialize_ui_state(payload: object) -> MissionUiState:
    if not isinstance(payload, dict):
        raise ValueError("UI state payload must be a mapping.")
    if payload.get("schema_version") != UI_MISSION_STATE_SCHEMA_VERSION:
        raise ValueError("Unsupported UI state schema version.")
    selected_payload = payload.get("selected_candidate")
    error_payload = payload.get("last_error")
    if error_payload is not None and not isinstance(error_payload, dict):
        raise ValueError("last_error payload must be a mapping.")
    calculated_at_value = payload.get("calculated_at")
    return MissionUiState(
        draft_inputs=_snapshot_from_payload(payload.get("draft_inputs")),
        calculated_inputs=_snapshot_from_payload(payload.get("calculated_inputs")),
        calculation_status=CalculationStatus(str(payload.get("calculation_status", ""))),
        active_scenario=_scenario_from_payload(payload.get("active_scenario")),
        selected_candidate=(
            _scenario_from_payload(selected_payload) if selected_payload is not None else None
        ),
        calculated_at=(
            datetime.fromisoformat(str(calculated_at_value))
            if calculated_at_value is not None
            else None
        ),
        last_error=(
            PresentationError(
                kind=CalculationErrorKind(str(error_payload.get("kind", ""))),
                message=str(error_payload.get("message", "")),
            )
            if error_payload is not None
            else None
        ),
    )


def load_ui_state(session_state: MutableMapping[str, object]) -> MissionUiState:
    payload = session_state.get(UI_MISSION_STATE_KEY)
    return initial_ui_state() if payload is None else deserialize_ui_state(payload)


def store_ui_state(
    session_state: MutableMapping[str, object],
    state: MissionUiState,
) -> None:
    session_state[UI_MISSION_STATE_KEY] = serialize_ui_state(state)
