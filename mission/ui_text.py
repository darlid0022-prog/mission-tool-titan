"""Central English copy for the Streamlit interface."""

from typing import Final

UI_TEXT: Final[dict[str, str]] = {
    "app_caption": (
        "Deterministic first-order Earth → Saturn mission chain — ending in a "
        "Saturn-centered orbit at Titan's orbital radius, not a Titan encounter — with "
        "explicit propulsive delta-v, simplified mass sizing, and isolated feasibility "
        "studies."
    ),
    "architecture_header": "1. Mission architecture",
    "destination_label": "Interplanetary solver target",
    "destination_help": (
        "The Lambert solver's target planet. Every Lambert-capable planet computes a real "
        "direct arrival; only Saturn currently has a connected moon-transfer chain (Titan)."
    ),
    "moon_label": "Moon destination (optional)",
    "moon_help": (
        "A moon reachable from the selected planet through the connected staging-and-transfer "
        "chain, or direct arrival only if no moon is selected."
    ),
    "no_moon_option": "Direct arrival only (no moon)",
    "destination_not_implemented": (
        "This destination is not implemented yet. Select a Lambert-capable planet to use "
        "the direct-arrival engine."
    ),
    "direct_arrival_only_note": (
        "Direct planetary arrival only: the connected budget, 3D trajectory view, and "
        "Saturn/Titan-specific studies below require selecting a moon destination "
        "(currently Titan, reached through Saturn)."
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
        "The connected budget reaches a Saturn-centered orbit at Titan's orbital radius, "
        "not Titan itself. Legacy Saturn staging, Titan-transfer, and Titan-entry studies "
        "remain available on Saturn & Titan studies. They are isolated from the connected "
        "budget."
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
    "instrument_catalog_label": "Add named instruments from the catalogue",
    "instrument_catalog_help": (
        "Named Orbiter/Lander instrument slots, inspired by real interplanetary missions. "
        "Selecting one adds a zero-mass, zero-power placeholder row below - fill in the real, "
        "sourced mass/power/data-rate values yourself, exactly as in the original spreadsheet."
    ),
    "instrument_catalog_caption": (
        "Catalogue entries carry no assumed mass or power: this tool does not ship "
        "unsourced instrument specifications. Edit each added row with a documented "
        "reference (e.g. a flown analogous instrument) before using it for sizing."
    ),
    "invalid_dates": "The end date must be on or after the start date.",
    "earth_saturn_spinner": "Calculating the Earth → Saturn trajectory…",
    "results_header": "Results (updated after calculation)",
    "complete_chain_note": (
        "Connected first-order Earth → Saturn budget, ending in a Saturn-centered orbit "
        "at Titan's orbital radius. The legacy circular Saturn-capture term is replaced "
        "by the modeled capture-to-ellipse and circularization burns; no Titan encounter "
        "or capture is included."
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
    "single_stage_allocation_bracket": (
        "Single-stage exceedance by allocation (not determined by the model): "
        "· entire Earth injection charged to the spacecraft: {vehicle_bound:.3f}× "
        "({required_delta_v_m_s:,.3f} m/s) "
        "· entire Earth injection charged to the launcher: {launcher_bound:.3f}× "
        "({saturn_subtotal_m_s:,.3f} m/s). "
        "Both bounds are conditional. The current model does not determine the "
        "allocation among a launcher, upper stage, and spacecraft."
    ),
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
    "saturn_studies_entry_technical": (
        "Arrived from Technical details — reviewing the connected model's arrival "
        "geometry, reference frames, hyperbola, and ellipse parameters."
    ),
    "saturn_studies_entry_isolated": (
        "Arrived from Isolated studies — reviewing legacy and Titan/EDL results that "
        "are excluded from the connected budget below."
    ),
    "connected_first_order_header": "Saturn hyperbolic arrival & capture — authoritative model",
    "connected_first_order_warning": (
        "This model feeds the connected delta-v budget and mission duration shown on "
        "Mission setup. Its endpoint is a Saturn-centered circular orbit at Titan's mean "
        "orbital radius — it does not model a Titan encounter, flyby, or Titan-centered "
        "capture."
    ),
    "hyperbolic_arrival_subheader": "Hyperbolic arrival",
    "hyperbolic_arrival_help": (
        "The incoming, unpowered planetocentric approach before any capture burn. v∞ "
        "(hyperbolic excess speed) is the Saturn-relative arrival speed."
    ),
    "arrival_v_infinity_new": "Saturn arrival v∞",
    "hyperbola_periapsis_radius": "Hyperbola periapsis radius",
    "hyperbola_eccentricity": "Hyperbola eccentricity",
    "hyperbola_turn_angle": "Hyperbola deflection angle",
    "f_ring_margin": "Margin outside F ring",
    "f_ring_margin_help": (
        "Periapsis radius minus the reference F-ring radius, both measured from Saturn's "
        "center. A positive margin means periapsis stays outside the F ring in this "
        "scalar, coplanar model — it is not a three-dimensional ring-plane clearance."
    ),
    "insertion_delta_v": "Insertion delta-v",
    "circularization_delta_v": "Circularization delta-v",
    "propulsive_insertion_subheader": "Propulsive capture-to-ellipse insertion",
    "propulsive_insertion_help": (
        "An impulsive engine burn at periapsis. Unlike every flyby demonstrator in this "
        "app, this maneuver costs real propulsive delta-v — it is not a gravity assist."
    ),
    "capture_ellipse_subheader": "Capture ellipse",
    "capture_ellipse_help": (
        "The bound orbit reached immediately after the capture burn: periapsis at the "
        "hyperbola's periapsis, apoapsis at Titan's mean orbital radius."
    ),
    "ellipse_periapsis_radius": "Ellipse periapsis radius",
    "ellipse_apoapsis_radius": "Ellipse apoapsis radius",
    "ellipse_eccentricity": "Ellipse eccentricity",
    "periapsis_apoapsis_duration": "Periapsis → apoapsis time",
    "circularization_subheader": "Circularization at Titan's orbital radius",
    "circularization_help": (
        "A second impulsive burn at apoapsis, circularizing into a Saturn-centered orbit "
        "at Titan's mean orbital radius. This orbit is co-orbital with Titan, not a Titan "
        "encounter, flyby, or capture — no Titan-centered maneuver is modeled here."
    ),
    "radius_vs_altitude_help": (
        "Radius is measured from the body's center; altitude is measured above its "
        "surface (or cloud tops for a giant planet). The two differ by the body's own "
        "radius, so they are not interchangeable."
    ),
    "staging_header": "Legacy internal ring-corridor arrival → staging study",
    "staging_warning": (
        "Legacy reference model, kept for comparison: it no longer feeds the connected "
        "delta-v budget above, which uses the authoritative hyperbolic-arrival-and-capture "
        "model instead. Energy estimate only — ring-plane clearance remains unresolved."
    ),
    "arrival_v_infinity": "Saturn arrival v∞ (m/s)",
    "arrival_v_infinity_help": (
        "Saturn-relative hyperbolic excess speed supplied by the Earth → Saturn leg."
    ),
    "periapsis_radius": "Legacy internal-corridor periapsis radius (km)",
    "periapsis_radius_help": (
        "Saturn-centered radius. The nominal value preserves the current PyKEP "
        "60,330 km radius plus a 2,000 km capture altitude. Feeds only the legacy "
        "arrival-to-staging study on Saturn & Titan studies, not the authoritative "
        "connected delta-v budget above, which uses a fixed 150,000 km design periapsis."
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
        "Legacy reference model, kept for comparison: this Saturn → Titan Hohmann phase "
        "is no longer included in the connected propulsive or mass budgets, which use the "
        "authoritative Saturn-capture model instead. It remains preliminary and retains "
        "the exclusions listed below."
    ),
    "study_parameters": "Study parameters",
    "staging_radius": "Legacy staging-study radius (km)",
    "staging_radius_help": (
        "Radius measured from Saturn's center. The lower bound is beyond the "
        "preliminary ring guard. Feeds only the legacy Saturn → Titan study on Saturn "
        "& Titan studies, not the authoritative connected delta-v budget above."
    ),
    "shared_staging_radius": (
        "This study uses the same Saturn staging-orbit radius selected in the "
        "arrival-to-staging section above."
    ),
    "titan_capture_altitude": "Isolated Titan capture-study altitude (km)",
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
        "Exploratory alternative only: this direct-entry study assumes an incoming "
        "Titan-relative hyperbola that is not produced by any connected model in this app "
        "(the authoritative Saturn-capture model above never reaches Titan). It is not "
        "included in the connected delta-v or mass budget."
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
        "Propulsive-equivalent saving relative only to the legacy Saturn → Titan study's "
        "Titan circular-capture burn above (not a term in the connected delta-v budget). "
        "Terminal descent and landing propulsion are not modeled."
    ),
    "edl_sources": "Scientific sources",
    "assumptions_exclusions": "Model assumptions and exclusions",
    "assumptions": "**Assumptions**",
    "exclusions": "**Exclusions**",
}


# v0.3.0 copy is kept in a separate, namespaced catalogue while the existing
# pages continue to consume UI_TEXT unchanged. Later UI batches can migrate one
# screen at a time without duplicating visible strings in rendering code.
UI_V030_TEXT: Final[dict[str, str]] = {
    "navigation_primary": "Mission workflow",
    "navigation_secondary": "Reference",
    "technical_details_title": "Technical details",
    "technical_details_introduction": (
        "Inspect the scientific outputs and diagnostics that support the active scenario."
    ),
    "isolated_studies_title": "Isolated studies",
    "isolated_studies_introduction": (
        "Explore reference studies that do not contribute to the connected mission total."
    ),
    "active_scenario": "Active scenario",
    "scenario_id": "Scenario ID",
    "calculated_at": "Calculated at",
    "scenario_technical_metadata": "Scenario technical metadata",
    "model_scope": "Model scope",
    "assumptions_and_limitations": "Assumptions and limitations",
    "technical_details_disclosure": "Technical details",
    "progress_label": "Mission progress",
    "current_step": "Current step",
    "calculation_status_label": "Calculation status",
    "status_input_error": "Input error — previous results preserved",
    "status_no_solution": "No solution — previous results preserved",
    "status_technical_error": "Technical error — previous results preserved",
    "trajectory_direct_3d_section": "Direct trajectory in 3D",
    "trajectory_direct_3d_description": (
        "Inspect the active scenario in static 3D or Direct animation, with playback, "
        "segment details, and standalone HTML export."
    ),
    "trajectory_launch_windows_section": "Explore launch windows",
    "trajectory_launch_windows_description": (
        "Search the connected Earth → Saturn model, inspect its real Pareto front, and "
        "explicitly apply a selected candidate."
    ),
    "trajectory_reference_duration": "Reference duration",
    "trajectory_duration_complete": "Complete reference scenario duration",
    "trajectory_duration_interplanetary": "Earth–Saturn interplanetary flight time",
    "trajectory_duration_saturn_phase": "Saturn periapsis-to-apoapsis transfer",
    "trajectory_duration_unavailable": (
        "A Saturn periapsis-to-apoapsis breakdown is not available for this scenario."
    ),
    "trajectory_3d_animated_transfer_label": "Direct Earth–Saturn Lambert transfer",
    "trajectory_last_search": "Last search",
    "trajectory_no_search": "No launch-window search in this session",
    "trajectory_search_candidates": "candidates available",
    "trajectory_launch_windows": "Explore launch windows and Pareto front",
    "trajectory_open_3d": "Open 3D trajectory",
    "trajectory_transition_note": (
        "The existing launch-window search and 3D views remain available during this transition."
    ),
    "budget_transition_note": (
        "Detailed budget presentation will be reorganized in a later update. Existing calculated "
        "results remain available from Mission."
    ),
    "verdict_transition_note": (
        "The consolidated model conclusion will be completed in a later update. No new "
        "feasibility threshold is introduced here."
    ),
    "technical_saturn": "Saturn and Titan model details",
    "technical_pareto": "Fixed Pareto study",
    "isolated_gravity": "Gravity-assist demonstrations",
    "isolated_feasibility": "Single-stage feasibility study",
    "isolated_saturn": "Legacy Saturn and Titan studies",
    "return_to_mission": "Return to Mission",
    "product_description": (
        "Preliminary Earth–Saturn mission design using a deterministic first-order model."
    ),
    "status_current": "Results up to date",
    "status_stale": "Inputs changed — recalculation required",
    "status_running": "Calculation in progress",
    "status_empty": "No results available",
    "badge_isolated": "Not connected to the active mission",
    "badge_technical": "Technical detail",
    "badge_connected": "Connected mission",
    "badge_excluded": "Not included in connected total",
    "mission_title": "Mission",
    "mission_introduction": (
        "Define the modeled objective, mission architecture, and primary inputs."
    ),
    "mission_final_state_heading": "Modeled final state",
    "mission_final_state_value": ("Saturn-centered circular orbit at Titan's mean orbital radius"),
    "mission_titan_warning": (
        "This Saturn-centered circularization is not a Titan encounter, flyby, capture, "
        "or Titan-centered orbit."
    ),
    "mission_architecture_heading": "Modeled mission architecture",
    "mission_allocation_note": (
        "Allocation of Earth injection and the other maneuvers to a launcher, upper "
        "stage, or spacecraft depends on the selected architecture. This allocation is "
        "not currently modeled."
    ),
    "mission_calculate": "Calculate mission",
    "mission_recalculate": "Recalculate mission",
    "mission_continue": "Continue to Trajectory",
    "trajectory_title": "Trajectory",
    "trajectory_introduction": (
        "Review the dates, duration, transfer geometry, and arrival in the Saturn system."
    ),
    "trajectory_dates_heading": "Dates and duration",
    "trajectory_window_heading": "Launch window",
    "trajectory_3d_heading": "3D heliocentric trajectory",
    "trajectory_arrival_heading": "Arrival at Saturn",
    "trajectory_exploration_heading": "Explore launch windows",
    "trajectory_method_note": (
        "Playback interpolates the sampled trajectory points. It is not an independent "
        "dynamical propagation."
    ),
    "trajectory_departure_marker": "Earth departure",
    "trajectory_arrival_marker": "Arrival in the Saturn system",
    "trajectory_spacecraft_marker": "Sampled spacecraft position",
    "trajectory_play": "Play",
    "trajectory_pause": "Pause",
    "trajectory_reset": "Reset",
    "trajectory_show_legend": "Show legend",
    "trajectory_show_segments": "Show segment data",
    "trajectory_apply": "Apply this scenario",
    "trajectory_continue": "Continue to Budget",
    "budget_title": "Budget",
    "budget_introduction": (
        "Separate departure energy, modeled Earth injection delta-v, and the Saturn "
        "maneuvers in the connected mission chain."
    ),
    "budget_departure_heading": "Earth departure conditions",
    "budget_c3_label": "Earth C3",
    "budget_v_infinity_label": "Earth v∞",
    "budget_injection_heading": "Modeled Earth injection",
    "budget_allocation_explanation": (
        "Allocation of this maneuver to a launcher, upper stage, or spacecraft depends "
        "on the selected architecture. No real launch vehicle is currently modeled."
    ),
    "budget_saturn_heading": "Modeled Saturn maneuvers",
    "budget_capture_label": "Saturn capture",
    "budget_circularization_label": "Saturn-centered circularization",
    "budget_saturn_subtotal": "Subtotal of modeled Saturn maneuvers",
    "budget_saturn_subtotal_explanation": (
        "This subtotal excludes Modeled Earth injection and is not the complete mission budget."
    ),
    "budget_total_heading": "Connected total",
    "budget_total_explanation": (
        "The connected total includes modeled Earth injection, Saturn capture, and "
        "Saturn-centered circularization."
    ),
    "budget_energy_note": (
        "C3 and v∞ characterize the departure energy conditions. They are not additional "
        "delta-v contributions to the connected total."
    ),
    "budget_mass_heading": "Simplified mass estimate",
    "budget_mass_note": (
        "This estimate uses the application's simplified mass model. It is not a complete "
        "vehicle design."
    ),
    "budget_previous_result_note": (
        "Inputs have changed. The values below belong to the previous calculation, not "
        "to the current draft inputs."
    ),
    "budget_no_result_note": (
        "Calculate a mission in Mission before reviewing its scientific budget."
    ),
    "budget_candidate_mass_unavailable": (
        "A simplified mass estimate is not stored in the applied launch-window candidate. "
        "This page does not recalculate it silently."
    ),
    "budget_c3_unavailable": (
        "Earth C3 is not presented for this historical non-Lambert reference scenario."
    ),
    "budget_non_saturn_scope": (
        "This destination currently provides the existing direct-arrival budget only. "
        "Saturn capture and Saturn-centered circularization do not apply."
    ),
    "budget_historical_scope": (
        "This historical reference keeps its own Earth-departure and Saturn Orbit "
        "Insertion budget. It is not the direct baseline architecture."
    ),
    "budget_included": "Included in connected total",
    "budget_not_applicable": "Not applicable to this scenario",
    "budget_dry_mass": "Simplified dry mass",
    "budget_propellant_mass": "Simplified propellant mass",
    "budget_wet_mass": "Simplified wet mass",
    "budget_continue": "Continue to Verdict",
    "verdict_title": "Verdict",
    "verdict_introduction": (
        "This conclusion applies only to the calculated scenario and the scope of the "
        "current model."
    ),
    "verdict_conclusion_heading": "Model conclusion",
    "verdict_final_state_heading": "Calculated final state",
    "verdict_final_state": (
        "The model reaches a Saturn-centered circular orbit at Titan's mean orbital radius."
    ),
    "verdict_titan_exclusion": "This result does not demonstrate a Titan encounter.",
    "verdict_allocation_limitation": (
        "The current model does not determine how Earth injection or the other maneuvers "
        "are allocated among a launcher, upper stage, and spacecraft."
    ),
    "verdict_demonstrated_heading": "What the model calculates",
    "verdict_excluded_heading": "What the model does not demonstrate",
    "verdict_limits_heading": "Model assumptions and limitations",
    "verdict_details": "Open technical details",
    "verdict_previous_result_note": (
        "Inputs have changed. This conclusion describes the previous calculation, not "
        "the current draft inputs."
    ),
    "verdict_no_result_note": (
        "Calculate a mission in Mission before reviewing a model conclusion."
    ),
    "verdict_historical_conclusion": (
        "The active scenario is the Cassini VVEJGA historical reference. Its dates, "
        "budget, and terminal state remain specific to that historical model."
    ),
    "verdict_historical_final_state": (
        "The historical reference ends in Cassini's modeled post-Saturn-Orbit-Insertion "
        "state. It does not automatically reach the direct baseline's final orbit."
    ),
    "verdict_non_saturn_conclusion": (
        "The calculated scenario describes a direct planetary-arrival result within "
        "the scope and assumptions currently available for this destination."
    ),
    "verdict_non_saturn_final_state": (
        "The model ends at the selected planet's direct-arrival state. No Saturn or "
        "Titan endpoint is implied."
    ),
    "verdict_calculates_departure": "Earth departure conditions from the active result",
    "verdict_calculates_dates": "Trajectory dates and time of flight",
    "verdict_calculates_injection": "Modeled Earth injection",
    "verdict_calculates_saturn": (
        "Saturn capture and Saturn-centered circularization for the direct baseline"
    ),
    "verdict_calculates_total": "The complete connected total",
    "verdict_calculates_final_state": (
        "A Saturn-centered circular orbit at Titan's mean orbital radius"
    ),
    "verdict_calculates_mass": "The existing simplified mass estimate",
    "verdict_not_launcher": "Compatibility with a real launch vehicle",
    "verdict_not_allocation": (
        "Definitive allocation among a launcher, upper stage, and spacecraft"
    ),
    "verdict_not_titan_encounter": "A Titan encounter or flyby",
    "verdict_not_titan_capture": "Titan capture or a Titan-centered orbit",
    "verdict_not_gravity_assist": "A connected gravity-assist trajectory",
    "verdict_not_propagation": "Independent dynamical propagation of the 3D playback",
    "verdict_not_vehicle_design": "A complete vehicle design",
    "verdict_assumption_dynamics": (
        "The connected baseline uses the existing deterministic first-order, impulsive, "
        "coplanar model and its documented constants."
    ),
    "verdict_assumption_endpoint": (
        "Titan's mean orbital radius is a Saturn-centered radial reference only."
    ),
    "verdict_assumption_isolated": (
        "Gravity-assist demonstrators and legacy studies are excluded from the active "
        "connected total."
    ),
    "verdict_open_isolated": "Open isolated studies",
    "verdict_return_mission": "Edit mission",
    "error_input_summary": "Correct the highlighted inputs before calculating.",
    "error_no_solution": (
        "The inputs are valid, but the model did not produce a solution for this scenario."
    ),
    "error_technical": (
        "The calculation could not be completed because of a technical error. Previous "
        "results were not replaced."
    ),
    "error_stale_results": (
        "Inputs have changed. The displayed results are from the previous calculation."
    ),
}


UI_V030_TOOLTIPS: Final[dict[str, str]] = {
    "badge_connected": (
        '"Connected" means Earth injection, Saturn capture, and Saturn-centered '
        "circularization are summed into one reproducible total for the active "
        "scenario - as opposed to an isolated study, which is not summed into that "
        "total."
    ),
    "earth_c3": (
        "Characteristic energy of Earth departure. For a hyperbolic departure, C3 is the "
        "square of the hyperbolic excess speed. It is not a delta-v."
    ),
    "earth_v_infinity": (
        "Hyperbolic excess speed relative to Earth. It characterizes the departure state "
        "but is not itself a propulsive maneuver."
    ),
    "modeled_earth_injection": (
        "Earth injection delta-v calculated by the model. Its allocation to a launcher, "
        "upper stage, or spacecraft depends on the selected architecture."
    ),
    "saturn_arrival_v_infinity": (
        "Hyperbolic excess speed relative to Saturn before the capture maneuver."
    ),
    "saturn_capture": (
        "Modeled propulsive maneuver from hyperbolic Saturn arrival into the "
        "Saturn-centered capture orbit."
    ),
    "saturn_circularization": (
        "Modeled propulsive maneuver into a circular Saturn-centered orbit at Titan's mean "
        "orbital radius. It is not a Titan encounter."
    ),
    "saturn_subtotal": (
        "Sum of Saturn capture and Saturn-centered circularization. It excludes modeled "
        "Earth injection."
    ),
    "connected_total": (
        "Sum of modeled Earth injection, Saturn capture, and Saturn-centered circularization."
    ),
    "saturn_periapsis_radius": (
        "Minimum distance from Saturn's center on the relevant trajectory. It is a radius, "
        "not an altitude."
    ),
    "periapsis_altitude": (
        "Distance above the reference surface. It differs from a radius measured from the "
        "body's center."
    ),
    "final_saturn_orbital_radius": (
        "Distance from Saturn's center to the modeled final circular orbit."
    ),
    "titan_mean_orbital_radius": (
        "Radial reference used for the final Saturn-centered orbit. It does not imply an "
        "encounter with Titan."
    ),
    "simplified_wet_mass": (
        "Wet mass estimated by the simplified model, including propellant. It is not a "
        "complete vehicle design."
    ),
    "pareto_front": (
        "Set of scenarios that are non-dominated for the displayed objectives. No point is "
        "universally optimal without an additional preference."
    ),
    "heliocentric_speed_gain": (
        "Change in heliocentric speed during an isolated flyby. It is not directly a "
        "propulsive delta-v saving."
    ),
    "mjd2000_epoch": (
        "Technical epoch representation used by the calculations. Civil UTC dates remain "
        "the primary display."
    ),
}


UI_SYMBOLS: Final[dict[str, str]] = {
    "c3": "C3",
    "v_infinity": "v∞",
    "delta_v": "Δv",
    "utc": "UTC",
    "mjd2000": "MJD2000",
}


UI_UNITS: Final[dict[str, str]] = {
    "metres_per_second": "m/s",
    "kilometres_per_second": "km/s",
    "square_kilometres_per_square_second": "km²/s²",
    "kilometres": "km",
    "days": "days",
    "kilograms": "kg",
}
