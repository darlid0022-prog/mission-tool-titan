"""Streamlit interface for the Mission Design Calculator."""

import pandas as pd
import streamlit as st

from app_services import PHYSICS_MODEL_VERSION, compute_cached_trajectory
from mission.capabilities import (
    PLANNED_DESTINATIONS,
    PLANNED_MISSION_FEATURES,
    SUPPORTED_DESTINATIONS,
)
from mission.moon_transfer import compute_saturn_titan_transfer
from mission.saturn_staging import compute_saturn_arrival_to_staging
from mission.sizing import compute_mass_budget
from mission.ui_text import UI_TEXT

st.set_page_config(page_title="Mission Design - Titan", layout="wide")
st.title(":material/satellite_alt: Mission Design Calculator")
st.caption(UI_TEXT["app_caption"])

# -----------------------------------------------------------------------
# 2. ENTRÉES - colonne de gauche : architecture de mission
# -----------------------------------------------------------------------
col_inputs, col_results = st.columns([1, 2])

with col_inputs:
    with st.form("orbital_inputs"):
        st.header(UI_TEXT["architecture_header"])
        destination = st.selectbox(
            UI_TEXT["destination_label"],
            SUPPORTED_DESTINATIONS,
            help=UI_TEXT["destination_help"],
        )
        departure_type = st.radio(UI_TEXT["departure_type"], ["Direct", "LEO"])
        leo_altitude_km = st.number_input(
            UI_TEXT["leo_altitude"],
            min_value=100,
            value=250,
            help=UI_TEXT["leo_help"],
        )
        capture_altitude_km = st.number_input(
            UI_TEXT["saturn_capture_altitude"], min_value=0, value=2000
        )

        st.header(UI_TEXT["launch_window_header"])
        launch_window_start = st.date_input(UI_TEXT["launch_start"])
        launch_window_end = st.date_input(UI_TEXT["launch_end"])
        st.form_submit_button(UI_TEXT["calculate"], icon=":material/calculate:")

    st.info(UI_TEXT["titan_scope"])

    with st.expander(UI_TEXT["planned_capabilities"]):
        st.write(UI_TEXT["planned_destinations"] + ", ".join(PLANNED_DESTINATIONS))
        for feature in PLANNED_MISSION_FEATURES:
            st.write(f"- {feature}")

    st.header(UI_TEXT["propulsion_header"])
    isp_s = st.number_input(UI_TEXT["isp"], min_value=1, value=320)

    st.header(UI_TEXT["instruments_header"])
    st.caption(UI_TEXT["instruments_caption"])
    default_instruments = pd.DataFrame(
        [
            {
                "Instrument": "",
                "Cible": "Orbiter",
                "Masse (kg)": 0.0,
                "Puissance (W)": 0.0,
                "Débit (bps)": 0.0,
            },
        ]
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
            "Débit (bps)": st.column_config.NumberColumn("Data rate (bps)", min_value=0.0),
        },
    )

if launch_window_end < launch_window_start:
    st.error(UI_TEXT["invalid_dates"])
    st.stop()

with st.spinner(UI_TEXT["earth_saturn_spinner"]):
    traj = compute_cached_trajectory(
        PHYSICS_MODEL_VERSION,
        destination,
        departure_type,
        launch_window_start,
        launch_window_end,
        leo_altitude_km,
        capture_altitude_km,
    )
mass = compute_mass_budget(traj["dv_total"], isp_s, instruments_df)
mass_ratio = mass["wet_mass_kg"] / mass["dry_mass_kg"] if mass["dry_mass_kg"] > 0 else 1.0

with col_results:
    st.header(UI_TEXT["results_header"])
    st.info(traj["note"])

    st.subheader(UI_TEXT["provisional_budget"])
    st.caption(UI_TEXT["budget_caption"])
    dv_table = pd.DataFrame(
        traj["dv_budget"].items(), columns=[UI_TEXT["maneuver"], UI_TEXT["value_m_s"]]
    )
    st.dataframe(dv_table, width="stretch")
    st.metric(UI_TEXT["dv_sum"], f"{traj['dv_total']:.0f} m/s")

    st.subheader(UI_TEXT["mass_budget"])
    if departure_type == "Direct":
        st.warning(UI_TEXT["direct_warning"])
    if mass_ratio > 20:
        st.warning(
            f"Estimated mass ratio: {mass_ratio:,.0f}. Chemical propulsion at "
            f"{isp_s:.0f} s is unrealistic for this delta-v budget without a "
            "multi-stage architecture."
        )
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(UI_TEXT["instrument_mass"], f"{mass['instrument_mass_kg']:.1f} kg")
    c2.metric(UI_TEXT["dry_mass"], f"{mass['dry_mass_kg']:.1f} kg")
    c3.metric(UI_TEXT["propellant_mass"], f"{mass['propellant_mass_kg']:.1f} kg")
    c4.metric(UI_TEXT["wet_mass"], f"{mass['wet_mass_kg']:.1f} kg")

st.divider()
st.header(UI_TEXT["staging_header"])
st.warning(UI_TEXT["staging_warning"])

with st.container(border=True):
    st.subheader(UI_TEXT["study_parameters"])
    staging_input_1, staging_input_2, staging_input_3 = st.columns(3)
    with staging_input_1:
        saturn_arrival_v_infinity_m_s = st.number_input(
            UI_TEXT["arrival_v_infinity"],
            min_value=0.0,
            value=6_490.744714263188,
            step=100.0,
            help=UI_TEXT["arrival_v_infinity_help"],
        )
    with staging_input_2:
        saturn_periapsis_radius_km = st.number_input(
            UI_TEXT["periapsis_radius"],
            min_value=60_269,
            max_value=66_899,
            value=62_330,
            step=100,
            help=UI_TEXT["periapsis_radius_help"],
        )
    with staging_input_3:
        saturn_staging_radius_km = st.number_input(
            UI_TEXT["staging_radius"],
            min_value=480_001,
            max_value=1_221_899,
            value=600_000,
            step=1_000,
            help=UI_TEXT["staging_radius_help"],
        )

    staging_result = compute_saturn_arrival_to_staging(
        arrival_v_infinity_m_s=float(saturn_arrival_v_infinity_m_s),
        periapsis_radius_m=float(saturn_periapsis_radius_km) * 1_000.0,
        staging_radius_m=float(saturn_staging_radius_km) * 1_000.0,
        periapsis_radius_provenance=(
            "User-selected Saturn-centered radius; nominal value preserves the "
            "PyKEP Saturn radius plus UI capture altitude."
        ),
    )

    st.caption(
        f"Method: `{staging_result.method}` · Source: `{staging_result.source}` · "
        f"Replaces: `{staging_result.replaces_budget_term}`."
    )
    with st.container(horizontal=True):
        st.metric(
            UI_TEXT["capture_to_ellipse_dv"],
            f"{staging_result.capture_to_ellipse_delta_v_m_s:,.1f} m/s",
            border=True,
        )
        st.metric(
            UI_TEXT["staging_circularisation_dv"],
            f"{staging_result.staging_circularisation_delta_v_m_s:,.1f} m/s",
            border=True,
        )
        st.metric(
            UI_TEXT["staging_phase_total_dv"],
            f"{staging_result.total_delta_v_m_s:,.1f} m/s",
            border=True,
        )
        st.metric(
            UI_TEXT["staging_tof"],
            f"{staging_result.time_of_flight_days:.3f} days",
            border=True,
        )

    st.subheader(UI_TEXT["ring_constraints"])
    st.warning(
        "Planet–ring corridor at periapsis: the selected periapsis is "
        f"{staging_result.periapsis_below_d_ring_inner_edge_m / 1_000:,.0f} km below "
        "the D ring's inner edge. Cassini's 2017 Grand Finale flew through this corridor, "
        "which RPWS observations found to be largely dust-free. This is a relevant flight "
        "precedent, but the scalar model still cannot verify the transfer ellipse's full "
        "three-dimensional ring-plane geometry."
    )
    with st.container(horizontal=True):
        st.metric(
            UI_TEXT["d_ring_clearance"],
            f"{staging_result.periapsis_below_d_ring_inner_edge_m / 1_000:,.0f} km",
            help="Positive clearance within the planet–D-ring corridor at periapsis.",
            border=True,
        )
        st.metric(
            UI_TEXT["e_ring_margin"],
            f"+{staging_result.staging_e_ring_radial_margin_m / 1_000:,.0f} km",
            help="Radial margin of the final circular staging orbit only.",
            border=True,
        )

    with st.expander(UI_TEXT["assumptions_exclusions"]):
        st.markdown(UI_TEXT["assumptions"])
        for assumption in staging_result.assumptions:
            st.write(f"- {assumption}")
        st.markdown(UI_TEXT["exclusions"])
        for exclusion in staging_result.exclusions:
            st.write(f"- {exclusion}")

st.divider()
st.header(UI_TEXT["titan_header"])
st.warning(UI_TEXT["titan_warning"])

with st.container(border=True):
    st.subheader(UI_TEXT["study_parameters"])
    st.caption(UI_TEXT["shared_staging_radius"])
    titan_capture_altitude_km = st.number_input(
        UI_TEXT["titan_capture_altitude"],
        min_value=1_000,
        value=1_500,
        step=100,
        help=UI_TEXT["titan_capture_help"],
    )

    titan_transfer = compute_saturn_titan_transfer(
        saturn_staging_radius_m=float(saturn_staging_radius_km) * 1_000.0,
        titan_capture_altitude_m=float(titan_capture_altitude_km) * 1_000.0,
    )

    st.caption(
        f"Method: `{titan_transfer.method}` · Source: `{titan_transfer.source}` · "
        "Circular, coplanar, impulsive calculation."
    )
    with st.container(horizontal=True):
        st.metric(
            UI_TEXT["departure_dv"],
            f"{titan_transfer.departure_delta_v_m_s:,.1f} m/s",
            border=True,
        )
        st.metric(
            UI_TEXT["titan_v_infinity"],
            f"{titan_transfer.v_infinity_titan_m_s:,.1f} m/s",
            help=UI_TEXT["titan_v_infinity_help"],
            border=True,
        )
        st.metric(
            UI_TEXT["titan_capture_dv"],
            f"{titan_transfer.capture_delta_v_m_s:,.1f} m/s",
            border=True,
        )
        st.metric(
            UI_TEXT["partial_total_dv"],
            f"{titan_transfer.total_delta_v_m_s:,.1f} m/s",
            border=True,
        )

    st.metric(
        UI_TEXT["titan_tof"],
        f"{titan_transfer.time_of_flight_days:.3f} days",
        help=f"{titan_transfer.time_of_flight_s:,.0f} seconds.",
        border=True,
    )

    with st.expander(UI_TEXT["assumptions_exclusions"]):
        st.markdown(UI_TEXT["assumptions"])
        for assumption in titan_transfer.assumptions:
            st.write(f"- {assumption}")
        st.markdown(UI_TEXT["exclusions"])
        for exclusion in titan_transfer.exclusions:
            st.write(f"- {exclusion}")
