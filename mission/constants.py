"""Authoritative physical constants used by mission-domain calculations."""

# Standard acceleration of gravity used by the Tsiolkovsky equation.
G0_M_S2 = 9.80665

# IAU 2012 Resolution B2: the astronomical unit is exact.
ASTRONOMICAL_UNIT_M = 149_597_870_700.0

# JPL DE440 astrodynamic parameters (SI).
# https://ssd.jpl.nasa.gov/astro_par.html
SUN_MU_M3_S2 = 1.32712440041279419e20

# Circular-orbit radii used by the first-order heliocentric Hohmann model.
# Earth is represented at exactly 1 au. Saturn's J2000 semimajor axis is from
# JPL's 1800--2050 approximate planetary elements.
# https://ssd.jpl.nasa.gov/planets/approx_pos.html
EARTH_MEAN_ORBIT_RADIUS_M = ASTRONOMICAL_UNIT_M
SATURN_MEAN_ORBIT_RADIUS_M = 9.53667594 * ASTRONOMICAL_UNIT_M

# JPL planetary physical parameters.
# https://ssd.jpl.nasa.gov/planets/phys_par.html
SATURN_EQUATORIAL_RADIUS_M = 60_268_000.0

# JPL SAT441 values converted from km-based units to SI.
# https://ssd.jpl.nasa.gov/sats/phys_par/sep.html
SATURN_MU_M3_S2 = 3.793120623e16
TITAN_MU_M3_S2 = 8.97813710e12
TITAN_MEAN_RADIUS_M = 2.57476e6

# JPL SAT441 mean elements.
# https://ssd.jpl.nasa.gov/sats/elem/sep.html
# Required first-order design convention. This intentionally differs by 30 km
# from the rounded SAT441 table value retained in older project documents.
TITAN_MEAN_ORBIT_RADIUS_M = 1_221_870_000.0
TITAN_MEAN_ECCENTRICITY = 0.029
TITAN_MEAN_INCLINATION_RAD = 0.005235987755982988
TITAN_SIDEREAL_PERIOD_S = 1_377_686.7072

JPL_SATURN_SYSTEM_SOURCE = "JPL SAT441"
JPL_DE440_SOURCE = "JPL DE440 / approximate J2000 planetary elements"

# Saturn-centred design geometry, all measured from Saturn's centre.
F_RING_REFERENCE_RADIUS_M = 140_180_000.0
NOMINAL_SATURN_PERIAPSIS_RADIUS_M = 150_000_000.0

# JPL "Planetary Satellite Physical Parameters" (MAR097 / JUP365).
# https://ssd.jpl.nasa.gov/sats/phys_par/
# Same authoritative source family as the Saturn/Titan constants above; GM
# values converted from km^3/s^2 to SI, radii converted from km to m.
JPL_MARS_SYSTEM_SOURCE = "JPL MAR097"
JPL_JUPITER_SYSTEM_SOURCE = "JPL JUP365"

PHOBOS_MU_M3_S2 = 7.087e5
PHOBOS_MEAN_RADIUS_M = 1.108e4

DEIMOS_MU_M3_S2 = 9.62e4
DEIMOS_MEAN_RADIUS_M = 6.2e3

IO_MU_M3_S2 = 5.95991547e12
IO_MEAN_RADIUS_M = 1.82149e6

EUROPA_MU_M3_S2 = 3.20271210e12
EUROPA_MEAN_RADIUS_M = 1.5608e6

GANYMEDE_MU_M3_S2 = 9.88783275e12
GANYMEDE_MEAN_RADIUS_M = 2.6312e6

CALLISTO_MU_M3_S2 = 7.17928340e12
CALLISTO_MEAN_RADIUS_M = 2.4103e6

# ---------------------------------------------------------------------------
# Ceres and Pluto
#
# Preferred GM (mu) values are taken from the JPL Small-Body Database when
# available (published GM values are preferred to G * mass approximations).
# Ceres: JPL Small-Body DB reports GM ≈ 6.26e10 m^3/s^2 (used below).
# Note: the project Excel source (mission_design_tool.xlsx) listed Ceres
# perihelion and aphelion values reversed; the correct ordering is
# perihelion ≈ 3.81e11 m, aphelion ≈ 4.46e11 m (documented in reference
# comments but not stored as constants here).
# Pluto: JPL value used where available (GM ≈ 8.70e11 m^3/s^2).
# ---------------------------------------------------------------------------

CERES_MU_M3_S2 = 6.26e10
CERES_MEAN_RADIUS_M = 469700.0

PLUTO_MU_M3_S2 = 8.70e11
PLUTO_MEAN_RADIUS_M = 1188300.0
