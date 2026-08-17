"""Isolated gravity-assist flyby demonstrators.

Energy-conserving patched-conic demonstrations that take no arguments and
are not wired into the connected mission chain or its budget, so this page
needs no session_state from Mission setup.
"""

import math

import streamlit as st

from mission.gravity_assist import (
    compute_earth_flyby_demonstration,
    compute_jupiter_flyby_demonstration,
    compute_venus_flyby_demonstration,
)

flyby_demonstrations = (
    compute_venus_flyby_demonstration(),
    compute_earth_flyby_demonstration(),
    compute_jupiter_flyby_demonstration(),
)

st.header(":material/rocket_launch: Gravity-assist flyby demonstrators")
st.caption(
    "Isolated, energy-conserving patched-conic demonstrations. They are not wired into "
    "the connected Earth → Saturn → Titan trajectory or its budget."
)
for flyby_result in flyby_demonstrations:
    with st.container(border=True):
        st.subheader(f"{flyby_result.body} flyby")
        with st.container(horizontal=True):
            st.metric(
                "Incoming v∞", f"{flyby_result.v_infinity_magnitude_m_s:,.1f} m/s", border=True
            )
            st.metric(
                "Outgoing v∞",
                f"{math.sqrt(sum(value**2 for value in flyby_result.v_infinity_out_m_s)):,.1f} m/s",
                border=True,
            )
            st.metric(
                "Turn angle", f"{math.degrees(flyby_result.turn_angle_rad):.3f}°", border=True
            )
            st.metric(
                "Heliocentric speed gain",
                f"{flyby_result.heliocentric_speed_change_m_s:,.1f} m/s",
                border=True,
            )
        st.caption(
            f"Periapsis altitude: {flyby_result.periapsis_altitude_m / 1_000:,.0f} km · "
            f"radius: {flyby_result.periapsis_radius_m / 1_000:,.0f} km · "
            "body-frame v∞ magnitude is conserved."
        )
