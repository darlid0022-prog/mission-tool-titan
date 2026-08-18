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

import streamlit as st

import app_services
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
    st.success(f"{len(result.candidates)} candidate(s) found — results view is built in a later step.")
