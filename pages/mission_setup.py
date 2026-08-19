"""Mission setup: destination, launch window, propulsion, instruments, and
the connected propulsive delta-v/mass budget that directly results from them.

This is the page every other page depends on: submitting the form stores the
simple input values in st.session_state (see app_services.MissionSetupInputs)
so other pages can rebuild the same derived results via
app_services.require_mission_bundle() without recomputing or duplicating any
business logic here.
"""

from datetime import UTC, datetime, timedelta

import pandas as pd
import streamlit as st

import app_services
import launch_window_service as lw
from mission import colors
from mission.capabilities import (
    MOON_DESTINATIONS,
    PLANET_DESTINATIONS,
    PLANNED_DESTINATIONS,
    PLANNED_MISSION_FEATURES,
)
from mission.constants import (
    F_RING_REFERENCE_RADIUS_M,
    NOMINAL_SATURN_PERIAPSIS_RADIUS_M,
    TITAN_MEAN_ORBIT_RADIUS_M,
)
from mission.payload_catalog import catalog_by_label, catalog_row
from mission.pdf_report import MissionPdfReport, generate_mission_summary_pdf
from mission.sizing import compute_mass_budget
from mission.ui_components import render_mission_progress
from mission.ui_session_state import load_ui_state, store_ui_state
from mission.ui_state import (
    activate_cassini_historical_reference,
    begin_calculation,
    calculation_succeeded,
    return_to_baseline,
    update_draft_inputs,
)
from mission.ui_state_migration import restore_baseline_scenario, snapshot_from_inputs
from mission.ui_text import UI_TEXT, UI_V030_TEXT

# Phases the connected delta-v budget (mission.dv_budget.MissionDeltaVBudget)
# structurally contributes to - Lunar transfer and Landing have no field in
# that budget at all (see its as_dict()), for either trajectory type offered
# on this page, so they are never silently implied to contribute below.
_CONNECTED_BUDGET_PHASES = (colors.LAUNCH, colors.INTERPLANETARY_TRANSFER, colors.ARRIVAL)


def _format_mjd2000_as_utc_date(epoch_mjd2000: float) -> str:
    """Pure formatting, same MJD2000 epoch/conversion already used across this
    app (e.g. mission/trajectory_plot.py's _format_mjd2000) - not a new or
    re-derived date, just a calendar-date rendering of the existing epoch."""
    epoch = datetime(2000, 1, 1, tzinfo=UTC) + timedelta(days=epoch_mjd2000)
    return epoch.date().isoformat()


st.title(UI_V030_TEXT["mission_title"])
st.caption(UI_V030_TEXT["mission_introduction"])
render_mission_progress(UI_V030_TEXT["mission_title"])
scorecard_slot = st.empty()
stored_inputs = app_services.load_mission_setup_inputs()
default_destination = stored_inputs.destination if stored_inputs else "Saturn"

with st.form("orbital_inputs"):
    st.header(UI_TEXT["architecture_header"])
    destination = st.selectbox(
        UI_TEXT["destination_label"],
        PLANET_DESTINATIONS,
        index=PLANET_DESTINATIONS.index(default_destination),
        help=UI_TEXT["destination_help"],
    )
    available_moons = [
        moon for moon, parent_planet in MOON_DESTINATIONS.items() if parent_planet == destination
    ]
    moon_choices = [UI_TEXT["no_moon_option"], *available_moons]
    default_moon_choice = (
        stored_inputs.selected_moon
        if stored_inputs and stored_inputs.selected_moon in moon_choices
        else UI_TEXT["no_moon_option"]
    )
    if stored_inputs is None and "Titan" in moon_choices:
        default_moon_choice = "Titan"
    moon_choice = st.selectbox(
        UI_TEXT["moon_label"],
        moon_choices,
        index=moon_choices.index(default_moon_choice),
        help=UI_TEXT["moon_help"],
    )
    selected_moon = None if moon_choice == UI_TEXT["no_moon_option"] else moon_choice
    if destination == "Saturn":
        default_trajectory_type = (
            stored_inputs.trajectory_type
            if stored_inputs and stored_inputs.trajectory_type in app_services.TRAJECTORY_TYPES
            else app_services.TRAJECTORY_TYPE_DIRECT
        )
        trajectory_type = st.radio(
            "Trajectory type",
            app_services.TRAJECTORY_TYPES,
            index=app_services.TRAJECTORY_TYPES.index(default_trajectory_type),
            help=(
                "Direct solves a Lambert transfer over your chosen launch window below. "
                "The historical option instead uses the real Cassini Venus-Venus-Earth-"
                "Jupiter gravity-assist tour (1997-2004): its own real dates and delta-v "
                "(Earth-departure injection plus the Saturn Orbit Insertion burn only - "
                "every flyby in between is unpowered) replace the connected budget below, "
                "independent of the launch window and moon selection above."
            ),
        )
    else:
        trajectory_type = app_services.TRAJECTORY_TYPE_DIRECT
    departure_type = st.radio(
        UI_TEXT["departure_type"],
        ["Direct", "LEO"],
        index=["Direct", "LEO"].index(stored_inputs.departure_type) if stored_inputs else 1,
        help=UI_TEXT["departure_type_help"],
    )
    leo_altitude_km = st.number_input(
        UI_TEXT["leo_altitude"],
        min_value=100,
        value=int(stored_inputs.leo_altitude_km) if stored_inputs else 250,
        help=UI_TEXT["leo_help"],
    )
    connected_saturn_periapsis_radius_km = st.number_input(
        "Connected Saturn capture periapsis radius (km)",
        min_value=int(F_RING_REFERENCE_RADIUS_M / 1_000) + 1,
        max_value=int(TITAN_MEAN_ORBIT_RADIUS_M / 1_000) - 1,
        value=(
            int(stored_inputs.connected_saturn_periapsis_radius_km)
            if stored_inputs
            else int(NOMINAL_SATURN_PERIAPSIS_RADIUS_M / 1_000)
        ),
        step=100,
        help=(
            "Saturn-centred radius used by the connected capture burn. It must lie "
            "strictly outside the approximately 140,180 km F-ring reference radius."
        ),
    )
    connected_capture_apoapsis_radius_km = st.number_input(
        "Connected capture-ellipse apoapsis (km)",
        value=int(TITAN_MEAN_ORBIT_RADIUS_M / 1_000),
        disabled=True,
        help=(
            "Fixed Saturn-centred endpoint at Titan's 1,221,870 km mean orbital radius. "
            "This is not a phased Titan encounter or Titan capture."
        ),
    )
    st.warning(
        "The connected periapsis must remain outside the F-ring reference radius. "
        "The 62,330 km internal ring-corridor geometry is available only as an "
        "explicitly isolated legacy study on Saturn & Titan studies."
    )
    # Legacy studies remain inspectable on Saturn & Titan studies, but are no
    # longer editable mission inputs and never feed the connected budget.
    saturn_periapsis_radius_km = 62_330.0
    saturn_staging_radius_km = 600_000.0
    titan_capture_altitude_km = 1_500.0

    st.header(UI_TEXT["launch_window_header"])
    launch_window_start = st.date_input(
        UI_TEXT["launch_start"],
        value=(
            stored_inputs.launch_window_start
            if stored_inputs
            else app_services.DEFAULT_LAUNCH_WINDOW_START
        ),
    )
    launch_window_end = st.date_input(
        UI_TEXT["launch_end"],
        value=(
            stored_inputs.launch_window_end
            if stored_inputs
            else app_services.DEFAULT_LAUNCH_WINDOW_END
        ),
    )
    submitted = st.form_submit_button(UI_TEXT["calculate"], icon=":material/calculate:")

st.info(UI_TEXT["titan_scope"])

connected_destination_names = ", ".join(MOON_DESTINATIONS.keys())
planned_destination_names = ", ".join(PLANNED_DESTINATIONS)
# One cohesive markdown list instead of one isolated bullet per st.write call.
planned_features = tuple(feature for feature in PLANNED_MISSION_FEATURES if feature.strip())
# Each of the three sources renders only if it actually has content, and the
# whole expander renders only if at least one of them does - an empty
# collection must never leave behind a bare "-", "*", or empty placeholder.
if connected_destination_names or planned_destination_names or planned_features:
    with st.expander(UI_TEXT["planned_capabilities"]):
        if connected_destination_names:
            st.write(UI_TEXT["connected_destinations"] + connected_destination_names)
        if planned_destination_names:
            st.write(UI_TEXT["planned_destinations"] + planned_destination_names)
        if planned_features:
            st.markdown("\n".join(f"- {feature}" for feature in planned_features))

st.header(UI_TEXT["propulsion_header"])
isp_s = st.number_input(
    UI_TEXT["isp"],
    min_value=100,
    value=int(stored_inputs.isp_s) if stored_inputs else 320,
)

st.header(UI_TEXT["instruments_header"])
st.caption(UI_TEXT["instruments_caption"])

catalog_options = catalog_by_label()
selected_catalog_labels = st.multiselect(
    UI_TEXT["instrument_catalog_label"],
    options=list(catalog_options.keys()),
    default=[],
    help=UI_TEXT["instrument_catalog_help"],
)
st.caption(UI_TEXT["instrument_catalog_caption"])

if stored_inputs is None:
    instrument_rows = [
        {
            "Instrument": "Science payload (aggregate)",
            "Cible": "Orbiter",
            "Masse (kg)": 143.5,
            "Puissance (W)": 323.0,
            "Débit (bps)": 0.0,
        },
    ]
    instrument_rows.extend(catalog_row(catalog_options[label]) for label in selected_catalog_labels)
    default_instruments = pd.DataFrame(instrument_rows)
else:
    default_instruments = stored_inputs.instruments_df.copy()
    existing_instrument_names = set(default_instruments["Instrument"].astype(str))
    selected_rows = [
        catalog_row(catalog_options[label])
        for label in selected_catalog_labels
        if catalog_options[label].name not in existing_instrument_names
    ]
    if selected_rows:
        default_instruments = pd.concat(
            [default_instruments, pd.DataFrame(selected_rows)],
            ignore_index=True,
        )
instruments_df = st.data_editor(
    default_instruments,
    num_rows="dynamic",
    width="stretch",
    column_config={
        "Instrument": st.column_config.TextColumn("Instrument"),
        "Cible": st.column_config.TextColumn("Target"),
        "Masse (kg)": st.column_config.NumberColumn("Mass (kg)", min_value=0.0),
        "Puissance (W)": st.column_config.NumberColumn("Power (W)", min_value=0.0),
        "Débit (bps)": st.column_config.NumberColumn(
            "Data rate (bps; 0 = not available)", min_value=0.0
        ),
    },
)

if launch_window_end < launch_window_start:
    st.error(UI_TEXT["invalid_dates"])
    st.stop()
if connected_saturn_periapsis_radius_km * 1_000.0 <= F_RING_REFERENCE_RADIUS_M:
    st.error("Connected Saturn periapsis must lie strictly outside the reference F ring.")
    st.stop()
if connected_capture_apoapsis_radius_km <= connected_saturn_periapsis_radius_km:
    st.error("Connected capture-ellipse apoapsis must exceed its periapsis.")
    st.stop()

mission_inputs = app_services.MissionSetupInputs(
    destination=destination,
    selected_moon=selected_moon,
    departure_type=departure_type,
    leo_altitude_km=leo_altitude_km,
    saturn_periapsis_radius_km=saturn_periapsis_radius_km,
    saturn_staging_radius_km=saturn_staging_radius_km,
    titan_capture_altitude_km=titan_capture_altitude_km,
    launch_window_start=launch_window_start,
    launch_window_end=launch_window_end,
    isp_s=isp_s,
    instruments_df=instruments_df,
    trajectory_type=trajectory_type,
    connected_saturn_periapsis_radius_km=connected_saturn_periapsis_radius_km,
    connected_capture_apoapsis_radius_km=connected_capture_apoapsis_radius_km,
)
app_services.store_mission_setup_inputs(mission_inputs)
ui_state = update_draft_inputs(
    load_ui_state(st.session_state), snapshot_from_inputs(mission_inputs)
)
store_ui_state(st.session_state, ui_state)
if submitted:
    submitted_query = app_services.encode_mission_setup_query(mission_inputs)
    st.query_params[app_services.MISSION_QUERY_PARAM] = submitted_query[
        app_services.MISSION_QUERY_PARAM
    ]
    st.session_state["mission_share_url"] = app_services.build_mission_share_url(
        st.context.url or "http://localhost:8501",
        submitted_query,
    )

active_launch_candidate = st.session_state.get(lw.ACTIVE_LAUNCH_WINDOW_CANDIDATE_STATE_KEY)
if submitted and not isinstance(active_launch_candidate, lw.LaunchWindowCandidate):
    store_ui_state(st.session_state, begin_calculation(load_ui_state(st.session_state)))
if isinstance(active_launch_candidate, lw.LaunchWindowCandidate):
    candidate_id = active_launch_candidate.scenario_id or (
        f"candidate #{active_launch_candidate.rank}"
    )
    candidate_mass = compute_mass_budget(
        active_launch_candidate.delta_v_total_m_s,
        mission_inputs.isp_s,
        mission_inputs.instruments_df,
    )
    with scorecard_slot.container(border=True):
        st.subheader(":material/dashboard: Mission scorecard")
        st.caption(f"Active scenario: {lw.MISSION_SCENARIO_LAUNCH_WINDOW_LABEL} — {candidate_id}.")
        st.caption(
            "Date source: selected Launch windows Lambert solution "
            f"({active_launch_candidate.departure_datetime.date().isoformat()} → "
            f"{active_launch_candidate.saturn_arrival_datetime.date().isoformat()})."
        )
        with st.container(horizontal=True):
            st.metric(
                "Connected Saturn periapsis",
                f"{NOMINAL_SATURN_PERIAPSIS_RADIUS_M / 1_000:,.0f} km",
                border=True,
            )
            st.metric(
                "Final Saturn-centred radius",
                f"{TITAN_MEAN_ORBIT_RADIUS_M / 1_000:,.0f} km",
                border=True,
            )
        st.metric(
            "Connected delta-v",
            f"{active_launch_candidate.delta_v_total_m_s:,.1f} m/s",
            border=True,
        )
        st.metric(
            "Wet mass (simplified — selected candidate budget)",
            f"{candidate_mass['wet_mass_kg']:,.0f} kg",
            border=True,
        )
        st.caption(
            "Simplified wet mass applies the selected candidate's unchanged delta-v "
            "budget to the current Mission setup Isp and payload mass model; it is not "
            "an additional trajectory or delta-v calculation."
        )
        st.metric(
            "Earth → Saturn flight time",
            f"{active_launch_candidate.time_of_flight_days:,.1f} days",
            border=True,
        )
        st.metric(
            "Total reference-scenario duration",
            f"{active_launch_candidate.total_duration_days:,.2f} days",
            border=True,
        )
        st.caption(
            "Delta-v and durations above are copied directly from the selected "
            "Launch windows candidate. No Mission setup trajectory or connected "
            "budget is recomputed while this scenario is active."
        )
        if st.button("Return to mission baseline", icon=":material/undo:"):
            st.session_state.pop(lw.ACTIVE_LAUNCH_WINDOW_CANDIDATE_STATE_KEY, None)
            restore_baseline_scenario(st.session_state)
            st.rerun()
    st.stop()

bundle = app_services.require_mission_bundle()
if bundle is None:
    st.stop()
if submitted:
    ui_state = calculation_succeeded(
        load_ui_state(st.session_state), calculated_at=datetime.now(UTC)
    )
    ui_state = (
        activate_cassini_historical_reference(ui_state)
        if trajectory_type == app_services.TRAJECTORY_TYPE_CASSINI_HISTORICAL
        else return_to_baseline(ui_state)
    )
    store_ui_state(st.session_state, ui_state)

displayed_dv_rows = list(bundle.complete_dv_budget.as_dict().items())
if trajectory_type == app_services.TRAJECTORY_TYPE_CASSINI_HISTORICAL:
    displayed_dv_rows[1] = (
        "Venus/Venus/Earth/Jupiter flybys (unpowered)",
        displayed_dv_rows[1][1],
    )
    displayed_dv_rows[2] = (
        "Saturn Orbit Insertion (SOI)",
        displayed_dv_rows[2][1],
    )
else:
    displayed_dv_rows[1] = (
        UI_TEXT["dsm_not_modeled"],
        displayed_dv_rows[1][1],
    )
    # The connected Saturn->Titan chain's authoritative model always converts
    # to an injection burn (see app_services.compute_mission_bundle), so the
    # "Direct" relabel below only applies where departure_type genuinely still
    # selects the unconverted v∞ - the planet-only path.
    if departure_type == "Direct" and bundle.connected_first_order is None:
        displayed_dv_rows[0] = (
            UI_TEXT["direct_departure_value"],
            displayed_dv_rows[0][1],
        )

trajectory = bundle.earth_saturn_trajectory
assert trajectory.departure_mjd2000 is not None
assert trajectory.arrival_mjd2000 is not None
assert trajectory.v_inf_depart is not None
assert trajectory.v_inf_arrival is not None
pdf_report = MissionPdfReport(
    destination=destination,
    selected_moon=selected_moon,
    launch_window_start=launch_window_start,
    launch_window_end=launch_window_end,
    departure_mjd2000=trajectory.departure_mjd2000,
    arrival_mjd2000=trajectory.arrival_mjd2000,
    mission_duration_days=bundle.mission_duration_days,
    method=trajectory.method or "lambert",
    v_inf_depart_m_s=trajectory.v_inf_depart,
    v_inf_arrival_m_s=trajectory.v_inf_arrival,
    delta_v_rows=tuple(displayed_dv_rows),
    delta_v_total_m_s=bundle.dv_total,
)
pdf_bytes = generate_mission_summary_pdf(pdf_report)

with scorecard_slot.container(border=True):
    st.subheader(":material/dashboard: Mission scorecard")
    active_label = (
        lw.MISSION_SCENARIO_CASSINI_LABEL
        if trajectory_type == app_services.TRAJECTORY_TYPE_CASSINI_HISTORICAL
        else lw.MISSION_SCENARIO_BASELINE_LABEL
    )
    st.caption(f"Active scenario: {active_label}.")
    if active_label == lw.MISSION_SCENARIO_BASELINE_LABEL:
        st.page_link(
            "pages/launch_windows.py",
            label="Find an optimized launch window",
            icon=":material/search:",
            help=(
                "Opens Launch windows to search for a candidate departure date. "
                "Does not change the active scenario above by itself."
            ),
        )
    if trajectory_type == app_services.TRAJECTORY_TYPE_CASSINI_HISTORICAL:
        st.caption("Date source: historical Cassini VVEJGA encounter dates.")
        st.metric("Connected Saturn periapsis", "Historical SOI geometry", border=True)
        st.metric("Final Saturn-centred radius", "Historical post-SOI orbit", border=True)
    elif bundle.connected_first_order is not None:
        departure_date_str = _format_mjd2000_as_utc_date(
            bundle.earth_saturn_trajectory.departure_mjd2000
        )
        arrival_date_str = _format_mjd2000_as_utc_date(
            bundle.earth_saturn_trajectory.arrival_mjd2000
        )
        st.caption(
            "Date source: Mission setup Earth → Saturn trajectory solution "
            f"({departure_date_str} → {arrival_date_str} UTC)."
        )
        st.caption(
            "MJD2000 epoch reference (technical): "
            f"{bundle.earth_saturn_trajectory.departure_mjd2000:.3f} → "
            f"{bundle.earth_saturn_trajectory.arrival_mjd2000:.3f}."
        )
        with st.container(horizontal=True):
            st.metric(
                "Connected Saturn periapsis",
                f"{bundle.connected_first_order.saturn_capture.periapsis_radius_m / 1_000:,.0f} km",
                border=True,
            )
            st.metric(
                "Final Saturn-centred radius",
                f"{bundle.connected_first_order.saturn_capture.apoapsis_radius_m / 1_000:,.0f} km",
                border=True,
            )
    else:
        st.caption("Date source: Mission setup trajectory solution.")
        st.metric("Connected Saturn periapsis", "Not applicable", border=True)
        st.metric("Final Saturn-centred radius", "Not applicable", border=True)
    st.metric("Connected delta-v", f"{bundle.dv_total:,.0f} m/s", border=True)
    st.metric("Wet mass (simplified)", f"{bundle.mass['wet_mass_kg']:,.0f} kg", border=True)
    earth_saturn_flight_days = float(bundle.earth_saturn_trajectory.arrival_mjd2000) - float(
        bundle.earth_saturn_trajectory.departure_mjd2000
    )
    st.metric(
        "Earth → Saturn flight time",
        f"{earth_saturn_flight_days:,.1f} days",
        border=True,
    )
    st.metric(
        "Total reference-scenario duration",
        f"{bundle.mission_duration_days:,.1f} days",
        help=(
            "For the direct baseline this spans the heliocentric transfer and the "
            "Saturn-centred coast from periapsis to the reference apoapsis. It is "
            "not a phased Titan encounter or Titan capture."
        ),
        border=True,
    )
    st.metric(
        "Single-stage exceedance",
        f"{bundle.single_stage_feasibility.threshold_exceedance_factor:.2f}×",
        border=True,
    )
    st.caption("Live connected-budget values for the active baseline scenario.")
    st.caption(
        "Gravity-assist delta-v savings are not included above and are not available "
        "without a connected multi-leg trajectory (see Gravity assists for isolated, "
        "unpowered flyby demonstrators only)."
    )

with st.container(horizontal=True):
    if st.button("Copy share link", icon=":material/link:"):
        current_query = app_services.encode_mission_setup_query(mission_inputs)
        st.query_params[app_services.MISSION_QUERY_PARAM] = current_query[
            app_services.MISSION_QUERY_PARAM
        ]
        st.session_state["mission_share_url"] = app_services.build_mission_share_url(
            st.context.url or "http://localhost:8501",
            current_query,
        )
    st.download_button(
        "Download mission summary PDF",
        data=pdf_bytes,
        file_name=f"earth-to-{destination.lower()}-mission-summary.pdf",
        mime="application/pdf",
        icon=":material/download:",
        on_click="ignore",
    )
if share_url := st.session_state.get("mission_share_url"):
    st.caption("Use the copy control in the code block to share this exact mission setup.")
    if "localhost" in share_url or "127.0.0.1" in share_url:
        st.warning(
            "This localhost link is usable only on this machine while the app is not deployed."
        )
    st.code(share_url, language=None)

st.header(UI_TEXT["results_header"])
if trajectory_type == app_services.TRAJECTORY_TYPE_CASSINI_HISTORICAL:
    st.info(
        "Historical Cassini-style gravity-assist trajectory: delta-v and duration below "
        "are the real Earth-departure injection, the real Saturn Orbit Insertion (SOI) "
        "burn, and the real October 1997 - July 2004 cruise - not a Lambert solve of the "
        "launch window or moon selection above."
    )
else:
    st.info(UI_TEXT["complete_chain_note"])

st.subheader(UI_TEXT["provisional_budget"])
st.caption(UI_TEXT["budget_caption"])
st.caption("Mission-phase key — the same colors used on every page and chart below:")
with st.container(horizontal=True):
    for phase in colors.PHASE_ORDER:
        label = (
            phase.label if phase in _CONNECTED_BUDGET_PHASES else f"{phase.label} (not included)"
        )
        st.badge(label, color=colors.BADGE_COLOR[phase.label])
st.caption(
    "Lunar transfer and Landing are not modeled in this connected budget and do not "
    "contribute to the delta-v total above."
)
dv_table = pd.DataFrame(
    displayed_dv_rows,
    columns=[UI_TEXT["maneuver"], UI_TEXT["value_m_s"]],
)
st.dataframe(dv_table, width="stretch")
st.metric(UI_TEXT["dv_sum"], f"{bundle.dv_total:.0f} m/s")

st.subheader(UI_TEXT["mass_budget"])
st.warning(UI_TEXT["mass_model_warning"], icon=":material/warning:")
if departure_type == "Direct":
    st.warning(UI_TEXT["direct_warning"])
if bundle.mass_ratio > 20:
    st.warning(
        f"Simplified mass ratio: {bundle.mass_ratio:,.0f}. This indicates that one "
        f"non-discarding chemical stage at {isp_s:.0f} s is unsuitable for the modeled "
        "delta-v; see the calibrated feasibility study below."
    )
c1, c2, c3, c4 = st.columns(4)
c1.metric(UI_TEXT["instrument_mass"], f"{bundle.mass['instrument_mass_kg']:.1f} kg")
c2.metric(UI_TEXT["dry_mass"], f"{bundle.mass['dry_mass_kg']:.1f} kg")
c3.metric(UI_TEXT["propellant_mass"], f"{bundle.mass['propellant_mass_kg']:.1f} kg")
c4.metric(UI_TEXT["wet_mass"], f"{bundle.mass['wet_mass_kg']:.1f} kg")
