"""One-way, idempotent migration from legacy Streamlit session keys.

Legacy keys read here are ``mission_setup_inputs``,
``selected_launch_window_candidate`` and ``active_launch_window_candidate``.
Only the primitive v2 input token and lightweight scenario references are
written to the v0.3 state payload; scientific result objects remain on their
legacy keys while the corresponding pages are migrated in later lots.
"""

from __future__ import annotations

from collections.abc import MutableMapping
from datetime import UTC, datetime

import app_services
import launch_window_service as lw
from mission.ui_session_state import UI_MISSION_STATE_KEY, load_ui_state, store_ui_state
from mission.ui_state import (
    CalculationStatus,
    MissionInputSnapshot,
    MissionUiState,
    apply_selected_candidate,
    begin_new_search,
    cassini_scenario_reference,
    launch_window_candidate_reference,
    return_to_baseline,
    select_candidate,
)


class UiStateMigrationError(ValueError):
    """Raised when an existing v0.3 payload cannot be decoded safely."""


def _candidate_reference(candidate: lw.LaunchWindowCandidate):
    scenario_id = candidate.scenario_id or f"candidate-{candidate.rank}"
    return launch_window_candidate_reference(
        scenario_id=scenario_id,
        source_search_id=f"legacy-search:{scenario_id}",
    )


def snapshot_from_inputs(inputs: app_services.MissionSetupInputs) -> MissionInputSnapshot:
    query = app_services.encode_mission_setup_query(inputs)
    return MissionInputSnapshot(query[app_services.MISSION_QUERY_PARAM])


def initialize_or_migrate_ui_state(
    session_state: MutableMapping[str, object],
    *,
    migrated_at: datetime | None = None,
) -> MissionUiState:
    """Initialize once; an existing valid v0.3 payload is never replaced."""
    if UI_MISSION_STATE_KEY in session_state:
        try:
            return load_ui_state(session_state)
        except (TypeError, ValueError) as exc:
            raise UiStateMigrationError(f"Invalid v0.3 UI state: {exc}") from exc

    state = MissionUiState()
    inputs = session_state.get(app_services.MISSION_SETUP_STATE_KEY)
    if isinstance(inputs, app_services.MissionSetupInputs):
        snapshot = snapshot_from_inputs(inputs)
        timestamp = migrated_at or datetime.now(UTC)
        state = MissionUiState(
            draft_inputs=snapshot,
            calculated_inputs=snapshot,
            calculation_status=CalculationStatus.CURRENT,
            active_scenario=(
                cassini_scenario_reference()
                if inputs.trajectory_type == app_services.TRAJECTORY_TYPE_CASSINI_HISTORICAL
                else state.active_scenario
            ),
            calculated_at=timestamp,
        )

    selected = session_state.get(lw.SELECTED_LAUNCH_WINDOW_CANDIDATE_STATE_KEY)
    if isinstance(selected, lw.LaunchWindowCandidate):
        state = select_candidate(state, _candidate_reference(selected))
    active = session_state.get(lw.ACTIVE_LAUNCH_WINDOW_CANDIDATE_STATE_KEY)
    if isinstance(active, lw.LaunchWindowCandidate):
        reference = _candidate_reference(active)
        state = apply_selected_candidate(select_candidate(state, reference))

    store_ui_state(session_state, state)
    return state


def clear_unapplied_candidate_for_new_search(
    session_state: MutableMapping[str, object],
) -> None:
    store_ui_state(session_state, begin_new_search(load_ui_state(session_state)))


def select_legacy_candidate(
    session_state: MutableMapping[str, object], candidate: lw.LaunchWindowCandidate
) -> None:
    store_ui_state(
        session_state,
        select_candidate(load_ui_state(session_state), _candidate_reference(candidate)),
    )


def apply_legacy_candidate(
    session_state: MutableMapping[str, object], candidate: lw.LaunchWindowCandidate
) -> None:
    selected = select_candidate(load_ui_state(session_state), _candidate_reference(candidate))
    store_ui_state(session_state, apply_selected_candidate(selected))


def restore_baseline_scenario(session_state: MutableMapping[str, object]) -> None:
    store_ui_state(session_state, return_to_baseline(load_ui_state(session_state)))
