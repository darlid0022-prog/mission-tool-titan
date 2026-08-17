"""Mission capabilities currently exposed by the application."""

from .bodies import SUPPORTED_BODIES

# Every Lambert-capable planet registered in bodies.py, excluding Earth (the
# fixed mission origin). A planet destination is a direct, single-leg
# arrival: no staging or capture maneuver is modeled yet for a bare
# planetary arrival - see compute_earth_destination_mission in full_mission.py.
PLANET_DESTINATIONS = tuple(
    body.name
    for body in SUPPORTED_BODIES.values()
    if body.supports_lambert and body.name != "Earth"
)

# Moons reachable through the two-extra-leg chain (hyperbolic arrival-to-
# staging, then a parent-to-moon Hohmann transfer) that Titan already uses -
# see mission/arrival_staging.py and mission/parent_moon_transfer.py, the
# generic engines mission/full_mission.py's compute_earth_destination_mission
# is built on. Keyed by moon name -> its Lambert-capable parent planet, so a
# moon can only be offered once its parent planet is the selected destination.
MOON_DESTINATIONS = {
    "Titan": "Saturn",
}

PLANNED_DESTINATIONS = (
    "Phobos",
    "Deimos",
    "Ceres",
    "Io",
    "Europa",
    "Ganymede",
    "Callisto",
    "Pluto",
)

PLANNED_MISSION_FEATURES = (
    "High-fidelity Saturn to Titan trajectory",
    "Flyby and deep-space manoeuvres",
    "High-fidelity Titan EDL and landing dynamics",
    "Final-orbit lowering",
)
