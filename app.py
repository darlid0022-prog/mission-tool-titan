"""Streamlit interface for the Mission Design Calculator."""

import math

import pandas as pd
import streamlit as st

from app_services import (
    DEFAULT_LAUNCH_WINDOW_END,
    DEFAULT_LAUNCH_WINDOW_START,
    PARETO_MODEL_VERSION,
    PHYSICS_MODEL_VERSION,
    compute_cached_pareto_front,
    compute_cached_trajectory,
)
from mission.capabilities import (
    CONNECTED_CHAIN_DESTINATIONS,
    PLANNED_DESTINATIONS,
    PLANNED_MISSION_FEATURES,
    SUPPORTED_DESTINATIONS,
)
from mission.dv_budget import compose_complete_dv_budget
from mission.feasibility_check import evaluate_single_stage_chemical_feasibility
from mission.full_mission import compute_earth_saturn_titan_mission
from mission.mass_model import PayloadItem
from mission.pareto_plot import build_pareto_front_figure, select_pareto_highlights
from mission.sizing import compute_mass_budget
from mission.titan_edl import compute_titan_edl
from mission.trajectory_plot import build_complete_mission_figure
from mission.trajectory_visualization import (
    CompleteMissionScene3D,
    MissionAnimationTimeline3D,
    build_complete_mission_scene,
    build_mission_animation_timeline,
    interpolate_spacecraft_position,
)
from mission.ui_text import UI_TEXT

ANIMATION_PHASE_OPTIONS = (
    "Earth → Saturn cruise",
    "Saturn arrival → staging",
    "Saturn → Titan",
)
ANIMATION_PHASE_SELECTOR_KEY = "mission_animation_phase"
ANIMATION_PHASE_ELAPSED_KEY = "mission_phase_elapsed_days"


def _reset_animation_phase_elapsed() -> None:
    """Return the marker to the start whenever the selected phase changes."""
    st.session_state[ANIMATION_PHASE_ELAPSED_KEY] = 0.0


def _animation_phase_timing(
    timeline: MissionAnimationTimeline3D,
    selected_phase: str,
) -> tuple[float, float]:
    """Return the absolute start and duration of one UI animation phase."""
    earth_duration = timeline.earth_saturn_duration_days
    staging_duration = timeline.saturn_staging_duration_days
    timings = {
        ANIMATION_PHASE_OPTIONS[0]: (0.0, earth_duration),
        ANIMATION_PHASE_OPTIONS[1]: (earth_duration, staging_duration),
        ANIMATION_PHASE_OPTIONS[2]: (
            earth_duration + staging_duration,
            timeline.saturn_titan_duration_days,
        ),
    }
    return timings[selected_phase]


def _absolute_animation_elapsed_days(
    selected_phase: str,
    phase_start_days: float,
    phase_duration_days: float,
    phase_elapsed_days: float,
) -> float:
    """Map phase-local UI time to the existing absolute animation timeline."""
    phase_end_days = phase_start_days + phase_duration_days
    if selected_phase != ANIMATION_PHASE_OPTIONS[-1] and phase_elapsed_days >= phase_duration_days:
        return math.nextafter(phase_end_days, phase_start_days)
    return phase_start_days + phase_elapsed_days


@st.fragment
def render_trajectory_animation(
    scene: CompleteMissionScene3D,
    timeline: MissionAnimationTimeline3D,
) -> None:
    """Rerun only the phase controls, marker, and chart when time changes."""
    st.session_state.setdefault(ANIMATION_PHASE_SELECTOR_KEY, ANIMATION_PHASE_OPTIONS[0])
    st.session_state.setdefault(ANIMATION_PHASE_ELAPSED_KEY, 0.0)
    selected_phase = st.segmented_control(
        UI_TEXT["mission_phase_selector"],
        ANIMATION_PHASE_OPTIONS,
        required=True,
        key=ANIMATION_PHASE_SELECTOR_KEY,
        help=UI_TEXT["mission_phase_selector_help"],
        on_change=_reset_animation_phase_elapsed,
        width="stretch",
    )
    assert isinstance(selected_phase, str)
    phase_start_days, phase_duration_days = _animation_phase_timing(timeline, selected_phase)
    saved_phase_elapsed = float(st.session_state[ANIMATION_PHASE_ELAPSED_KEY])
    if not 0.0 <= saved_phase_elapsed <= phase_duration_days:
        st.session_state[ANIMATION_PHASE_ELAPSED_KEY] = 0.0

    phase_elapsed_days = st.slider(
        UI_TEXT["phase_elapsed_time"],
        min_value=0.0,
        max_value=float(phase_duration_days),
        step=float(phase_duration_days / 20_000.0),
        format="%.2f days" if phase_duration_days >= 100.0 else "%.4f days",
        key=ANIMATION_PHASE_ELAPSED_KEY,
        help=UI_TEXT["phase_elapsed_time_help"],
    )
    elapsed_days = _absolute_animation_elapsed_days(
        selected_phase,
        phase_start_days,
        phase_duration_days,
        phase_elapsed_days,
    )
    spacecraft_position = interpolate_spacecraft_position(timeline, elapsed_days)
    with st.container(horizontal=True):
        st.metric(
            UI_TEXT["current_elapsed_time"],
            f"{spacecraft_position.elapsed_days:,.2f} days",
            border=True,
        )
        st.metric(
            UI_TEXT["current_mission_phase"],
            selected_phase,
            border=True,
        )
    trajectory_figure = build_complete_mission_figure(scene, spacecraft_position)
    st.plotly_chart(
        trajectory_figure,
        width="stretch",
        height=720,
        key="complete_mission_trajectory_3d",
        config={"displaylogo": False, "scrollZoom": True},
    )


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
        departure_type = st.radio(
            UI_TEXT["departure_type"],
            ["Direct", "LEO"],
            index=1,
            help=UI_TEXT["departure_type_help"],
        )
        leo_altitude_km = st.number_input(
            UI_TEXT["leo_altitude"],
            min_value=100,
            value=250,
            help=UI_TEXT["leo_help"],
        )
        saturn_periapsis_radius_km = st.number_input(
            UI_TEXT["periapsis_radius"],
            min_value=60_269,
            max_value=66_899,
            value=62_330,
            step=100,
            help=UI_TEXT["periapsis_radius_help"],
        )
        saturn_staging_radius_km = st.number_input(
            UI_TEXT["staging_radius"],
            min_value=480_001,
            max_value=1_221_899,
            value=600_000,
            step=1_000,
            help=UI_TEXT["staging_radius_help"],
        )
        titan_capture_altitude_km = st.number_input(
            UI_TEXT["titan_capture_altitude"],
            min_value=1_000,
            value=1_500,
            step=100,
            help=UI_TEXT["titan_capture_help"],
        )

        st.header(UI_TEXT["launch_window_header"])
        launch_window_start = st.date_input(
            UI_TEXT["launch_start"],
            value=DEFAULT_LAUNCH_WINDOW_START,
        )
        launch_window_end = st.date_input(
            UI_TEXT["launch_end"],
            value=DEFAULT_LAUNCH_WINDOW_END,
        )
        st.form_submit_button(UI_TEXT["calculate"], icon=":material/calculate:")

    st.info(UI_TEXT["titan_scope"])

    with st.expander(UI_TEXT["planned_capabilities"]):
        st.write(UI_TEXT["connected_destinations"] + ", ".join(CONNECTED_CHAIN_DESTINATIONS))
        st.write(UI_TEXT["planned_destinations"] + ", ".join(PLANNED_DESTINATIONS))
        for feature in PLANNED_MISSION_FEATURES:
            st.write(f"- {feature}")

    st.header(UI_TEXT["propulsion_header"])
    isp_s = st.number_input(UI_TEXT["isp"], min_value=100, value=320)

    st.header(UI_TEXT["instruments_header"])
    st.caption(UI_TEXT["instruments_caption"])
    default_instruments = pd.DataFrame(
        [
            {
                "Instrument": "Science payload (aggregate)",
                "Cible": "Orbiter",
                "Masse (kg)": 143.5,
                "Puissance (W)": 323.0,
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
            "Débit (bps)": st.column_config.NumberColumn(
                "Data rate (bps; 0 = not available)", min_value=0.0
            ),
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
    )
    complete_mission = compute_earth_saturn_titan_mission(
        traj["earth_saturn_leg"],
        saturn_periapsis_radius_m=float(saturn_periapsis_radius_km) * 1_000.0,
        saturn_periapsis_radius_provenance=(
            "User-selected Saturn-centered radius; nominal value preserves the "
            "PyKEP Saturn radius plus UI capture altitude."
        ),
        saturn_staging_radius_m=float(saturn_staging_radius_km) * 1_000.0,
        titan_capture_altitude_m=float(titan_capture_altitude_km) * 1_000.0,
    )

staging_result = complete_mission.saturn_arrival_staging
titan_transfer = complete_mission.saturn_titan_transfer
titan_edl = compute_titan_edl(
    titan_transfer.v_infinity_titan_m_s,
    titan_transfer.capture_delta_v_m_s,
)
complete_dv_budget = compose_complete_dv_budget(
    traj["dv_budget"],
    staging_result,
    titan_transfer,
)
dv_total = complete_dv_budget.total_m_s
mass = compute_mass_budget(dv_total, isp_s, instruments_df)
mass_ratio = mass["wet_mass_kg"] / mass["dry_mass_kg"] if mass["dry_mass_kg"] > 0 else 1.0
payload_items = tuple(
    PayloadItem(
        name=(str(row["Instrument"]).strip() or f"Payload item {index + 1}"),
        mass_kg=float(row["Masse (kg)"]),
        max_power_w=float(row["Puissance (W)"]),
        data_rate_bps=float(row["Débit (bps)"]),
    )
    for index, (_, row) in enumerate(instruments_df.fillna(0.0).iterrows())
)
single_stage_feasibility = evaluate_single_stage_chemical_feasibility(
    dv_total,
    float(isp_s),
    payload_items,
)


with col_results:
    st.header(UI_TEXT["results_header"])
    st.info(UI_TEXT["complete_chain_note"])

    st.subheader(UI_TEXT["provisional_budget"])
    st.caption(UI_TEXT["budget_caption"])
    displayed_dv_rows = list(complete_dv_budget.as_dict().items())
    displayed_dv_rows[1] = (
        UI_TEXT["dsm_not_modeled"],
        displayed_dv_rows[1][1],
    )
    if departure_type == "Direct":
        displayed_dv_rows[0] = (
            UI_TEXT["direct_departure_value"],
            displayed_dv_rows[0][1],
        )
    dv_table = pd.DataFrame(
        displayed_dv_rows,
        columns=[UI_TEXT["maneuver"], UI_TEXT["value_m_s"]],
    )
    st.dataframe(dv_table, width="stretch")
    st.metric(UI_TEXT["dv_sum"], f"{dv_total:.0f} m/s")

    st.subheader(UI_TEXT["mass_budget"])
    st.warning(UI_TEXT["mass_model_warning"], icon=":material/warning:")
    if departure_type == "Direct":
        st.warning(UI_TEXT["direct_warning"])
    if mass_ratio > 20:
        st.warning(
            f"Simplified mass ratio: {mass_ratio:,.0f}. This indicates that one "
            f"non-discarding chemical stage at {isp_s:.0f} s is unsuitable for the modeled "
            "delta-v; see the calibrated feasibility study below."
        )
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(UI_TEXT["instrument_mass"], f"{mass['instrument_mass_kg']:.1f} kg")
    c2.metric(UI_TEXT["dry_mass"], f"{mass['dry_mass_kg']:.1f} kg")
    c3.metric(UI_TEXT["propellant_mass"], f"{mass['propellant_mass_kg']:.1f} kg")
    c4.metric(UI_TEXT["wet_mass"], f"{mass['wet_mass_kg']:.1f} kg")

st.header(UI_TEXT["pareto_header"])
st.caption(UI_TEXT["pareto_caption"])
with st.container(border=True):
    with st.spinner(UI_TEXT["pareto_spinner"]):
        pareto_result = compute_cached_pareto_front(PARETO_MODEL_VERSION)
    pareto_highlights = select_pareto_highlights(pareto_result)
    pareto_figure = build_pareto_front_figure(pareto_result)
    st.plotly_chart(
        pareto_figure,
        width="stretch",
        height=540,
        key="connected_mission_pareto_front",
        config={"displaylogo": False, "scrollZoom": True},
    )
    baseline = pareto_highlights.baseline
    optimum = pareto_highlights.delta_v_optimum
    delta_v_percent = 100.0 * (baseline.total_delta_v_m_s / optimum.total_delta_v_m_s - 1.0)
    duration_percent = 100.0 * (baseline.total_duration_days / optimum.total_duration_days - 1.0)
    mass_percent = 100.0 * (baseline.wet_mass_kg / optimum.wet_mass_kg - 1.0)
    st.caption(
        UI_TEXT["pareto_comparison"].format(
            delta_v_difference=baseline.total_delta_v_m_s - optimum.total_delta_v_m_s,
            delta_v_percent=delta_v_percent,
            duration_difference=baseline.total_duration_days - optimum.total_duration_days,
            duration_percent=duration_percent,
            mass_difference=baseline.wet_mass_kg - optimum.wet_mass_kg,
            mass_percent=mass_percent,
        )
    )

st.header(UI_TEXT["single_stage_feasibility_header"])
st.caption(UI_TEXT["single_stage_feasibility_caption"])
with st.container(border=True):
    f1, f2, f3 = st.columns(3)
    f1.metric(
        UI_TEXT["single_stage_required_delta_v"],
        f"{single_stage_feasibility.required_delta_v_m_s:,.3f} m/s",
    )
    f2.metric(
        UI_TEXT["single_stage_maximum_delta_v"],
        f"{single_stage_feasibility.maximum_feasible_delta_v_m_s:,.3f} m/s",
    )
    f3.metric(
        UI_TEXT["single_stage_threshold_factor"],
        f"{single_stage_feasibility.threshold_exceedance_factor:.3f}×",
    )
    if single_stage_feasibility.is_feasible:
        st.success(UI_TEXT["single_stage_feasible"])
    else:
        st.info(UI_TEXT["single_stage_infeasible_finding"])
    st.caption(
        UI_TEXT["single_stage_model_source"].format(
            model_version=single_stage_feasibility.model_version
        )
    )

st.header(UI_TEXT["trajectory_3d_header"])
st.caption(UI_TEXT["trajectory_3d_caption"])
with st.container(border=True):
    earth_saturn_trajectory = complete_mission.mission.legs[0].trajectory
    assert earth_saturn_trajectory is not None
    trajectory_scene_key = (
        earth_saturn_trajectory.departure_mjd2000,
        earth_saturn_trajectory.arrival_mjd2000,
        staging_result.periapsis_radius_m,
        staging_result.staging_radius_m,
        titan_transfer.titan_orbit_radius_m,
    )
    if st.session_state.get("trajectory_scene_key") != trajectory_scene_key:
        trajectory_scene = build_complete_mission_scene(complete_mission)
        trajectory_timeline = build_mission_animation_timeline(
            trajectory_scene,
            complete_mission,
        )
        st.session_state["trajectory_scene_key"] = trajectory_scene_key
        st.session_state["trajectory_scene"] = trajectory_scene
        st.session_state["trajectory_timeline"] = trajectory_timeline
    render_trajectory_animation(
        st.session_state["trajectory_scene"],
        st.session_state["trajectory_timeline"],
    )

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
