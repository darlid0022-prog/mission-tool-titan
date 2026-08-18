"""Mission setup: destination, launch window, propulsion, instruments, and
the connected propulsive delta-v/mass budget that directly results from them.

This is the page every other page depends on: submitting the form stores the
simple input values in st.session_state (see app_services.MissionSetupInputs)
so other pages can rebuild the same derived results via
app_services.require_mission_bundle() without recomputing or duplicating any
business logic here.
"""

import pandas as pd
import streamlit as st

import app_services
from mission import colors
from mission.capabilities import (
    MOON_DESTINATIONS,
    PLANET_DESTINATIONS,
    PLANNED_DESTINATIONS,
    PLANNED_MISSION_FEATURES,
)
from mission.payload_catalog import catalog_by_label, catalog_row
from mission.pdf_report import MissionPdfReport, generate_mission_summary_pdf
from mission.ui_text import UI_TEXT

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
    saturn_periapsis_radius_km = st.number_input(
        UI_TEXT["periapsis_radius"],
        min_value=60_269,
        max_value=66_899,
        value=int(stored_inputs.saturn_periapsis_radius_km) if stored_inputs else 62_330,
        step=100,
        help=UI_TEXT["periapsis_radius_help"],
    )
    saturn_staging_radius_km = st.number_input(
        UI_TEXT["staging_radius"],
        min_value=480_001,
        max_value=1_221_899,
        value=int(stored_inputs.saturn_staging_radius_km) if stored_inputs else 600_000,
        step=1_000,
        help=UI_TEXT["staging_radius_help"],
    )
    titan_capture_altitude_km = st.number_input(
        UI_TEXT["titan_capture_altitude"],
        min_value=1_000,
        value=int(stored_inputs.titan_capture_altitude_km) if stored_inputs else 1_500,
        step=100,
        help=UI_TEXT["titan_capture_help"],
    )

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

with st.expander(UI_TEXT["planned_capabilities"]):
    st.write(UI_TEXT["connected_destinations"] + ", ".join(MOON_DESTINATIONS.keys()))
    st.write(UI_TEXT["planned_destinations"] + ", ".join(PLANNED_DESTINATIONS))
    for feature in PLANNED_MISSION_FEATURES:
        st.write(f"- {feature}")

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
)
app_services.store_mission_setup_inputs(mission_inputs)
if submitted:
    submitted_query = app_services.encode_mission_setup_query(mission_inputs)
    st.query_params[app_services.MISSION_QUERY_PARAM] = submitted_query[
        app_services.MISSION_QUERY_PARAM
    ]
    st.session_state["mission_share_url"] = app_services.build_mission_share_url(
        st.context.url or "http://localhost:8501",
        submitted_query,
    )

bundle = app_services.require_mission_bundle()
if bundle is None:
    st.stop()

displayed_dv_rows = list(bundle.complete_dv_budget.as_dict().items())
displayed_dv_rows[1] = (
    UI_TEXT["dsm_not_modeled"],
    displayed_dv_rows[1][1],
)
if departure_type == "Direct":
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
    st.metric("Connected delta-v", f"{bundle.dv_total:,.0f} m/s", border=True)
    st.metric("Wet mass (simplified)", f"{bundle.mass['wet_mass_kg']:,.0f} kg", border=True)
    st.metric("Duration to Titan", f"{bundle.mission_duration_days:,.1f} days", border=True)
    st.metric(
        "Single-stage exceedance",
        f"{bundle.single_stage_feasibility.threshold_exceedance_factor:.2f}×",
        border=True,
    )
    st.metric(
        "Flyby gain coverage",
        f"{bundle.flyby_deficit_coverage:.1%}"
        if bundle.flyby_deficit_coverage is not None
        else "N/A",
        border=True,
    )
    st.caption(
        "Live connected-budget values. Flyby coverage compares the sum of the isolated "
        "Venus, Earth, and Jupiter demonstrations with the current single-stage delta-v deficit."
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
    st.code(share_url, language=None)

st.header(UI_TEXT["results_header"])
st.info(UI_TEXT["complete_chain_note"])

st.subheader(UI_TEXT["provisional_budget"])
st.caption(UI_TEXT["budget_caption"])
st.caption("Mission-phase key — the same colors used on every page and chart below:")
with st.container(horizontal=True):
    for phase in colors.PHASE_ORDER:
        st.badge(phase.label, color=colors.BADGE_COLOR[phase.label])
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
