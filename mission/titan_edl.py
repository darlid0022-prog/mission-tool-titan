"""Pure preliminary ballistic entry model for Titan."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .constants import TITAN_MEAN_RADIUS_M, TITAN_MU_M3_S2

# Huygens atmospheric interface and entry geometry reported by ESA.
# https://www.esa.int/Science_Exploration/Space_Science/Cassini-Huygens/Huygens_descent_timeline
# https://www.esa.int/Enabling_Support/Operations/Animation_Cassini_s_view_of_Titan
DEFAULT_ENTRY_INTERFACE_ALTITUDE_M = 1_270_000.0
DEFAULT_ENTRY_FLIGHT_PATH_ANGLE_DEG = 65.0

# Huygens-equivalent ballistic coefficient from NASA/TM-20220014544.
# https://ntrs.nasa.gov/api/citations/20220014544/downloads/NASA-TM-20220014544.pdf
DEFAULT_BALLISTIC_COEFFICIENT_KG_M2 = 38.0

# Simplified Titan lower-atmosphere values from NASA/TM-20220016292.
# https://ntrs.nasa.gov/api/citations/20220016292/downloads/TM-20220016292.pdf
DEFAULT_SURFACE_DENSITY_KG_M3 = 5.43
DEFAULT_DENSITY_SCALE_HEIGHT_M = 22_000.0

# Huygens reached approximately Mach 1.5 / 400 m/s before parachute deployment.
# https://archives.esac.esa.int/psa/ftp/CASSINI-HUYGENS/HUYGENS_HK/
# HP-SSA-HK-2-3-V1.0/DOCUMENT/PUBLICATIONS/HUYGENS_OVERVIEW_NATURE2005.PDF
DEFAULT_PARACHUTE_DEPLOYMENT_SPEED_M_S = 400.0
METHOD = "ballistic_direct_entry_exponential_atmosphere"

SOURCES = (
    "[ESA Huygens descent timeline](https://www.esa.int/Science_Exploration/Space_Science/"
    "Cassini-Huygens/Huygens_descent_timeline) — 1,270 km atmospheric interface",
    "[ESA Huygens entry geometry](https://www.esa.int/Enabling_Support/Operations/"
    "Animation_Cassini_s_view_of_Titan) — approximately 65 degrees and 6 km/s",
    "[NASA/TM-20220014544](https://ntrs.nasa.gov/api/citations/20220014544/downloads/"
    "NASA-TM-20220014544.pdf) — Huygens ballistic coefficient of 38 kg/m²",
    "[NASA/TM-20220016292](https://ntrs.nasa.gov/api/citations/20220016292/downloads/"
    "TM-20220016292.pdf) — 5.43 kg/m³ surface density and 22 km scale height",
    "[Huygens mission overview](https://archives.esac.esa.int/psa/ftp/CASSINI-HUYGENS/"
    "HUYGENS_HK/HP-SSA-HK-2-3-V1.0/DOCUMENT/PUBLICATIONS/"
    "HUYGENS_OVERVIEW_NATURE2005.PDF) — approximately 400 m/s deployment speed",
)


@dataclass(frozen=True)
class TitanEdlResult:
    """Typed output of the isolated direct ballistic-entry study."""

    origin_state: str
    destination_state: str
    method: str
    incoming_v_infinity_m_s: float
    entry_interface_altitude_m: float
    entry_interface_radius_m: float
    entry_velocity_m_s: float
    ballistic_coefficient_kg_m2: float
    entry_flight_path_angle_deg: float
    surface_density_kg_m3: float
    density_scale_height_m: float
    parachute_deployment_speed_m_s: float
    estimated_parachute_deployment_altitude_m: float
    atmospheric_velocity_reduction_m_s: float
    reference_circular_capture_delta_v_m_s: float
    propulsive_equivalent_savings_m_s: float
    assumptions: tuple[str, ...]
    exclusions: tuple[str, ...]
    sources: tuple[str, ...]


def _require_finite_number(name: str, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise TypeError(f"{name} must be a real number in SI units.")
    converted = float(value)
    if not math.isfinite(converted):
        raise ValueError(f"{name} must be finite.")
    return converted


def ballistic_speed_at_altitude(
    entry_velocity_m_s: float,
    altitude_m: float,
    *,
    entry_interface_altitude_m: float = DEFAULT_ENTRY_INTERFACE_ALTITUDE_M,
    ballistic_coefficient_kg_m2: float = DEFAULT_BALLISTIC_COEFFICIENT_KG_M2,
    entry_flight_path_angle_deg: float = DEFAULT_ENTRY_FLIGHT_PATH_ANGLE_DEG,
    surface_density_kg_m3: float = DEFAULT_SURFACE_DENSITY_KG_M3,
    density_scale_height_m: float = DEFAULT_DENSITY_SCALE_HEIGHT_M,
) -> float:
    """Return drag-only speed along a constant-angle exponential-atmosphere path."""
    entry_speed = _require_finite_number("entry_velocity_m_s", entry_velocity_m_s)
    altitude = _require_finite_number("altitude_m", altitude_m)
    interface_altitude = _require_finite_number(
        "entry_interface_altitude_m", entry_interface_altitude_m
    )
    beta = _require_finite_number("ballistic_coefficient_kg_m2", ballistic_coefficient_kg_m2)
    angle_deg = _require_finite_number("entry_flight_path_angle_deg", entry_flight_path_angle_deg)
    surface_density = _require_finite_number("surface_density_kg_m3", surface_density_kg_m3)
    scale_height = _require_finite_number("density_scale_height_m", density_scale_height_m)

    if entry_speed <= 0.0:
        raise ValueError("entry_velocity_m_s must be positive.")
    if interface_altitude <= 0.0 or altitude < 0.0 or altitude > interface_altitude:
        raise ValueError("altitude_m must be between zero and the entry-interface altitude.")
    if beta <= 0.0 or surface_density <= 0.0 or scale_height <= 0.0:
        raise ValueError("Atmosphere and ballistic parameters must be positive.")
    if angle_deg <= 0.0 or angle_deg >= 90.0:
        raise ValueError("entry_flight_path_angle_deg must be between 0 and 90 degrees.")

    sin_gamma = math.sin(math.radians(angle_deg))
    density_column = (
        surface_density
        * scale_height
        * (math.exp(-altitude / scale_height) - math.exp(-interface_altitude / scale_height))
    )
    return entry_speed * math.exp(-density_column / (2.0 * beta * sin_gamma))


def estimate_ballistic_deployment_altitude(
    entry_velocity_m_s: float,
    deployment_speed_m_s: float = DEFAULT_PARACHUTE_DEPLOYMENT_SPEED_M_S,
    *,
    entry_interface_altitude_m: float = DEFAULT_ENTRY_INTERFACE_ALTITUDE_M,
    ballistic_coefficient_kg_m2: float = DEFAULT_BALLISTIC_COEFFICIENT_KG_M2,
    entry_flight_path_angle_deg: float = DEFAULT_ENTRY_FLIGHT_PATH_ANGLE_DEG,
    surface_density_kg_m3: float = DEFAULT_SURFACE_DENSITY_KG_M3,
    density_scale_height_m: float = DEFAULT_DENSITY_SCALE_HEIGHT_M,
) -> float:
    """Solve the analytic drag model for the altitude of a requested speed."""
    entry_speed = _require_finite_number("entry_velocity_m_s", entry_velocity_m_s)
    deployment_speed = _require_finite_number("deployment_speed_m_s", deployment_speed_m_s)
    interface_altitude = _require_finite_number(
        "entry_interface_altitude_m", entry_interface_altitude_m
    )
    beta = _require_finite_number("ballistic_coefficient_kg_m2", ballistic_coefficient_kg_m2)
    angle_deg = _require_finite_number("entry_flight_path_angle_deg", entry_flight_path_angle_deg)
    surface_density = _require_finite_number("surface_density_kg_m3", surface_density_kg_m3)
    scale_height = _require_finite_number("density_scale_height_m", density_scale_height_m)

    if entry_speed <= 0.0 or deployment_speed <= 0.0:
        raise ValueError("Entry and deployment speeds must be positive.")
    if deployment_speed >= entry_speed:
        raise ValueError("deployment_speed_m_s must be less than entry_velocity_m_s.")
    if interface_altitude <= 0.0 or beta <= 0.0 or surface_density <= 0.0 or scale_height <= 0.0:
        raise ValueError("Atmosphere and ballistic parameters must be positive.")
    if angle_deg <= 0.0 or angle_deg >= 90.0:
        raise ValueError("entry_flight_path_angle_deg must be between 0 and 90 degrees.")

    sin_gamma = math.sin(math.radians(angle_deg))
    exponential_density_ratio = math.exp(-interface_altitude / scale_height) + (
        2.0
        * beta
        * sin_gamma
        * math.log(entry_speed / deployment_speed)
        / (surface_density * scale_height)
    )
    if exponential_density_ratio > 1.0:
        raise ValueError("The requested deployment speed is not reached above Titan's surface.")
    return -scale_height * math.log(exponential_density_ratio)


def compute_titan_edl(
    incoming_v_infinity_m_s: float,
    reference_circular_capture_delta_v_m_s: float,
    *,
    entry_interface_altitude_m: float = DEFAULT_ENTRY_INTERFACE_ALTITUDE_M,
    ballistic_coefficient_kg_m2: float = DEFAULT_BALLISTIC_COEFFICIENT_KG_M2,
    entry_flight_path_angle_deg: float = DEFAULT_ENTRY_FLIGHT_PATH_ANGLE_DEG,
    surface_density_kg_m3: float = DEFAULT_SURFACE_DENSITY_KG_M3,
    density_scale_height_m: float = DEFAULT_DENSITY_SCALE_HEIGHT_M,
    parachute_deployment_speed_m_s: float = DEFAULT_PARACHUTE_DEPLOYMENT_SPEED_M_S,
) -> TitanEdlResult:
    """Compute an isolated direct-entry alternative without changing mission budgets."""
    v_infinity = _require_finite_number("incoming_v_infinity_m_s", incoming_v_infinity_m_s)
    reference_capture = _require_finite_number(
        "reference_circular_capture_delta_v_m_s",
        reference_circular_capture_delta_v_m_s,
    )
    interface_altitude = _require_finite_number(
        "entry_interface_altitude_m", entry_interface_altitude_m
    )

    if v_infinity < 0.0:
        raise ValueError("incoming_v_infinity_m_s must be non-negative.")
    if reference_capture < 0.0:
        raise ValueError("reference_circular_capture_delta_v_m_s must be non-negative.")
    if interface_altitude <= 0.0:
        raise ValueError("entry_interface_altitude_m must be positive.")

    interface_radius = TITAN_MEAN_RADIUS_M + interface_altitude
    entry_velocity = math.sqrt(v_infinity**2 + 2.0 * TITAN_MU_M3_S2 / interface_radius)
    deployment_altitude = estimate_ballistic_deployment_altitude(
        entry_velocity,
        parachute_deployment_speed_m_s,
        entry_interface_altitude_m=interface_altitude,
        ballistic_coefficient_kg_m2=ballistic_coefficient_kg_m2,
        entry_flight_path_angle_deg=entry_flight_path_angle_deg,
        surface_density_kg_m3=surface_density_kg_m3,
        density_scale_height_m=density_scale_height_m,
    )
    deployment_speed = float(parachute_deployment_speed_m_s)

    return TitanEdlResult(
        origin_state="Titan-relative hyperbolic approach",
        destination_state="Pre-parachute atmospheric descent",
        method=METHOD,
        incoming_v_infinity_m_s=v_infinity,
        entry_interface_altitude_m=interface_altitude,
        entry_interface_radius_m=interface_radius,
        entry_velocity_m_s=entry_velocity,
        ballistic_coefficient_kg_m2=float(ballistic_coefficient_kg_m2),
        entry_flight_path_angle_deg=float(entry_flight_path_angle_deg),
        surface_density_kg_m3=float(surface_density_kg_m3),
        density_scale_height_m=float(density_scale_height_m),
        parachute_deployment_speed_m_s=deployment_speed,
        estimated_parachute_deployment_altitude_m=deployment_altitude,
        atmospheric_velocity_reduction_m_s=entry_velocity - deployment_speed,
        reference_circular_capture_delta_v_m_s=reference_capture,
        propulsive_equivalent_savings_m_s=reference_capture,
        assumptions=(
            "Direct ballistic entry begins on the incoming Titan-relative hyperbola.",
            "Titan gravity is treated as spherical from infinity to the atmospheric interface.",
            "The drag phase is lift-free with constant flight-path angle "
            "and ballistic coefficient.",
            "Gravity, curvature, winds, and flight-path evolution are neglected during drag.",
            "Density follows one exponential profile anchored at Titan's surface.",
            "Atmospheric drag reduces speed to 400 m/s without a propulsive capture burn.",
        ),
        exclusions=(
            "Heat-shield material, thickness, ablation, and thermal margins.",
            "Entry-corridor width, navigation dispersions, winds, and three-dimensional targeting.",
            "Peak g-load qualification and vehicle attitude or six-degree-of-freedom dynamics.",
            "Parachute inflation, deployment loads, reefing, and descent dynamics.",
            "Landing-site targeting, terminal descent, and touchdown systems.",
        ),
        sources=SOURCES,
    )
