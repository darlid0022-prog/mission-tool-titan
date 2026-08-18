# Consolidated first-order Earth–Saturn–Titan-orbit model

## Scope

This deterministic analytical chain replaces the former connected-budget
sequence that circularised at 600,000 km, departed again for Titan, and then
claimed a Titan-centred circular capture. The endpoint is instead a
**Saturn-centred circular orbit at Titan's mean orbital radius**. It is not a
phased Titan encounter and contains no Titan capture manoeuvre.

All internal quantities use SI units. Display-layer distances may be converted
to kilometres. Every Saturn and Titan-system radius is measured from Saturn's
centre unless explicitly described as an altitude.

## Sources and constants

- Astronomical unit: `149,597,870,700 m` exactly, IAU 2012 Resolution B2.
- Solar GM: `1.32712440041279419e20 m³/s²`, JPL DE440 astrodynamic parameters.
- Earth circular reference radius: `1 au` (first-order design convention).
- Saturn J2000 semimajor axis: `9.53667594 au`, JPL approximate planetary
  elements for 1800–2050.
- Saturn GM: `3.793120623e16 m³/s²`, JPL SAT441.
- Saturn equatorial radius: `60,268 km`, JPL planetary physical parameters.
- Titan mean orbital radius: `1,221,870 km`, required design convention.
- Reference F-ring radius: approximately `140,180 km`, NASA Cassini mission
  reference geometry.
- Nominal capture periapsis: `150,000 km`, a design choice outside the reference
  F-ring radius, not an operational ring-clearance certification.

Primary references:

- <https://ssd.jpl.nasa.gov/astro_par.html>
- <https://ssd.jpl.nasa.gov/planets/approx_pos.html>
- <https://ssd.jpl.nasa.gov/planets/phys_par.html>
- <https://ssd.jpl.nasa.gov/sats/phys_par/sep.html>
- <https://science.nasa.gov/wp-content/uploads/2023/09/cassini.pdf>

## Analytical architecture

1. An interplanetary leg supplies Earth-departure and Saturn-arrival
   hyperbolic-excess velocities. Mission setup and Launch windows use their
   dated Lambert leg; the deterministic reference calculation uses a circular,
   coplanar heliocentric Hohmann transfer.
2. The supplied Saturn-relative hyperbolic arrival state feeds the common
   capture function without substitution by another transfer model.
3. Tangential impulsive burn at `150,000 km` into a Saturn-centred ellipse with
   apoapsis `1,221,870 km`.
4. Tangential impulsive circularisation at apoapsis.

The hyperbola uses:

```text
epsilon_h = v_inf² / 2
a_h = -mu_saturn / v_inf²
e_h = 1 + r_p v_inf² / mu_saturn
v_p,h = sqrt(v_inf² + 2 mu_saturn / r_p)
delta = 2 asin(1 / e_h)
```

The captured ellipse uses vis-viva at the same burn points. Each delta-v is
the scalar speed difference at one common radius; no velocities from different
points are subtracted.

## Nominal deterministic Hohmann-reference values

| Quantity | Value |
| --- | ---: |
| Hohmann departure v-infinity | 10,288.580691 m/s |
| Saturn arrival v-infinity | 5,442.813670 m/s |
| Hohmann flight time | 2,208.405768 d |
| Hyperbolic specific energy | +14,812,110.321839 J/kg |
| Hyperbolic semimajor axis | -1,280,411.953659 km |
| Hyperbolic eccentricity | 1.117149797 |
| Hyperbolic periapsis speed | 23,138.142472 m/s |
| Deflection angle | 127.051578° |
| Ellipse specific energy | -27,649,271.600079 J/kg |
| Ellipse semimajor axis | 685,935.000 km |
| Ellipse eccentricity | 0.781320388 |
| Ellipse periapsis speed | 21,223.827958 m/s |
| Ellipse apoapsis speed | 2,605.493378 m/s |
| Circular speed at apoapsis | 5,571.675643 m/s |
| Capture impulse | 1,914.314514 m/s |
| Circularisation impulse | 2,966.182265 m/s |
| Saturn phase total | 4,880.496779 m/s |
| Periapsis-to-apoapsis time | 3.353994 d |

## Validation and limitations

The solver rejects non-finite/non-numeric SI inputs, non-positive GM or radii,
a periapsis at or below Saturn's equatorial radius, a periapsis at or inside the
reference F-ring radius, and an apoapsis at or below periapsis. These scalar
guards do not establish three-dimensional clearance from ring material.

The standalone Hohmann reference excludes launch-window phasing and real
planetary eccentricity and inclination. The application and launch-window
engine instead supply their Lambert states to the same Saturn equations.
All modes exclude gravity assists, Saturn oblateness, finite burns,
ring-plane crossing geometry, perturbations, navigation corrections, Titan
encounter phasing, and Titan-centred capture. Consequently this is an energy
model for preliminary comparison, not a flyable mission trajectory.
