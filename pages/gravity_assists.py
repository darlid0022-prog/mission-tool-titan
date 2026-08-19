"""Isolated gravity-assist flyby demonstrators.

Energy-conserving patched-conic demonstrations that take no arguments and
are not wired into the connected mission chain or its budget, so this page
needs no session_state from Mission setup.
"""

import math

import streamlit as st

from mission.gravity_assist import (
    EARTH_ALTITUDE_SOURCE,
    FIRST_VENUS_ALTITUDE_SOURCE,
    JUPITER_ALTITUDE_SOURCE,
    compute_earth_flyby_demonstration,
    compute_jupiter_flyby_demonstration,
    compute_venus_flyby_demonstration,
)

flyby_demonstrations = (
    compute_venus_flyby_demonstration(),
    compute_earth_flyby_demonstration(),
    compute_jupiter_flyby_demonstration(),
)

# Real Cassini flyby altitudes (see the _SOURCE citations below), one
# independent unpowered-turn demonstrator per body - not the connected
# five-leg VVEJGA tour. mission.gravity_assist also implements the second
# Venus flyby (compute_second_venus_flyby_demonstration,
# SECOND_VENUS_ALTITUDE_SOURCE) for the historical Cassini tour reconstruction
# elsewhere in the app; it is deliberately not added as a fourth card here.
_FLYBY_ALTITUDE_SOURCE = {
    "Venus": FIRST_VENUS_ALTITUDE_SOURCE,
    "Earth": EARTH_ALTITUDE_SOURCE,
    "Jupiter": JUPITER_ALTITUDE_SOURCE,
}

st.header(":material/rocket_launch: Gravity-assist flyby demonstrators")
st.caption(
    "Three independent demonstrators, one per body flown by. The reference VVEJGA "
    "architecture includes two Venus flybys; the second is not yet modeled here. "
    "These demonstrators do not reconstitute the reference sequence, and their "
    "gains are not additive."
)
st.caption(
    "Isolated, unpowered (non-propulsive), energy-conserving patched-conic "
    "demonstrations — each computed independently, on its own fixed dates. They do "
    "not form a connected VVEJGA trajectory, are not wired into the connected "
    "Earth → Saturn trajectory or its budget, and their heliocentric speed gains "
    "are not directly additive as delta-v savings (each flyby's gain depends on the "
    "incoming state the *previous* leg would have delivered, which none of these "
    "isolated demonstrators supplies to the next)."
)
for flyby_result in flyby_demonstrations:
    with st.container(border=True):
        st.subheader(f"{flyby_result.body} flyby")
        st.caption("Unpowered flyby — no propulsive delta-v is spent on this maneuver.")
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
            f"radius: {flyby_result.periapsis_radius_m / 1_000:,.0f} km (altitude is above "
            "the body's surface; radius is measured from its center — the two differ by the "
            "body's own radius) · body-frame v∞ magnitude is conserved."
        )
        st.caption(
            f"This is Cassini's real {flyby_result.body} flyby altitude — "
            f"Source: {_FLYBY_ALTITUDE_SOURCE[flyby_result.body]}"
        )
