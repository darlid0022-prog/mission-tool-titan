# Preliminary Saturn-to-Titan transfer model

Status: specification only — no production implementation yet.

## 1. Purpose

Define a transparent first-order model for a Saturn-centred transfer from a
circular staging orbit to a circular capture orbit around Titan.

This model is intended for early trade studies and software architecture. It is
not a navigation-quality trajectory and must not be presented as one.

## 2. Authoritative constants

The source of truth is JPL Solar System Dynamics, ephemeris SAT441.

| Quantity | Symbol | Source value | Internal SI value |
| --- | --- | ---: | ---: |
| Saturn gravitational parameter | `mu_saturn` | 37,931,206.23 km³/s² | 3.793120623e16 m³/s² |
| Titan gravitational parameter | `mu_titan` | 8,978.13710 km³/s² | 8.97813710e12 m³/s² |
| Titan mean radius | `radius_titan` | 2,574.76 km | 2.57476e6 m |
| Titan mean semimajor axis | `orbit_radius_titan` | 1,221,900 km | 1.2219e9 m |
| Titan mean eccentricity | `eccentricity_titan` | 0.029 | dimensionless |
| Titan mean inclination | `inclination_titan` | 0.3° | 0.00523599 rad |
| Titan sidereal period | `period_titan` | 15.945448 days | 1,377,686.7072 s |

Primary sources:

- JPL satellite physical parameters:
  <https://ssd.jpl.nasa.gov/sats/phys_par/sep.html>
- JPL Saturn satellite mean elements:
  <https://ssd.jpl.nasa.gov/sats/elem/sep.html>

JPL warns that mean elements are approximate and should not be used for
high-fidelity work. A future high-fidelity implementation must use Horizons or a
SAT441/SPICE ephemeris instead:
<https://ssd.jpl.nasa.gov/sats/orbits.html>

## 3. Design assumptions

The following values are design choices, not measured physical constants.

### Saturn staging orbit

- Saturn-centred circular orbit.
- Radius from Saturn's centre: `600,000 km` (`6.0e8 m`).
- Coplanar with Titan's simplified circular orbit.

This radius is deliberately separate from the application's current Saturn
capture altitude. NASA data place the outer edge of the diffuse E ring near
`480,000 km` from Saturn's centre. The 600,000 km staging radius is outside that
nominal edge and beyond Rhea's mean orbit, but it is not a certified operationally
safe orbit.

Ring reference:
<https://nssdc.gsfc.nasa.gov/planetary/factsheet/satringfact.html>

The manoeuvres required to move from Saturn arrival/capture to this staging orbit
are **not included** in this model. They must remain a separate, visibly missing
budget phase until modelled.

### Titan capture orbit

- Circular Titan-centred orbit.
- Nominal altitude above Titan's mean radius: `1,500 km` (`1.5e6 m`).
- Nominal capture radius: `4,074.76 km` (`4.07476e6 m`).

NASA describes Titan's atmosphere as extending to nearly 600 km. The 1,500 km
altitude therefore provides a preliminary margin for a purely impulsive capture,
but it is not an aerothermal clearance certification.

Atmosphere reference:
<https://science.nasa.gov/saturn/moons/titan/facts/>

### Dynamical simplifications

- Saturn and Titan are point masses for their respective two-body phases.
- Titan's Saturn-centred orbit is treated as circular at its mean semimajor axis.
- The staging orbit and Titan orbit are treated as coplanar.
- The transfer is a two-impulse Hohmann transfer.
- Burns are instantaneous.
- Departure is phased so Titan reaches the encounter point at transfer arrival.
- Titan capture is impulsive and fully propulsive.
- No aerocapture, gravity assist, plane change, finite burn, oblateness, ring
  interaction, third-body perturbation, moon perturbation, station keeping, or
  navigation correction is included.
- Titan's published eccentricity and inclination are retained as metadata but
  deliberately ignored by this first-order solver.

## 4. Inputs and validation

All production calculations use SI units internally.

Required inputs:

- `saturn_staging_radius_m`: Saturn-centred radius, default `6.0e8 m`.
- `titan_capture_altitude_m`: altitude above Titan mean radius, default `1.5e6 m`.

Validation rules:

- all inputs and constants must be finite and strictly positive;
- staging radius must be greater than `4.8e8 m`, the nominal outer E-ring radius
  used by this preliminary model;
- staging radius must be less than Titan's mean orbital radius;
- Titan capture altitude must be at least `1.0e6 m` for this non-atmospheric
  preliminary mode;
- output values must be finite and non-negative;
- callers must not pass kilometres to an API documented in metres.

The ring and atmosphere thresholds are conservative design guards, not guarantees
of mission safety.

## 5. Equations

Let:

- `mu_s` be Saturn's gravitational parameter;
- `mu_t` be Titan's gravitational parameter;
- `r_1` be the Saturn staging-orbit radius;
- `r_2` be Titan's simplified Saturn-centred orbital radius;
- `r_p` be the Titan capture-orbit radius;
- `a_t = (r_1 + r_2) / 2` be the transfer-ellipse semimajor axis.

Saturn staging circular speed:

```text
v_circular_1 = sqrt(mu_s / r_1)
```

Transfer speed at Saturn staging radius:

```text
v_transfer_periapsis = sqrt(mu_s * (2 / r_1 - 1 / a_t))
```

Departure impulse:

```text
delta_v_departure = v_transfer_periapsis - v_circular_1
```

Transfer speed at Titan's orbital radius:

```text
v_transfer_apoapsis = sqrt(mu_s * (2 / r_2 - 1 / a_t))
```

Simplified Titan Saturn-centred circular speed:

```text
v_titan = sqrt(mu_s / r_2)
```

Titan-relative hyperbolic excess speed:

```text
v_infinity_titan = abs(v_titan - v_transfer_apoapsis)
```

Hohmann time of flight:

```text
time_of_flight = pi * sqrt(a_t^3 / mu_s)
```

Titan capture radius:

```text
r_p = radius_titan + titan_capture_altitude
```

Impulsive Titan capture into a circular orbit:

```text
delta_v_capture =
    sqrt(v_infinity_titan^2 + 2 * mu_t / r_p) - sqrt(mu_t / r_p)
```

Modelled Saturn-to-Titan total:

```text
delta_v_total = delta_v_departure + delta_v_capture
```

This total explicitly excludes Saturn arrival-to-staging manoeuvres.

## 6. Nominal regression case

Inputs:

- Saturn staging radius: `600,000 km`;
- Titan orbital radius: `1,221,900 km`;
- Titan capture altitude: `1,500 km`;
- official constants listed above.

Expected first-order outputs:

| Output | Expected value |
| --- | ---: |
| Saturn staging circular speed | 7,951.017359 m/s |
| Transfer departure speed | 9,208.592692 m/s |
| Departure ΔV | 1,257.575332 m/s |
| Transfer arrival speed | 4,521.773971 m/s |
| Titan Saturn-centred circular speed | 5,571.607245 m/s |
| Titan-relative `v_infinity` | 1,049.833274 m/s |
| Time of flight | 443,499.726268 s |
| Time of flight | 5.133099 days |
| Titan capture ΔV | 862.725696 m/s |
| Modelled total ΔV | 2,120.301028 m/s |

Numerical regression tests may use an absolute tolerance of `1e-3 m/s` and
`1e-3 s`. These tolerances test deterministic implementation equivalence; they do
not claim millimetre-per-second physical accuracy for the simplified model.

## 7. Required output contract

The future implementation must return a canonical `TrajectoryResult` or a
dedicated typed result containing at least:

- origin `Saturn`;
- destination `Titan`;
- method identifier such as `hohmann_circular_coplanar`;
- staging radius;
- Titan capture altitude and radius;
- departure ΔV;
- Titan `v_infinity`;
- capture ΔV;
- total modelled ΔV;
- time of flight;
- explicit assumptions and exclusions;
- source/version identifier `JPL SAT441`.

The result must keep `v_infinity_titan` separate from propulsive ΔV.

## 8. Acceptance criteria before UI integration

- Constants match the JPL values in this document after SI conversion.
- Nominal regression values match within the declared numerical tolerance.
- Increasing Titan capture altitude changes capture ΔV consistently with the
  implemented equation.
- Setting staging radius at or below the ring guard raises a clear error.
- Setting staging radius at or above Titan's orbital radius raises a clear error.
- Setting capture altitude below the non-atmospheric guard raises a clear error.
- No existing Earth-to-Saturn numerical regression changes.
- The UI labels the result as preliminary and shows that Saturn capture-to-staging
  ΔV is missing.
- The result is not added to the full mission mass budget until the missing
  Saturn arrival-to-staging phase is either modelled or explicitly accepted by the
  user as an exclusion.
