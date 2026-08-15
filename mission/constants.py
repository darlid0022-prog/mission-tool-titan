"""Authoritative physical constants used by mission-domain calculations."""

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
