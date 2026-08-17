"""Isolated Saturn arrival-to-staging, Saturn -> Titan transfer, and Titan
EDL studies, rebuilt from the mission-setup inputs stored in session_state.
"""

import streamlit as st

import app_services
from mission.ui_text import UI_TEXT

bundle = app_services.require_mission_bundle()
if bundle is None:
    st.stop()

staging_result = bundle.staging_result
titan_transfer = bundle.titan_transfer
titan_edl = bundle.titan_edl

st.header(UI_TEXT["staging_header"])
st.warning(UI_TEXT["staging_warning"])

with st.container(border=True):
    st.subheader(UI_TEXT["study_parameters"])
    with st.container(horizontal=True):
        st.metric(
            UI_TEXT["arrival_v_infinity"],
            f"{staging_result.arrival_v_infinity_m_s:,.1f} m/s",
            help=UI_TEXT["arrival_v_infinity_help"],
            border=True,
        )
        st.metric(
            UI_TEXT["periapsis_radius"],
            f"{staging_result.periapsis_radius_m / 1_000:,.0f} km",
            border=True,
        )
        st.metric(
            UI_TEXT["staging_radius"],
            f"{staging_result.staging_radius_m / 1_000:,.0f} km",
            border=True,
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

st.header(UI_TEXT["titan_header"])
st.warning(UI_TEXT["titan_warning"])

with st.container(border=True):
    st.subheader(UI_TEXT["study_parameters"])
    st.caption(UI_TEXT["shared_staging_radius"])
    st.metric(
        UI_TEXT["titan_capture_altitude"],
        f"{titan_transfer.titan_capture_altitude_m / 1_000:,.0f} km",
        border=True,
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

st.header(UI_TEXT["titan_edl_header"])
st.warning(UI_TEXT["titan_edl_warning"])

with st.container(border=True):
    st.subheader(UI_TEXT["study_parameters"])
    with st.container(horizontal=True):
        st.metric(
            UI_TEXT["edl_incoming_v_infinity"],
            f"{titan_edl.incoming_v_infinity_m_s:,.1f} m/s",
            border=True,
        )
        st.metric(
            UI_TEXT["edl_interface_altitude"],
            f"{titan_edl.entry_interface_altitude_m / 1_000:,.0f} km",
            border=True,
        )
        st.metric(
            UI_TEXT["edl_ballistic_coefficient"],
            f"{titan_edl.ballistic_coefficient_kg_m2:.0f} kg/m²",
            border=True,
        )
        st.metric(
            UI_TEXT["edl_entry_angle"],
            f"−{titan_edl.entry_flight_path_angle_deg:.0f}°",
            border=True,
        )

    st.caption(f"Method: `{titan_edl.method}` · Direct entry; no prior Titan orbit.")
    with st.container(horizontal=True):
        st.metric(
            UI_TEXT["edl_interface_velocity"],
            f"{titan_edl.entry_velocity_m_s:,.1f} m/s",
            border=True,
        )
        st.metric(
            UI_TEXT["edl_deployment_speed"],
            f"{titan_edl.parachute_deployment_speed_m_s:,.0f} m/s",
            border=True,
        )
        st.metric(
            UI_TEXT["edl_deployment_altitude"],
            f"{titan_edl.estimated_parachute_deployment_altitude_m / 1_000:,.1f} km",
            border=True,
        )
        st.metric(
            UI_TEXT["edl_atmospheric_reduction"],
            f"{titan_edl.atmospheric_velocity_reduction_m_s:,.1f} m/s",
            help=UI_TEXT["edl_atmospheric_reduction_help"],
            border=True,
        )

    st.metric(
        UI_TEXT["edl_capture_savings"],
        f"{titan_edl.propulsive_equivalent_savings_m_s:,.1f} m/s",
        help=UI_TEXT["edl_capture_savings_help"],
        border=True,
    )

    with st.expander(UI_TEXT["assumptions_exclusions"]):
        st.markdown(UI_TEXT["assumptions"])
        for assumption in titan_edl.assumptions:
            st.write(f"- {assumption}")
        st.markdown(UI_TEXT["exclusions"])
        for exclusion in titan_edl.exclusions:
            st.write(f"- {exclusion}")

    with st.expander(UI_TEXT["edl_sources"]):
        for source in titan_edl.sources:
            st.write(f"- {source}")
