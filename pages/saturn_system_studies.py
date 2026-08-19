"""Saturn hyperbolic-arrival/capture (authoritative model), plus the legacy
Saturn arrival-to-staging, Saturn -> Titan transfer, and Titan EDL studies -
all rebuilt from the mission-setup inputs stored in session_state.
"""

import math

import streamlit as st

import app_services
from mission import colors
from mission.constants import F_RING_REFERENCE_RADIUS_M
from mission.ui_text import UI_TEXT


def _bulleted(items: tuple[str, ...]) -> None:
    """Render one cohesive markdown list instead of one isolated bullet per call."""
    st.markdown("\n".join(f"- {item}" for item in items))


bundle = app_services.require_mission_bundle()
if bundle is None:
    st.stop()

# Saturn studies require a connected Saturn->Titan mission; for planet-only
# arrivals inform the user and stop instead of assuming Saturn-specific data.
if bundle.staging_result is None:
    st.info("Saturn system studies are available only when a moon destination (Titan) is selected.")
    st.stop()

staging_result = bundle.staging_result
titan_transfer = bundle.titan_transfer
titan_edl = bundle.titan_edl
connected = bundle.connected_first_order

# Two menu pages (Technical details, Isolated studies) both link here today -
# this reads back which one the reader came from (see the query_params on
# each st.page_link) to say why, without merging or duplicating this page.
_entry_section = st.query_params.get("section")
if _entry_section == "technical":
    st.caption(UI_TEXT["saturn_studies_entry_technical"])
elif _entry_section == "isolated":
    st.caption(UI_TEXT["saturn_studies_entry_isolated"])

st.header(UI_TEXT["connected_first_order_header"])
st.badge(colors.ARRIVAL.label, color=colors.BADGE_COLOR[colors.ARRIVAL.label])
if connected is None:
    # Explicit placeholder rather than a guessed number: this model is expected
    # to be populated whenever a connected Saturn->Titan mission is selected
    # (see app_services.compute_mission_bundle); if it is ever absent, say so
    # instead of silently falling back to the legacy sections below.
    st.warning(
        "The authoritative Saturn hyperbolic-arrival-and-capture model is not available "
        "for this mission configuration. Expected data interface: "
        "app_services.MissionBundle.connected_first_order "
        "(mission.connected_physics.ConnectedFirstOrderResult)."
    )
else:
    st.info(UI_TEXT["connected_first_order_warning"])
    with st.container(border=True):
        st.subheader(UI_TEXT["hyperbolic_arrival_subheader"])
        st.caption(UI_TEXT["hyperbolic_arrival_help"])
        with st.container(horizontal=True):
            st.metric(
                UI_TEXT["arrival_v_infinity_new"],
                f"{connected.arrival_v_infinity_m_s:,.1f} m/s",
                help=UI_TEXT["hyperbolic_arrival_help"],
                border=True,
            )
            st.metric(
                UI_TEXT["hyperbola_periapsis_radius"],
                f"{connected.saturn_hyperbola.periapsis_radius_m / 1_000:,.0f} km",
                help=UI_TEXT["radius_vs_altitude_help"],
                border=True,
            )
            st.metric(
                UI_TEXT["hyperbola_eccentricity"],
                f"{connected.saturn_hyperbola.eccentricity:.3f}",
                border=True,
            )
            st.metric(
                UI_TEXT["hyperbola_turn_angle"],
                f"{math.degrees(connected.saturn_hyperbola.turn_angle_rad):.1f}°",
                border=True,
            )

        f_ring_margin_m = connected.saturn_hyperbola.periapsis_radius_m - F_RING_REFERENCE_RADIUS_M
        st.metric(
            UI_TEXT["f_ring_margin"],
            f"{f_ring_margin_m / 1_000:,.0f} km",
            help=UI_TEXT["f_ring_margin_help"],
            border=True,
        )
        st.caption(UI_TEXT["f_ring_margin_scalar_limit"])

        st.subheader(UI_TEXT["propulsive_insertion_subheader"])
        st.caption(UI_TEXT["propulsive_insertion_help"])
        st.metric(
            UI_TEXT["insertion_delta_v"],
            f"{connected.saturn_capture.capture_delta_v_m_s:,.1f} m/s",
            border=True,
        )

        st.subheader(UI_TEXT["capture_ellipse_subheader"])
        st.caption(UI_TEXT["capture_ellipse_help"])
        with st.container(horizontal=True):
            st.metric(
                UI_TEXT["ellipse_periapsis_radius"],
                f"{connected.saturn_capture.periapsis_radius_m / 1_000:,.0f} km",
                help=UI_TEXT["radius_vs_altitude_help"],
                border=True,
            )
            st.metric(
                UI_TEXT["ellipse_apoapsis_radius"],
                f"{connected.saturn_capture.apoapsis_radius_m / 1_000:,.0f} km",
                help=UI_TEXT["radius_vs_altitude_help"],
                border=True,
            )
            st.metric(
                UI_TEXT["ellipse_eccentricity"],
                f"{connected.saturn_capture.eccentricity:.3f}",
                border=True,
            )
            st.metric(
                UI_TEXT["periapsis_apoapsis_duration"],
                f"{connected.saturn_capture.time_of_flight_days:.3f} days",
                border=True,
            )

        st.subheader(UI_TEXT["circularization_subheader"])
        st.caption(UI_TEXT["circularization_help"])
        st.metric(
            UI_TEXT["circularization_delta_v"],
            f"{connected.saturn_capture.circularisation_delta_v_m_s:,.1f} m/s",
            border=True,
        )

        st.caption(f"Method: `{connected.method}`.")

        with st.expander(UI_TEXT["assumptions_exclusions"]):
            st.markdown(UI_TEXT["assumptions"])
            _bulleted(connected.assumptions)
            st.markdown(UI_TEXT["exclusions"])
            _bulleted(connected.exclusions)

st.header(UI_TEXT["staging_header"])
st.badge(colors.ARRIVAL.label, color=colors.BADGE_COLOR[colors.ARRIVAL.label])
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
            help=UI_TEXT["radius_vs_altitude_help"],
            border=True,
        )
        st.metric(
            UI_TEXT["staging_radius"],
            f"{staging_result.staging_radius_m / 1_000:,.0f} km",
            help=UI_TEXT["radius_vs_altitude_help"],
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
        _bulleted(staging_result.assumptions)
        st.markdown(UI_TEXT["exclusions"])
        _bulleted(staging_result.exclusions)

st.header(UI_TEXT["titan_header"])
st.badge(colors.LUNAR_TRANSFER.label, color=colors.BADGE_COLOR[colors.LUNAR_TRANSFER.label])
st.warning(UI_TEXT["titan_warning"])

with st.container(border=True):
    st.subheader(UI_TEXT["study_parameters"])
    st.caption(UI_TEXT["shared_staging_radius"])
    st.metric(
        UI_TEXT["titan_capture_altitude"],
        f"{titan_transfer.titan_capture_altitude_m / 1_000:,.0f} km",
        help=UI_TEXT["radius_vs_altitude_help"],
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
        _bulleted(titan_transfer.assumptions)
        st.markdown(UI_TEXT["exclusions"])
        _bulleted(titan_transfer.exclusions)

st.header(UI_TEXT["titan_edl_header"])
st.badge(colors.LANDING.label, color=colors.BADGE_COLOR[colors.LANDING.label])
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
        _bulleted(titan_edl.assumptions)
        st.markdown(UI_TEXT["exclusions"])
        _bulleted(titan_edl.exclusions)

    with st.expander(UI_TEXT["edl_sources"]):
        _bulleted(titan_edl.sources)
