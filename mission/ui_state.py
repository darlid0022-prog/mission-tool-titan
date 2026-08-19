"""Pure v0.3.0 UI state machine.

The state stores only immutable presentation references and versioned mission-
input snapshots. It never stores a MissionBundle, LaunchWindowCandidate, PyKEP
object, trajectory, or other derived scientific result. Pages remain on their
legacy session-state keys until the navigation migration in the next batch.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum


class CalculationStatus(StrEnum):
    NO_RESULT = "no_result"
    RUNNING = "running"
    CURRENT = "current"
    STALE = "stale"
    INPUT_ERROR = "input_error"
    NO_SOLUTION = "no_solution"
    TECHNICAL_ERROR = "technical_error"


class CalculationErrorKind(StrEnum):
    INPUT_ERROR = "input_error"
    NO_SOLUTION = "no_solution"
    TECHNICAL_ERROR = "technical_error"


class ActiveScenarioKind(StrEnum):
    BASELINE = "baseline"
    LAUNCH_WINDOW_CANDIDATE = "launch_window_candidate"
    CASSINI_HISTORICAL_REFERENCE = "cassini_historical_reference"


_ERROR_STATUS_BY_KIND = {
    CalculationErrorKind.INPUT_ERROR: CalculationStatus.INPUT_ERROR,
    CalculationErrorKind.NO_SOLUTION: CalculationStatus.NO_SOLUTION,
    CalculationErrorKind.TECHNICAL_ERROR: CalculationStatus.TECHNICAL_ERROR,
}


@dataclass(frozen=True)
class MissionInputSnapshot:
    """One exact versioned MissionSetupInputs serialization.

    ``mission_query_token`` is the existing v2 share-link payload, without a
    URL or query-parameter name. Reusing that established representation keeps
    the state serializable without changing the link contract.
    """

    mission_query_token: str
    schema_version: int = 2

    def __post_init__(self) -> None:
        if self.schema_version != 2:
            raise ValueError("MissionInputSnapshot requires mission schema version 2.")
        if (
            not isinstance(self.mission_query_token, str)
            or not self.mission_query_token.strip()
            or len(self.mission_query_token) > 32_000
        ):
            raise ValueError("mission_query_token must be a non-empty v2 token.")


@dataclass(frozen=True)
class ScenarioReference:
    """Serializable identity of a scenario, never its scientific result."""

    kind: ActiveScenarioKind
    scenario_id: str
    source_label: str
    source_search_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, ActiveScenarioKind):
            raise TypeError("kind must be an ActiveScenarioKind.")
        if not isinstance(self.scenario_id, str) or not self.scenario_id.strip():
            raise ValueError("scenario_id must be non-empty.")
        if not isinstance(self.source_label, str) or not self.source_label.strip():
            raise ValueError("source_label must be non-empty.")
        if self.kind is ActiveScenarioKind.LAUNCH_WINDOW_CANDIDATE:
            if not isinstance(self.source_search_id, str) or not self.source_search_id.strip():
                raise ValueError("A launch-window candidate requires source_search_id.")
        elif self.source_search_id is not None:
            raise ValueError("Only a launch-window candidate may have source_search_id.")


def baseline_scenario_reference() -> ScenarioReference:
    return ScenarioReference(
        kind=ActiveScenarioKind.BASELINE,
        scenario_id="mission-setup-baseline",
        source_label="Mission setup baseline",
    )


def cassini_scenario_reference() -> ScenarioReference:
    return ScenarioReference(
        kind=ActiveScenarioKind.CASSINI_HISTORICAL_REFERENCE,
        scenario_id="cassini-vvejga-historical-reference",
        source_label="Cassini VVEJGA historical reference",
    )


def launch_window_candidate_reference(
    *,
    scenario_id: str,
    source_search_id: str,
) -> ScenarioReference:
    return ScenarioReference(
        kind=ActiveScenarioKind.LAUNCH_WINDOW_CANDIDATE,
        scenario_id=scenario_id,
        source_label="Selected launch-window candidate",
        source_search_id=source_search_id,
    )


@dataclass(frozen=True)
class PresentationError:
    kind: CalculationErrorKind
    message: str

    def __post_init__(self) -> None:
        if not isinstance(self.kind, CalculationErrorKind):
            raise TypeError("kind must be a CalculationErrorKind.")
        if not isinstance(self.message, str) or not self.message.strip():
            raise ValueError("message must be non-empty.")


@dataclass(frozen=True)
class MissionUiState:
    """Complete immutable state for the four primary v0.3.0 views."""

    draft_inputs: MissionInputSnapshot | None = None
    calculated_inputs: MissionInputSnapshot | None = None
    calculation_status: CalculationStatus = CalculationStatus.NO_RESULT
    active_scenario: ScenarioReference = baseline_scenario_reference()
    selected_candidate: ScenarioReference | None = None
    calculated_at: datetime | None = None
    last_error: PresentationError | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.calculation_status, CalculationStatus):
            raise TypeError("calculation_status must be a CalculationStatus.")
        if not isinstance(self.active_scenario, ScenarioReference):
            raise TypeError("active_scenario must be a ScenarioReference.")
        if self.selected_candidate is not None and (
            not isinstance(self.selected_candidate, ScenarioReference)
            or self.selected_candidate.kind is not ActiveScenarioKind.LAUNCH_WINDOW_CANDIDATE
        ):
            raise ValueError("selected_candidate must be a launch-window reference.")
        if self.calculated_at is not None and (
            not isinstance(self.calculated_at, datetime)
            or self.calculated_at.tzinfo is None
            or self.calculated_at.utcoffset() is None
        ):
            raise ValueError("calculated_at must be a timezone-aware datetime.")
        if self.calculated_inputs is None and self.calculated_at is not None:
            raise ValueError("calculated_at requires calculated_inputs.")
        if self.calculated_inputs is not None and self.calculated_at is None:
            raise ValueError("calculated_inputs require calculated_at metadata.")

        expected_error_status = (
            _ERROR_STATUS_BY_KIND[self.last_error.kind] if self.last_error is not None else None
        )
        if expected_error_status is None and self.calculation_status in set(
            _ERROR_STATUS_BY_KIND.values()
        ):
            raise ValueError("An error calculation status requires last_error.")
        if (
            expected_error_status is not None
            and self.calculation_status is not expected_error_status
        ):
            raise ValueError("last_error kind must match calculation_status.")

        if self.calculation_status is CalculationStatus.NO_RESULT and (
            self.calculated_inputs is not None or self.last_error is not None
        ):
            raise ValueError("NO_RESULT cannot contain calculated inputs or an error.")
        if self.calculation_status is CalculationStatus.RUNNING and self.draft_inputs is None:
            raise ValueError("RUNNING requires draft_inputs.")
        if self.calculation_status is CalculationStatus.CURRENT and (
            self.calculated_inputs is None or self.draft_inputs != self.calculated_inputs
        ):
            raise ValueError("CURRENT requires identical draft and calculated inputs.")
        if self.calculation_status is CalculationStatus.STALE and (
            self.calculated_inputs is None or self.draft_inputs == self.calculated_inputs
        ):
            raise ValueError("STALE requires changed draft inputs and a prior result.")


def initial_ui_state() -> MissionUiState:
    return MissionUiState()


def update_draft_inputs(
    state: MissionUiState,
    draft_inputs: MissionInputSnapshot,
) -> MissionUiState:
    """Change only the draft and derive current/stale/no-result status."""
    if not isinstance(draft_inputs, MissionInputSnapshot):
        raise TypeError("draft_inputs must be a MissionInputSnapshot.")
    if state.calculated_inputs is None:
        status = CalculationStatus.NO_RESULT
    elif draft_inputs == state.calculated_inputs:
        status = CalculationStatus.CURRENT
    else:
        status = CalculationStatus.STALE
    return replace(
        state,
        draft_inputs=draft_inputs,
        calculation_status=status,
        last_error=None,
    )


def begin_calculation(state: MissionUiState) -> MissionUiState:
    if state.draft_inputs is None:
        raise ValueError("Cannot calculate without draft inputs.")
    if state.calculation_status is CalculationStatus.RUNNING:
        raise ValueError("A calculation is already running.")
    return replace(
        state,
        calculation_status=CalculationStatus.RUNNING,
        last_error=None,
    )


def calculation_succeeded(
    state: MissionUiState,
    *,
    calculated_at: datetime,
) -> MissionUiState:
    if state.calculation_status is not CalculationStatus.RUNNING:
        raise ValueError("A successful calculation must complete a running calculation.")
    if state.draft_inputs is None:
        raise ValueError("A successful calculation requires draft inputs.")
    return replace(
        state,
        calculated_inputs=state.draft_inputs,
        calculation_status=CalculationStatus.CURRENT,
        calculated_at=calculated_at,
        last_error=None,
    )


def calculation_failed(
    state: MissionUiState,
    *,
    kind: CalculationErrorKind,
    message: str,
) -> MissionUiState:
    """Record a failure while preserving the last successful inputs and timestamp."""
    if not isinstance(kind, CalculationErrorKind):
        raise TypeError("kind must be a CalculationErrorKind.")
    error = PresentationError(kind=kind, message=message)
    return replace(
        state,
        calculation_status=_ERROR_STATUS_BY_KIND[kind],
        last_error=error,
    )


def select_candidate(
    state: MissionUiState,
    candidate: ScenarioReference,
) -> MissionUiState:
    if (
        not isinstance(candidate, ScenarioReference)
        or candidate.kind is not ActiveScenarioKind.LAUNCH_WINDOW_CANDIDATE
    ):
        raise ValueError("Only a launch-window candidate can be selected.")
    return replace(state, selected_candidate=candidate)


def apply_selected_candidate(state: MissionUiState) -> MissionUiState:
    if state.selected_candidate is None:
        raise ValueError("No selected candidate is available to apply.")
    return replace(state, active_scenario=state.selected_candidate)


def begin_new_search(state: MissionUiState) -> MissionUiState:
    """Clear only an unapplied selection; the active scenario is preserved."""
    return replace(state, selected_candidate=None)


def return_to_baseline(state: MissionUiState) -> MissionUiState:
    return replace(state, active_scenario=baseline_scenario_reference())


def activate_cassini_historical_reference(state: MissionUiState) -> MissionUiState:
    return replace(state, active_scenario=cassini_scenario_reference())
