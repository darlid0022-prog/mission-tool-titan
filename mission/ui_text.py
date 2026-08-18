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
