"""Central English copy for the Streamlit interface."""

from typing import Final

UI_TEXT: Final[dict[str, str]] = {
    "app_caption": (
        "Current scope: Earth → Saturn transfer and a separate preliminary "
        "Saturn → Titan leg study."
    ),
    "architecture_header": "1. Mission architecture",
    "destination_label": "Computable destination",
    "destination_help": "Only Saturn is currently connected to the trajectory engine.",
    "departure_type": "Departure type",
    "leo_altitude": "Initial LEO altitude (km)",
    "leo_help": "Used only when the departure type is LEO.",
    "saturn_capture_altitude": "Saturn capture altitude (km)",
    "launch_window_header": "2. Launch window",
    "launch_start": "Launch date — start",
    "launch_end": "Launch date — end",
    "calculate": "Calculate trajectory",
    "titan_scope": (
        "Titan is not yet available as an end-to-end mission destination. "
        "A separate preliminary Saturn → Titan study is available below."
    ),
    "planned_capabilities": "Planned capabilities",
    "planned_destinations": "Destinations: ",
    "propulsion_header": "3. Propulsion",
    "isp": "Main engine specific impulse (s)",
    "instruments_header": "4. Instruments",
    "instruments_caption": "Add or edit rows directly in the table below.",
    "invalid_dates": "The end date must be on or after the start date.",
    "earth_saturn_spinner": "Calculating the Earth → Saturn trajectory…",
    "results_header": "Results (updated after calculation)",
    "provisional_budget": "Preliminary delta-v budget",
    "budget_caption": (
        "The displayed values include the computed propulsive delta-v for LEO escape "
        "(when LEO is selected) and Saturn capture. Other entries remain preliminary."
    ),
    "maneuver": "Maneuver",
    "value_m_s": "Value (m/s)",
    "dv_sum": "Sum of budgeted delta-v values",
    "mass_budget": "Mass budget",
    "direct_warning": (
        "Direct mode still treats departure v∞ as a preliminary equivalent delta-v. "
        "The mass budget is not a launch-vehicle sizing result."
    ),
    "instrument_mass": "Instrument mass",
    "dry_mass": "Dry mass",
    "propellant_mass": "Propellant mass",
    "wet_mass": "Total wet mass",
    "titan_header": "Saturn → Titan — preliminary model",
    "titan_warning": (
        "Partial budget: the phase between Saturn arrival/capture and the Saturn "
        "staging orbit is not included here. The values below are not added to the "
        "global budget or mass sizing."
    ),
    "study_parameters": "Study parameters",
    "staging_radius": "Saturn staging-orbit radius (km)",
    "staging_radius_help": (
        "Radius measured from Saturn's center. The lower bound is beyond the "
        "preliminary ring guard."
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
    "partial_total_dv": "Total modeled delta-v (partial)",
    "titan_tof": "Saturn → Titan time of flight",
    "assumptions_exclusions": "Model assumptions and exclusions",
    "assumptions": "**Assumptions**",
    "exclusions": "**Exclusions**",
}
