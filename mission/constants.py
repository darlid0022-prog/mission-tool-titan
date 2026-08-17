"""Authoritative physical constants used by mission-domain calculations."""

# Standard acceleration of gravity used by the Tsiolkovsky equation.
G0_M_S2 = 9.80665

# JPL SAT441 values converted from km-based units to SI.
# https://ssd.jpl.nasa.gov/sats/phys_par/sep.html
SATURN_MU_M3_S2 = 3.793120623e16
TITAN_MU_M3_S2 = 8.97813710e12
TITAN_MEAN_RADIUS_M = 2.57476e6

# JPL SAT441 mean elements.
# https://ssd.jpl.nasa.gov/sats/elem/sep.html
TITAN_MEAN_ORBIT_RADIUS_M = 1.2219e9
TITAN_MEAN_ECCENTRICITY = 0.029
TITAN_MEAN_INCLINATION_RAD = 0.005235987755982988
TITAN_SIDEREAL_PERIOD_S = 1_377_686.7072

JPL_SATURN_SYSTEM_SOURCE = "JPL SAT441"

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
