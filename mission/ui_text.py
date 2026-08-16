"""Central English copy for the Streamlit interface."""

from typing import Final

UI_TEXT: Final[dict[str, str]] = {
    "app_caption": (
        "Connected preliminary Earth → Saturn → Titan mission chain with an explicit "
        "propulsive delta-v and mass budget."
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
    "instruments_caption": "Add or edit rows directly in the table below.",
    "invalid_dates": "The end date must be on or after the start date.",
    "earth_saturn_spinner": "Calculating the Earth → Saturn trajectory…",
    "results_header": "Results (updated after calculation)",
    "complete_chain_note": (
        "Connected preliminary Earth → Saturn → Titan budget. The legacy circular "
        "Saturn-capture term is replaced by capture-to-ellipse and staging circularization."
    ),
    "provisional_budget": "Preliminary delta-v budget",
    "budget_caption": (
        "The displayed values include every currently modeled propulsive burn. DSM / "
        "fly-by corrections remain zero because no such maneuver is modeled yet."
    ),
    "maneuver": "Maneuver",
    "value_m_s": "Value (m/s)",
    "dv_sum": "Sum of budgeted delta-v values",
    "mass_budget": "Mass budget",
    "mass_model_warning": (
        "Preliminary sizing: dry mass currently scales from the instrument table and does not "
        "yet represent a complete spacecraft bus."
    ),
    "direct_warning": (
        "Direct mode still treats departure v∞ as a preliminary equivalent delta-v. "
        "The mass budget is not a launch-vehicle sizing result."
    ),
    "instrument_mass": "Instrument mass",
    "dry_mass": "Dry mass",
    "propellant_mass": "Propellant mass",
    "wet_mass": "Total wet mass",
    "trajectory_3d_header": "Complete mission trajectory — interactive 3D view",
    "trajectory_3d_caption": (
        "Drag to rotate, scroll to zoom, and double-click to reset. The heliocentric and "
        "Saturn-centred panels use different reference frames and scales. Body sizes are not "
        "shown to scale."
    ),
    "mission_elapsed_time": "Mission elapsed time",
    "mission_elapsed_time_help": (
        "Moves the spacecraft marker along pre-sampled trajectory points without rerunning "
        "the orbital solver."
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
    "assumptions_exclusions": "Model assumptions and exclusions",
    "assumptions": "**Assumptions**",
    "exclusions": "**Exclusions**",
}
