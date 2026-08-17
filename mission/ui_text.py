"""Central English copy for the Streamlit interface."""

from typing import Final

UI_TEXT: Final[dict[str, str]] = {
    "app_caption": (
        "Deterministic first-order Earth → Saturn → Titan mission chain with explicit "
        "propulsive delta-v, simplified mass sizing, and isolated feasibility studies."
    ),
    "architecture_header": "1. Mission architecture",
    "destination_label": "Interplanetary solver target",
    "destination_help": (
        "The Lambert solver targets Saturn; the connected mission chain then continues to Titan."
    ),
    "departure_type": "Departure type",
    "departure_type_help": (
        "LEO converts the Lambert departure v∞ into the required injection burn at the "
        "selected parking-orbit altitude. Direct displays the unconverted v∞ instead."
    ),
    "direct_departure_value": "Earth departure v∞ (direct mode)",
    "leo_altitude": "Initial LEO altitude (km)",
    "leo_help": "Used only when the departure type is LEO.",
    "launch_window_header": "2. Launch window",
    "launch_start": "Launch date — start",
    "launch_end": "Launch date — end",
    "calculate": "Calculate trajectory",
    "titan_scope": (
        "Titan is connected through the preliminary Saturn staging and moon-transfer "
        "models. Their assumptions and exclusions remain visible below."
    ),
    "planned_capabilities": "Planned capabilities",
    "connected_destinations": "Connected mission destinations: ",
    "planned_destinations": "Destinations: ",
    "propulsion_header": "3. Propulsion",
    "isp": "Main engine specific impulse (s)",
    "instruments_header": "4. Instruments",
    "instruments_caption": (
        "The default aggregate science payload is 143.5 kg and 323 W. Add or edit rows "
        "directly; a zero data rate means that no aggregate value is currently available."
    ),
    "invalid_dates": "The end date must be on or after the start date.",
    "earth_saturn_spinner": "Calculating the Earth → Saturn trajectory…",
    "results_header": "Results (updated after calculation)",
    "complete_chain_note": (
        "Connected first-order Earth → Saturn → Titan budget. The legacy circular "
        "Saturn-capture term is replaced by the modeled capture-to-ellipse and staging "
        "circularization burns."
    ),
    "provisional_budget": "Connected propulsive delta-v budget",
    "budget_caption": (
        "The displayed values include every currently modeled propulsive burn. A zero for "
        "DSM / fly-by corrections explicitly means that this architecture models no such "
        "maneuver; it is not a missing numerical result."
    ),
    "dsm_not_modeled": "DSM / fly-by corrections (not modeled)",
    "maneuver": "Maneuver",
    "value_m_s": "Value (m/s)",
    "dv_sum": "Sum of budgeted delta-v values",
    "mass_budget": "Mass budget",
    "mass_model_warning": (
        "Simplified sizing model — does not couple propulsion hardware mass to propellant "
        "mass. See the single-stage feasibility study below for the calibrated model's "
        "conclusion on this mission's delta-v budget."
    ),
    "direct_warning": (
        "Direct mode still treats departure v∞ as a preliminary equivalent delta-v. "
        "The mass budget is not a launch-vehicle sizing result."
    ),
    "instrument_mass": "Instrument mass",
    "dry_mass": "Simplified dry mass",
    "propellant_mass": "Simplified propellant mass",
    "wet_mass": "Simplified total wet mass",
    "pareto_header": "Connected mission trade space — Pareto front",
    "pareto_caption": (
        "The fixed 1,176-point study varies Earth departure date and Earth → Saturn time "
        "of flight. All 38 non-dominated points are shown; marker color reports wet mass, "
        "which is not an independent objective with the fixed 320 s Isp and 143.5 kg "
        "aggregate payload. "
        "This uses the simplified sizing model, which does not couple propulsion hardware "
        "mass to propellant mass. See the single-stage feasibility study below for the "
        "calibrated model's conclusion on this mission's delta-v budget."
    ),
    "pareto_spinner": "Loading the deterministic Pareto front…",
    "pareto_comparison": (
        "The reproducible 2,856-day Earth → Saturn baseline is kept as the connected "
        "mission reference. Relative to the sampled minimum-delta-v point, it requires "
        "{delta_v_difference:.3f} m/s more (+{delta_v_percent:.2f}%), "
        "{duration_difference:.0f} more days (+{duration_percent:.2f}%), and "
        "{mass_difference:.3f} kg more simplified wet mass (+{mass_percent:.2f}%)."
    ),
    "single_stage_feasibility_header": "Single-stage chemical feasibility — preliminary model",
    "single_stage_feasibility_caption": (
        "This isolated Hesperos-calibrated study tests one non-discarding chemical stage. "
        "It is not merged into the connected delta-v, mass budget, or Pareto objectives."
    ),
    "single_stage_required_delta_v": "Required connected delta-v",
    "single_stage_maximum_delta_v": "Maximum feasible single-stage delta-v",
    "single_stage_threshold_factor": "Required / feasible threshold",
    "single_stage_feasible": "The calibrated single-stage mass solution converges.",
    "single_stage_infeasible_finding": (
        "The calibrated model confirms that this delta-v budget is not feasible with one "
        "non-discarding chemical stage. The mission requires a multi-stage or discardable-stage "
        "architecture, a delta-v reduction strategy such as Cassini-Huygens-style VVEJGA gravity "
        "assists, or both. This is a model finding, not an application error. Multi-stage sizing "
        "is outside the current scope."
    ),
    "single_stage_model_source": "Calibrated mass-model version: {model_version}.",
    "trajectory_3d_header": "Complete mission trajectory — interactive 3D view",
    "trajectory_3d_caption": (
        "Drag to rotate, scroll to zoom, and double-click to reset. The heliocentric and "
        "Saturn-centred panels use different reference frames and scales. Body sizes are not "
        "shown to scale."
    ),
    "mission_phase_selector": "Mission phase",
    "mission_phase_selector_help": (
        "Selects one mission phase and resets the spacecraft marker to that phase's start."
    ),
    "phase_elapsed_time": "Elapsed time within selected phase",
    "phase_elapsed_time_help": (
        "Moves the spacecraft marker within the selected phase using pre-sampled trajectory "
        "points, without rerunning the orbital solver."
    ),
    "current_elapsed_time": "Current mission-elapsed time",
    "current_mission_phase": "Current mission phase",
    "staging_header": "Saturn arrival → staging orbit — preliminary model",
    "staging_warning": (
        "Energy estimate only: ring-plane clearance is unresolved. This phase replaces "
        "the legacy circular Saturn-capture term in the connected budget."
    ),
    "arrival_v_infinity": "Saturn arrival v∞ (m/s)",
    "arrival_v_infinity_help": (
        "Saturn-relative hyperbolic excess speed supplied by the Earth → Saturn leg."
    ),
    "periapsis_radius": "Capture periapsis radius (km)",
    "periapsis_radius_help": (
        "Saturn-centered radius. The nominal value preserves the current PyKEP "
        "60,330 km radius plus a 2,000 km capture altitude."
    ),
    "capture_to_ellipse_dv": "Capture-to-ellipse delta-v",
    "staging_circularisation_dv": "Staging circularization delta-v",
    "staging_phase_total_dv": "Arrival-to-staging total delta-v",
    "staging_tof": "Periapsis-to-apoapsis time",
    "ring_constraints": "Ring-system constraints",
    "d_ring_clearance": "Periapsis below D-ring inner edge",
    "e_ring_margin": "Staging orbit beyond E-ring edge",
    "titan_header": "Saturn → Titan — preliminary model",
    "titan_warning": (
        "This phase is included in the connected propulsive and mass budgets. The model "
        "remains preliminary and retains the exclusions listed below."
    ),
    "study_parameters": "Study parameters",
    "staging_radius": "Saturn staging-orbit radius (km)",
    "staging_radius_help": (
        "Radius measured from Saturn's center. The lower bound is beyond the "
        "preliminary ring guard."
    ),
    "shared_staging_radius": (
        "This study uses the same Saturn staging-orbit radius selected in the "
        "arrival-to-staging section above."
    ),
    "titan_capture_altitude": "Titan capture altitude (km)",
    "titan_capture_help": (
        "Altitude above Titan's mean radius. The model applies a preliminary "
        "1,000 km non-atmospheric guard."
    ),
    "departure_dv": "Departure delta-v from staging orbit",
    "titan_v_infinity": "Titan-relative v∞ (non-propulsive)",
    "titan_v_infinity_help": (
        "Hyperbolic arrival speed relative to Titan, distinct from propulsive delta-v."
    ),
    "titan_capture_dv": "Titan capture delta-v",
    "partial_total_dv": "Saturn → Titan modeled delta-v",
    "titan_tof": "Saturn → Titan time of flight",
    "titan_edl_header": "Titan EDL — preliminary ballistic-entry model",
    "titan_edl_warning": (
        "Exploratory alternative only: this direct-entry study is not included in the "
        "connected delta-v or mass budget and does not replace the connected circular-capture "
        "reference case."
    ),
    "edl_incoming_v_infinity": "Incoming Titan-relative v∞",
    "edl_interface_altitude": "Atmospheric-interface altitude",
    "edl_ballistic_coefficient": "Ballistic coefficient",
    "edl_entry_angle": "Entry flight-path angle",
    "edl_interface_velocity": "Atmospheric-interface entry velocity",
    "edl_deployment_speed": "Target parachute-deployment speed",
    "edl_deployment_altitude": "Estimated deployment altitude",
    "edl_atmospheric_reduction": "Atmospheric velocity reduction",
    "edl_atmospheric_reduction_help": (
        "Drag-induced speed reduction, not a propulsive delta-v and not a budget term."
    ),
    "edl_capture_savings": "Avoided circular-capture burn",
    "edl_capture_savings_help": (
        "Propulsive-equivalent saving relative only to the currently budgeted Titan "
        "circular-capture burn. Terminal descent and landing propulsion are not modeled."
    ),
    "edl_sources": "Scientific sources",
    "assumptions_exclusions": "Model assumptions and exclusions",
    "assumptions": "**Assumptions**",
    "exclusions": "**Exclusions**",
}
