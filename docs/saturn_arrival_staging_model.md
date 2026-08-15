# Preliminary Saturn arrival-to-staging model

Status: scientific specification only — no production implementation yet.

## 1. Purpose and boundary

Define a transparent first-order model that connects the existing heliocentric
Earth-to-Saturn Lambert arrival to the `600,000 km` Saturn-centred circular
staging orbit used by the preliminary Saturn-to-Titan model.

The reference architecture does **not** first circularise in a low Saturn orbit.
It performs:

1. an impulsive burn at Saturn periapsis that captures the incoming hyperbola
   directly into an ellipse whose apoapsis is the staging radius; and
2. an impulsive burn at apoapsis that circularises into the staging orbit.

This distinction is mandatory. When eventually integrated into the full mission
budget, the two burns in this document must **replace**, not supplement, the
current `dV Capture at Destination` value. Adding both would double-count Saturn
capture.

### Existing capture contract versus the reference architecture

The current Earth-to-Saturn budget has one precise target state: an impulsive
transition from the incoming Saturn-relative hyperbola to a **circular** orbit at
`PyKEP Saturn radius + capture_altitude`. In the nominal regression this is a
circular orbit of radius `60,330 + 2,000 = 62,330 km`, and the already-budgeted
capture delta-v is `10,816.855099 m/s` using the current PyKEP constant.

That circular orbit is not the `600,000 km` staging orbit. Moving from it to the
staging orbit would be an additional two-burn transfer. The reference architecture
in this document deliberately chooses a mutually exclusive, more efficient target
for the Saturn arrival burn: an ellipse with periapsis `62,330 km` and apoapsis
`600,000 km`. Consequently there are two alternative budget modes:

- legacy mode: circular capture at `62,330 km`, with no staging transfer;
- staging mode: capture directly into the `62,330 × 600,000 km` ellipse, followed
  by circularisation at `600,000 km`.

They must never be active simultaneously in one budget.

The existing Earth-to-Saturn calculation and its numerical regressions remain
unchanged until a separate integration step is explicitly approved.

## 2. Authoritative data and model inputs

All production calculations use SI units.

### 2.1 Authoritative constant

| Quantity | Symbol | Source value | Internal SI value |
| --- | --- | ---: | ---: |
| Saturn gravitational parameter | `mu_saturn` | 37,931,206.23 km³/s² | 3.793120623e16 m³/s² |

Source: JPL Solar System Dynamics, SAT441:
<https://ssd.jpl.nasa.gov/sats/phys_par/sep.html>

JPL lists an uncertainty of `±0.24 km³/s²`. The deterministic regression values
below use the central value without uncertainty propagation.

For geometric context, JPL lists Saturn's equatorial radius as `60,268 ± 4 km`
and mean radius as `58,232 ± 6 km`:
<https://ssd.jpl.nasa.gov/planets/phys_par.html>

The solver must not silently use either radius to reconstruct the periapsis. It
accepts the actual periapsis radius used by the upstream Earth-to-Saturn capture
contract, because the current PyKEP low-precision Saturn body uses a different
reference radius (`60,330 km`). This preserves the existing trajectory results
while making the boundary explicit.

### 2.2 Required dynamic inputs

- `arrival_v_infinity_m_s`: Saturn-relative hyperbolic excess speed delivered by
  the selected Earth-to-Saturn Lambert solution.
- `periapsis_radius_m`: Saturn-centred periapsis radius used for the capture burn.
- `staging_radius_m`: Saturn-centred circular staging radius; default `6.0e8 m`.

Nominal upstream values used for regression:

- arrival `v_infinity`: `6,490.744714263188 m/s`;
- capture altitude selected in the current UI: `2,000 km`;
- current PyKEP Saturn reference radius: `60,330 km`;
- resulting periapsis radius: `62,330 km` (`6.233e7 m`);
- staging radius: `600,000 km` (`6.0e8 m`).

The PyKEP radius is compatibility metadata, not a new physical constant. Future
code should pass `periapsis_radius_m` explicitly and record its provenance.

## 3. Ring-system constraint and safety status

NASA's Saturnian Rings Fact Sheet places the main ring features approximately
between `66,900 km` and `173,000 km` from Saturn's centre and the diffuse E ring
between `180,000 km` and `480,000 km`:
<https://nssdc.gsfc.nasa.gov/planetary/factsheet/satringfact.html>

NASA independently describes the E ring as extending from about `180,000 km` to
`482,000 km`:
<https://science.nasa.gov/resource/the-enceladus-ring-2/>

NASA also describes the main rings as thin but the E ring as diffuse:
<https://science.nasa.gov/saturn/facts/>

The nominal transfer spans radii from `62,330 km` to `600,000 km`. A coplanar
equatorial interpretation would therefore cross the radial domains of the D, C,
B, A, F, G, and E rings. Merely placing the final staging orbit outside
`480,000 km` does **not** make the transfer ring-safe.

The numerical margins are explicit:

- reference F-ring radius: `140,180 km` from Saturn's centre;
- transfer periapsis minus F-ring radius: `62,330 - 140,180 = -77,850 km`;
- nominal staging radius minus the `480,000 km` outer E-ring guard: `+120,000 km`;
- nominal staging radius minus NASA's alternate `482,000 km` E-ring extent:
  `+118,000 km`.

Because the staging orbit is circular, its periapsis and apoapsis are both
`600,000 km`; its minimum radial margin beyond the alternate E-ring edge is
therefore `118,000 km`. The `62,330 km` value is the periapsis of the captured
**transfer ellipse**, not the periapsis of the final staging orbit.

Thus the final circular staging orbit has at least `118,000 km` of radial margin
beyond the cited E-ring edge, but the transfer path has **no positive radial
safety margin** relative to the rings. Its periapsis is `77,850 km` inside the
F-ring reference radius and the outbound arc passes through that radius. The
specified safety margin for the transfer itself is therefore `not established`,
not zero-risk and not “outside the rings.” The value `140,180 km` is taken from
NASA's Cassini mission reference guide:
<https://science.nasa.gov/wp-content/uploads/2023/09/cassini.pdf>

This scalar two-body model contains no orbit-plane orientation, node geometry,
ring-particle environment, collision probability, or operational clearance
analysis. Its ring-clearance status is therefore `unresolved`.

Consequences:

- results are energy estimates only, not a flyable trajectory;
- the UI must display a prominent ring-crossing warning;
- the phase must not enter the global mission or mass budget by default;
- operational integration requires a three-dimensional arrival geometry and a
  documented ring-plane avoidance strategy reviewed independently.

## 4. Dynamical assumptions

- Saturn is a point mass with constant `mu_saturn`.
- The incoming planetocentric trajectory is hyperbolic with scalar `v_infinity`.
- The capture burn occurs instantaneously at the specified periapsis.
- The post-capture orbit is an ellipse with periapsis `r_p` and apoapsis `r_a`.
- The staging orbit is circular at `r_a`.
- The second burn occurs instantaneously at apoapsis.
- Burns are tangential and ideally aligned with the velocity vector.
- The transfer is treated as coplanar for energy calculation only; this does not
  assert coplanarity with Saturn's rings.
- No plane change, Saturn oblateness, atmospheric interaction, finite burn,
  third-body perturbation, moon encounter, ring interaction, navigation
  correction, station keeping, or propulsion loss is included.
- The arrival epoch affects the upstream Lambert `v_infinity`, but not this
  time-invariant two-body calculation.

## 5. Validation rules

The future pure engine must enforce:

- every numeric input and constant is a real, finite number;
- `arrival_v_infinity_m_s >= 0`;
- `mu_saturn > 0`;
- `periapsis_radius_m > 0`;
- `staging_radius_m > periapsis_radius_m`;
- `staging_radius_m > 4.8e8 m`, matching the preliminary outer E-ring guard;
- all square-root radicands are finite and non-negative;
- every returned speed, duration, and delta-v is finite and non-negative;
- kilometres are converted at the caller boundary; the engine accepts metres;
- booleans are rejected as numeric inputs.

The ring guard constrains only the final staging radius. It does not validate the
path through the ring system.

## 6. Equations

Let:

- `mu` be Saturn's gravitational parameter;
- `v_inf` be the Saturn-relative arrival hyperbolic excess speed;
- `r_p` be the capture periapsis radius;
- `r_a` be the staging-orbit radius and transfer apoapsis;
- `a_t = (r_p + r_a) / 2` be the captured ellipse semimajor axis.

Incoming hyperbolic speed at periapsis:

```text
v_hyp_p = sqrt(v_inf^2 + 2 * mu / r_p)
```

Captured-ellipse speed at periapsis:

```text
v_transfer_p = sqrt(mu * (2 / r_p - 1 / a_t))
```

Capture burn directly into the staging-transfer ellipse:

```text
delta_v_capture_to_ellipse = v_hyp_p - v_transfer_p
```

Captured-ellipse speed at apoapsis:

```text
v_transfer_a = sqrt(mu * (2 / r_a - 1 / a_t))
```

Circular speed at the staging radius:

```text
v_circular_staging = sqrt(mu / r_a)
```

Staging-orbit circularisation burn:

```text
delta_v_staging_circularisation = v_circular_staging - v_transfer_a
```

Time from periapsis to apoapsis:

```text
time_of_flight = pi * sqrt(a_t^3 / mu)
```

Modelled phase total:

```text
delta_v_phase_total =
    delta_v_capture_to_ellipse + delta_v_staging_circularisation
```

For valid inputs with `r_a > r_p`, both burns are expected to be non-negative.

## 7. Nominal deterministic regression

Using the nominal inputs in section 2.2 and the SAT441 central `mu`:

| Output | Expected value |
| --- | ---: |
| Hyperbolic periapsis speed | 35,485.756342 m/s |
| Transfer-ellipse periapsis speed | 33,204.976183 m/s |
| Capture-to-ellipse ΔV | 2,280.780159 m/s |
| Transfer-ellipse apoapsis speed | 3,449.443609 m/s |
| Staging circular speed | 7,951.017359 m/s |
| Staging circularisation ΔV | 4,501.573750 m/s |
| Phase total ΔV | 6,782.353909 m/s |
| Periapsis-to-apoapsis time | 97,211.622651 s |
| Periapsis-to-apoapsis time | 1.125135 days |

Numerical regression tests may use absolute tolerances of `1e-3 m/s` and
`1e-3 s`. These tolerances verify deterministic implementation equivalence and
do not imply millimetre-per-second physical fidelity.

For comparison only, applying the same SAT441 constant to an immediate circular
capture at `62,330 km` gives `10,816.857540 m/s`. That comparison value is not a
third burn and must not be included in the phase total.

## 8. Required output contract

The pure solver may use an immutable typed calculation result for its detailed
burn breakdown, following the existing `SaturnTitanTransferResult` pattern. It
must not introduce a parallel mission-domain hierarchy. At the integration
boundary, the phase is represented by the existing types as follows:

- one `Leg(origin="Saturn", destination="Saturn")` so body continuity with the
  preceding Earth-to-Saturn leg and following Saturn-to-Titan leg is preserved;
- one canonical `TrajectoryResult` attached to that leg;
- `TrajectoryResult.v_inf_arrival = arrival_v_infinity_m_s`;
- `TrajectoryResult.v_inf_depart = None` because the final staging state is bound;
- `TrajectoryResult.delta_v = delta_v_phase_total`;
- `TrajectoryResult.tof_years = time_of_flight_s / (365.25 * 86400)`;
- `TrajectoryResult.method = "hyperbolic_capture_to_elliptic_staging"`;
- a `Saturn capture-to-ellipse` event at the Earth-to-Saturn arrival epoch;
- a `Saturn staging circularisation` event one transfer time later.

The detailed typed calculation result must contain at least:

- origin state `Saturn hyperbolic arrival`;
- destination state `Saturn staging circular orbit`;
- method `hyperbolic_capture_to_elliptic_staging`;
- source/version `JPL SAT441`;
- input `arrival_v_infinity_m_s`;
- periapsis and staging radii;
- transfer semimajor axis;
- hyperbolic and transfer speeds at periapsis;
- capture-to-ellipse delta-v;
- transfer and circular speeds at apoapsis;
- staging circularisation delta-v;
- phase total delta-v;
- periapsis-to-apoapsis time;
- explicit assumptions and exclusions;
- `ring_clearance_status = "unresolved"`;
- provenance of the periapsis radius.

The adapter into `TrajectoryResult` and `Leg` must copy numerical values without
recomputing them. The pure output must not mutate or depend on Streamlit state,
PyKEP objects, pandas objects, or the global mass budget.

## 9. Future budget-integration rule

The current Earth-to-Saturn budget contains a circular Saturn-capture burn. A
future complete preliminary chain must be assembled as:

```text
Earth departure and any DSM/flyby terms
+ Saturn capture-to-staging phase total from this model
+ Saturn-to-Titan modelled total
```

It must exclude the old circular `dV Capture at Destination` term when the new
capture-to-staging phase is selected. The UI must show which mutually exclusive
capture architecture is active.

Even after numerical integration, the combined result must remain excluded from
the default mass budget until the unresolved ring-clearance status is explicitly
accepted as a preliminary trade-study limitation.

## 10. Independent validation strategy

The deterministic regression in section 7 is the primary numerical oracle. The
future tests must additionally verify independent physical identities, rather
than only repeating the implementation formulas:

- incoming specific orbital energy reconstructed at periapsis equals
  `v_inf^2 / 2`;
- captured-ellipse specific energy reconstructed independently at periapsis and
  apoapsis equals `-mu / (2 * a_t)` at both points;
- angular momentum reconstructed as `r_p * v_transfer_p` equals
  `r_a * v_transfer_a`;
- the staging circular state satisfies `v_circular_staging^2 * r_a = mu`;
- the reported total equals the sum of exactly two burns;
- changing one input produces the expected monotonic behaviour without changing
  either existing trajectory engine.

Cassini provides an external architecture-level check, not a direct numerical
regression. NASA reports that Cassini's Saturn Orbit Insertion burn was
`626.17 m/s` and captured the spacecraft into Saturn orbit. NASA's operational
timeline records a `96 minute` finite burn, closest approach at `80,230 km` from
Saturn's centre, and protected ascending and descending ring-plane crossings at
`158,500 km`. This confirms both that capture into a bound Saturn orbit is a real
flight architecture and that ring-plane geometry is an operational constraint.
Cassini's delta-v must not be compared numerically to the nominal result here
because the published summary does not define the same arrival state and target
orbit, and the flight used a finite, steered, three-dimensional burn.

Official references:

- NASA Cassini SOI event report:
  <https://science.nasa.gov/missions/cassini/significant-event-report-for-week-ending-792004/>
- NASA Cassini SOI timeline, including the protected ring-plane crossing at
  `158,500 km` and the approximately `626 m/s` burn:
  <https://www.nasa.gov/wp-content/uploads/2015/01/61369main_soitimeline.pdf>

The implementation is rejected if it matches the nominal table but fails any
energy, angular-momentum, or budget-exclusivity invariant.

## 11. Acceptance criteria before implementation

- Constants and SI conversions match the official sources above.
- Nominal results match section 7 within the declared tolerances.
- Increasing `arrival_v_infinity_m_s` increases capture-to-ellipse delta-v.
- Setting `arrival_v_infinity_m_s` to zero remains finite and non-negative.
- A staging radius at or below the periapsis radius raises a clear error.
- A staging radius at or below the outer E-ring guard raises a clear error.
- Non-numeric, Boolean, NaN, and infinite inputs raise clear errors.
- The output keeps both burns separate and their sum exact within floating-point
  precision.
- The result explicitly reports unresolved ring clearance.
- The result reports the `-77,850 km` F-ring radial comparison and an
  `unestablished` transfer safety margin; it must not claim ring safety.
- The canonical adapter produces one Saturn-to-Saturn `Leg` containing one
  `TrajectoryResult` and the two required events without numerical recomputation.
- Energy and angular-momentum invariants in section 10 pass within documented
  floating-point tolerances.
- No existing Earth-to-Saturn or Saturn-to-Titan regression changes.
- No Streamlit or global-budget integration is added with the pure engine.
- Future global integration replaces the old Saturn circular-capture term rather
  than adding both capture architectures.
