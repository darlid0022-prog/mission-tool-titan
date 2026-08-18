"""Launch-window search: find and compare candidate Earth -> Saturn departure
dates, then send one chosen candidate to the 3D trajectory page.

No trajectory search happens in this file, or anywhere else in the UI layer:
every candidate comes from the injected
`launch_window_service.LaunchWindowSearchService` (see that module's
docstring for why this is an abstract, injected contract rather than a call
into a concrete engine - Codex is building the real search engine in
parallel, on a separate branch). This page never fabricates example search
results; when no engine is connected it says so explicitly instead.
"""

from datetime import timezone

import streamlit as st

import app_services
import launch_window_plot
import launch_window_service as lw

RESULT_STATE_KEY = "launch_window_result"
SELECTED_RANK_KEY = "launch_window_selected_rank"

_OBJECTIVE_LABEL_TO_VALUE = {
    label: value for value, label in lw.LAUNCH_WINDOW_OBJECTIVE_LABELS.items()
}
_RESOLUTION_LABEL_TO_VALUE = {
    label: value for value, label in lw.LAUNCH_WINDOW_RESOLUTION_LABELS.items()
}


def _clear_stale_results() -> None:
    """Drop any previous search's results before a new one starts.

    Called right before every new search attempt (valid or not) so a failed
    or differently-scoped search can never leave a prior scenario's
    candidates, selection, or numbers visible underneath a new form state.
    """
    st.session_state.pop(RESULT_STATE_KEY, None)
    st.session_state.pop(SELECTED_RANK_KEY, None)
    st.session_state.pop(lw.SELECTED_LAUNCH_WINDOW_CANDIDATE_STATE_KEY, None)
    st.session_state.pop(lw.ACTIVE_LAUNCH_WINDOW_CANDIDATE_STATE_KEY, None)


st.header(":material/search: Launch window search")
st.caption(
    "Search a departure-date range for the best Earth → Saturn launch windows "
    "against a chosen objective, then send one candidate to the 3D trajectory page."
)

service = lw.get_launch_window_service()
if service is None:
    st.info(
        "No launch-window search engine is connected yet. This page is "
        "interface-ready: once the search engine (built in parallel, on a "
        "separate branch) is merged, it is wired in behind "
        "`launch_window_service.get_launch_window_service()` with no change "
        "to this page."
    )

with st.form("launch_window_search_form"):
    st.subheader("Search parameters")
    start_col, end_col = st.columns(2)
    search_window_start = start_col.date_input(
        "Search window start",
        value=app_services.DEFAULT_LAUNCH_WINDOW_START,
        help="Earliest Earth-departure date to search.",
    )
    search_window_end = end_col.date_input(
        "Search window end",
        value=app_services.DEFAULT_LAUNCH_WINDOW_END,
        help="Latest Earth-departure date to search.",
    )

    min_tof_col, max_tof_col = st.columns(2)
    min_time_of_flight_days = min_tof_col.number_input(
        "Minimum time of flight (days)",
        min_value=1.0,
        value=1_800.0,
        step=50.0,
        help="Shortest Earth → Saturn cruise duration to consider.",
    )
    max_time_of_flight_days = max_tof_col.number_input(
        "Maximum time of flight (days)",
        min_value=1.0,
        value=3_600.0,
        step=50.0,
        help="Longest Earth → Saturn cruise duration to consider.",
    )

    objective_col, resolution_col = st.columns(2)
    objective_label = objective_col.selectbox(
        "Objective",
        list(lw.LAUNCH_WINDOW_OBJECTIVE_LABELS.values()),
        help=(
            "What the engine ranks candidates by: minimum delta-v, minimum "
            "duration, minimum C3, or a multi-objective trade-off."
        ),
    )
    resolution_label = resolution_col.radio(
        "Resolution",
        list(lw.LAUNCH_WINDOW_RESOLUTION_LABELS.values()),
        horizontal=True,
        help="Fast uses a coarse search grid; Detailed uses a finer one and costs more compute.",
    )

    max_results = st.number_input(
        "Number of results",
        min_value=1,
        max_value=lw.MAX_LAUNCH_WINDOW_RESULTS,
        value=10,
        step=1,
        help="How many ranked candidates to return.",
    )

    submitted = st.form_submit_button("Find launch windows", icon=":material/travel_explore:")

if submitted:
    _clear_stale_results()
    try:
        request = lw.LaunchWindowSearchRequest(
            search_window_start=search_window_start,
            search_window_end=search_window_end,
            min_time_of_flight_days=float(min_time_of_flight_days),
            max_time_of_flight_days=float(max_time_of_flight_days),
            objective=_OBJECTIVE_LABEL_TO_VALUE[objective_label],
            resolution=_RESOLUTION_LABEL_TO_VALUE[resolution_label],
            max_results=int(max_results),
        )
    except ValueError as exc:
        st.error(f"Invalid search parameters: {exc}")
    else:
        if service is None:
            st.info(
                "Cannot search: no launch-window search engine is connected. "
                "See the notice above."
            )
        else:
            # st.status (not st.spinner) so the loading/complete/error state
            # is a real, inspectable element for tests as well as users -
            # a plain spinner leaves nothing behind once its block exits.
            with st.status("Searching launch windows...", expanded=False) as status:
                try:
                    result = service.search(request)
                except lw.LaunchWindowSearchError as exc:
                    status.update(label=f"Search failed: {exc}", state="error")
                except Exception as exc:  # noqa: BLE001 - surface any engine failure, not just ours
                    status.update(label=f"Search failed: {exc}", state="error")
                else:
                    status.update(
                        label=f"Found {len(result.candidates)} candidate(s).",
                        state="complete",
                    )
                    st.session_state[RESULT_STATE_KEY] = result
                    st.session_state[SELECTED_RANK_KEY] = (
                        result.candidates[0].rank if result.candidates else None
                    )

result = st.session_state.get(RESULT_STATE_KEY)
if result is None:
    if not submitted:
        st.info(
            "Configure a search above and select **Find launch windows** to begin. "
            "No search has been run yet."
        )
elif not result.candidates:
    st.warning(
        "No launch-window candidates were found for these constraints. Try widening "
        "the search window or the time-of-flight range."
    )
else:
    candidates = result.candidates
    st.subheader(f"{len(candidates)} candidate(s) found")

    rank_options = [candidate.rank for candidate in candidates]

    def _format_rank_option(rank: int, _candidates=candidates) -> str:
        candidate = next(c for c in _candidates if c.rank == rank)
        launch_date = candidate.departure_datetime.astimezone(timezone.utc).date().isoformat()
        return f"#{rank} — {launch_date}"

    stored_selected_rank = st.session_state.get(SELECTED_RANK_KEY)
    default_selected_rank = (
        stored_selected_rank if stored_selected_rank in rank_options else rank_options[0]
    )
    selected_rank = st.selectbox(
        "Selected candidate",
        rank_options,
        index=rank_options.index(default_selected_rank),
        format_func=_format_rank_option,
        help="The candidate highlighted in the table and chart below, and sent to the 3D page.",
    )
    st.session_state[SELECTED_RANK_KEY] = selected_rank
    selected_candidate = next(c for c in candidates if c.rank == selected_rank)

    st.warning(
        "Arrival at Titan's orbital radius does not guarantee a phased encounter with "
        "Titan: Titan must actually be at that point in its orbit when the spacecraft "
        "arrives. This search targets Saturn/Titan's orbital radius only, not a phased "
        "Titan intercept."
    )

    with st.container(horizontal=True):
        st.metric(
            "Best launch date/time (UTC)",
            selected_candidate.departure_datetime.astimezone(timezone.utc).strftime(
                "%Y-%m-%d %H:%M"
            ),
            border=True,
        )
        st.metric(
            "Saturn arrival (UTC)",
            selected_candidate.saturn_arrival_datetime.astimezone(timezone.utc).strftime(
                "%Y-%m-%d %H:%M"
            ),
            border=True,
        )
        st.metric(
            "Scenario end (UTC)",
            selected_candidate.scenario_end_datetime.astimezone(timezone.utc).strftime(
                "%Y-%m-%d %H:%M"
            ),
            border=True,
        )
    with st.container(horizontal=True):
        st.metric(
            "Earth → Saturn flight time",
            f"{selected_candidate.time_of_flight_days:,.1f} days "
            f"({selected_candidate.time_of_flight_years:,.2f} yr)",
            help="The interplanetary cruise only - Earth departure to Saturn arrival.",
            border=True,
        )
        st.metric(
            "Total reference-scenario duration",
            f"{selected_candidate.total_duration_days:,.2f} days "
            f"({selected_candidate.total_duration_years:,.2f} yr)",
            help=(
                "Earth departure to scenario end: the Earth → Saturn flight time above "
                "plus the Saturn capture-to-ellipse burn and the circularization to "
                "Titan's orbital radius that happen after arrival."
            ),
            border=True,
        )
    with st.container(horizontal=True):
        st.metric("C3", f"{selected_candidate.c3_km2_s2:,.2f} km²/s²", border=True)
        st.metric(
            "v∞ Earth", f"{selected_candidate.v_infinity_earth_m_s:,.1f} m/s", border=True
        )
        st.metric(
            "v∞ Saturn", f"{selected_candidate.v_infinity_saturn_m_s:,.1f} m/s", border=True
        )
    st.caption(
        "C3 reflects only this trajectory's departure energy. No compatibility with any "
        "specific launch vehicle's C3-vs-payload-mass performance envelope has been "
        "checked — a high C3 may exceed what a given rocket can deliver to this energy."
    )
    with st.container(horizontal=True):
        st.metric(
            "Earth departure Δv",
            f"{selected_candidate.delta_v_departure_m_s:,.1f} m/s",
            border=True,
        )
        st.metric(
            "Delta-v capture", f"{selected_candidate.delta_v_capture_m_s:,.1f} m/s", border=True
        )
        st.metric(
            "Saturn-centered circularization Δv",
            f"{selected_candidate.delta_v_titan_circularization_m_s:,.1f} m/s",
            border=True,
        )
        st.metric(
            "Delta-v total", f"{selected_candidate.delta_v_total_m_s:,.1f} m/s", border=True
        )
    st.caption(
        "Earth departure Δv follows the configured Earth parking orbit — see Assumptions "
        "below for the exact altitude used. Saturn-centered circularization Δv is "
        "circularization at Titan's mean orbital radius — not Titan orbit insertion."
    )

    st.dataframe(
        launch_window_plot.build_candidates_dataframe(
            candidates,
            selected_rank=selected_rank,
            pareto_candidate_ranks=result.pareto_candidate_ranks,
        ),
        width="stretch",
        hide_index=True,
    )
    st.caption(
        'Click any column header to sort. "Selected" marks the candidate highlighted '
        'below and on the chart; "Pareto optimal" marks the same candidates as the '
        "chart's diamond markers — also the accessible, screen-reader-navigable "
        "alternative to the chart, built from the same data."
    )

    st.plotly_chart(
        launch_window_plot.build_candidates_chart(
            candidates,
            selected_rank=selected_rank,
            pareto_candidate_ranks=result.pareto_candidate_ranks,
        ),
        width="stretch",
        key="launch_window_candidates_chart",
        config={"displaylogo": False, "scrollZoom": True},
    )
    if result.pareto_candidate_ranks is None:
        st.caption(
            "Pareto front over these candidates: not yet available from the connected "
            "engine — reserved for the trade-off objective."
        )

    with st.expander("Assumptions"):
        if result.assumptions:
            st.markdown("\n".join(f"- {note}" for note in result.assumptions))
        else:
            st.caption("The connected engine did not report any assumptions for this search.")
        st.caption(f"Engine: {result.engine_name}")

    st.divider()
    active_candidate = st.session_state.get(
        lw.ACTIVE_LAUNCH_WINDOW_CANDIDATE_STATE_KEY
    )
    with st.container(horizontal=True):
        if st.button(
            "Use selected candidate as active scenario",
            icon=":material/check_circle:",
            help=(
                "Makes this exact engine result the source of truth for the Mission "
                "scorecard. It does not rerun either trajectory engine."
            ),
        ):
            st.session_state[lw.ACTIVE_LAUNCH_WINDOW_CANDIDATE_STATE_KEY] = (
                selected_candidate
            )
            active_candidate = selected_candidate
            st.success(
                f"Active scenario set to candidate "
                f"{selected_candidate.scenario_id or f'#{selected_candidate.rank}'}."
            )
        if isinstance(active_candidate, lw.LaunchWindowCandidate) and st.button(
            "Return to mission baseline",
            icon=":material/undo:",
        ):
            st.session_state.pop(
                lw.ACTIVE_LAUNCH_WINDOW_CANDIDATE_STATE_KEY, None
            )
            active_candidate = None
            st.success("Mission setup baseline restored as the active scenario.")

    if isinstance(active_candidate, lw.LaunchWindowCandidate):
        st.caption(
            f"Active scenario: {lw.MISSION_SCENARIO_LAUNCH_WINDOW_LABEL} — "
            f"{active_candidate.scenario_id or f'candidate #{active_candidate.rank}'}."
        )
    else:
        st.caption(f"Active scenario: {lw.MISSION_SCENARIO_BASELINE_LABEL}.")

    mission_setup_inputs = app_services.load_mission_setup_inputs()
    if mission_setup_inputs is None:
        st.info(
            "Configure and calculate a mission on the Mission setup page first, then "
            "you can send this candidate's launch date to the 3D trajectory view."
        )
    else:
        if st.button(
            "Send selected candidate to 3D view",
            icon=":material/3d_rotation:",
            help=(
                "Narrows Mission setup's launch window to this candidate's departure "
                "date (every other Mission setup input is kept) and opens the 3D "
                "trajectory page - the same Lambert engine and 3D page every other "
                "page already uses, not a second one."
            ),
        ):
            st.session_state[lw.SELECTED_LAUNCH_WINDOW_CANDIDATE_STATE_KEY] = (
                selected_candidate
            )
            updated_inputs = lw.apply_candidate_to_mission_setup(
                selected_candidate, mission_setup_inputs
            )
            app_services.store_mission_setup_inputs(updated_inputs)
            st.switch_page("pages/trajectory_3d.py")
