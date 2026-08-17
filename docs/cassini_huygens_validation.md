# Cassini–Huygens order-of-magnitude validation

Status: **deterministic architecture comparison — not a claim that the current model reproduces
Cassini–Huygens**.

## Current model case and traceability

This comparison was regenerated from the current test-passing functions, not copied from the
earlier validation pass:

- `trajectory.compute_trajectory()` for the locked Earth-to-Saturn solution;
- `mission.full_mission.compute_earth_saturn_titan_mission()` for the connected chain;
- `mission.dv_budget.compose_complete_dv_budget()` for the propulsive terms;
- `mission.sizing.compute_mass_budget()` for the explicitly simplified displayed mass;
- `mission.feasibility_check.evaluate_single_stage_chemical_feasibility()` for the independent
  Hesperos-calibrated single-stage check.

The deterministic case uses:

- departure MJD2000: `9,681.181818181818`;
- Earth-to-Saturn time of flight: `2,856.000000 days` (`7.819301848 years`);
- Earth departure hyperbolic excess speed: `10,432.306468 m/s`;
- Saturn arrival hyperbolic excess speed: `6,490.744714 m/s`;
- LEO altitude: `250 km`;
- Saturn arrival periapsis radius: `62,330 km`;
- Saturn staging circular-orbit radius: `600,000 km`;
- Titan capture altitude: `1,500 km`;
- main-engine specific impulse: `320 s`;
- aggregate science payload: `143.5 kg`, `323 W`.

| Current model term | Delta-v |
| --- | ---: |
| Earth departure injection | 7,381.479535 m/s |
| DSM / fly-by corrections | 0.000000 m/s |
| Saturn capture to transfer ellipse | 2,280.780159 m/s |
| Saturn staging circularisation | 4,501.573750 m/s |
| Saturn staging to Titan transfer | 1,257.575332 m/s |
| Titan circular capture | 862.725696 m/s |
| **Connected total** | **16,284.134471 m/s** |

The complete modeled duration to Titan arrival is `2,862.258233 days` (`7.836435957 years`).

The displayed mass remains an explicitly simplified rocket-equation estimate. For the `143.5 kg`
payload it gives `223.860000 kg` dry mass, `39,916.780790 kg` propellant, and
`40,140.640790 kg` wet mass, with a mass ratio of `179.311359`. It does not couple propulsion
hardware mass to propellant mass and is not a launch-vehicle sizing result.

## Official Cassini–Huygens reference points

- NASA reports launch on 15 October 1997, Saturn arrival on 1 July 2004, a `5,712 kg`
  launch mass including fuel, Huygens and the adapter, and `2,978 kg` of loaded propellant.
  Source: [NASA Cassini quick facts](https://science.nasa.gov/mission/cassini/quick-facts/).
- NASA describes the VVEJGA flight as a `6.7-year` trajectory using two Venus flybys, one
  Earth flyby and one Jupiter flyby. Source:
  [NASA/JPL Cassini trajectory](https://science.nasa.gov/resource/cassini-trajectory/).
- A NASA propulsion study gives a `5,609 kg` beginning-of-life accounting boundary,
  `312 s` propulsion performance and `2,039 m/s` axial-propulsion delta-v capability. The
  `2,039 m/s` value is an onboard capability, **not** Cassini's LEO-injection burn. Source:
  [NASA/TM—2005-214025](https://ntrs.nasa.gov/api/citations/20060000023/downloads/20060000023.pdf).
- Cassini's Saturn Orbit Insertion burn was approximately `626 m/s` and inserted the spacecraft
  into a highly elliptical Saturn orbit. Source:
  [JPL navigation performance assessment](https://descanso.jpl.nasa.gov/DPSummary/DESCANSO17_Cassini_RevA.pdf).
- NASA explains that even the Titan IVB/Centaur could not send the nearly `6,000 kg` spacecraft
  directly to Saturn; planetary gravity assists supplied the required heliocentric energy, and
  Titan flybys subsequently reshaped Cassini's Saturn-centred orbit. Source:
  [NASA Cassini gravity assists](https://science.nasa.gov/mission/cassini/gravity-assists/).
- Huygens was released on 24 December 2004 and descended at Titan on 14 January 2005. It used
  ballistic atmospheric entry rather than circular Titan capture. Sources:
  [NASA Cassini quick facts](https://science.nasa.gov/mission/cassini/quick-facts/) and
  [ESA Cassini–Huygens factsheet](https://www.esa.int/Science_Exploration/Space_Science/Cassini-Huygens/Cassini-Huygens_factsheet2).

Reference masses vary slightly with date and accounting boundary. The comparison therefore keeps
the `5,712 kg` NASA launch mass as its primary reference and labels the `5,609 kg` propulsion-study
boundary separately.

## Final comparison summary

| Quantity | Current connected model | Cassini–Huygens reference | Architectural explanation |
| --- | ---: | ---: | --- |
| Earth departure | 7,381.479535 m/s charged as propulsive LEO injection | Titan IVB/Centaur launch plus VVEJGA; no equivalent onboard LEO burn | The model uses a direct no-assist transfer; Cassini split launch energy from onboard propulsion and added energy through four gravity assists. |
| Connected propulsive delta-v / onboard capability | 16,284.134471 m/s total modeled burns | 2,039 m/s axial onboard capability | These boundaries are deliberately not equivalent: the model charges launch injection, Saturn circularisation and Titan capture to one budget. |
| Saturn arrival and staging | 6,782.353909 m/s, including circularisation at 600,000 km | approximately 626 m/s SOI into a highly elliptical orbit | Circular staging is much more expensive than becoming weakly bound; Cassini then used Titan flybys to reshape its orbit. |
| Titan endpoint | 862.725696 m/s circular-capture burn, after a 1,257.575332 m/s transfer departure | Huygens ballistic delivery and atmospheric entry | The model targets a Titan orbiter; Huygens did not circularise around Titan. |
| Earth-to-Saturn duration | 2,856.000 days (`7.819 years`) | approximately `6.7 years` (`2,451` calendar days from published dates) | Cassini's faster elapsed time used the longer-path VVEJGA architecture; duration alone is not a measure of trajectory energy. |
| Launch-to-Titan endpoint duration | 2,862.258 days (`7.836 years`) | `2,648` calendar days (`7.250 years`) from launch to Huygens landing | The endpoints differ: modeled Titan orbital arrival versus Huygens atmospheric descent. |
| Wet/launch mass | 40,140.640790 kg simplified single-stage estimate | 5,712 kg at launch | The model applies the whole ΔV to one ideal chemical stage with only 223.86 kg simplified dry mass; Cassini used a launch vehicle, assists, a tonne-scale spacecraft and onboard propulsion. |

## Single-stage feasibility finding

The independent Hesperos-calibrated model strengthens the same architectural conclusion without
using the simplified `40,140.64 kg` estimate. With `Isp = 320 s`, a `20%` system margin and the
calibrated propulsion-dry/propellant coupling, its analytical convergence boundary is
`3,833.463446 m/s`. The current `16,284.134471 m/s` requirement is `4.247890895` times that
threshold, and `size_parametric_vehicle()` correctly raises `MassArchitectureInfeasibleError`.

This is not a numerical failure. It is independent evidence that the direct, no-assist budget
cannot be assigned to one non-discarding chemical stage. A credible architecture requires a
launch-vehicle/onboard-propulsion split, discardable or multiple stages, a substantial delta-v
reduction strategy such as Cassini's VVEJGA sequence, or a combination of these measures.
Multi-stage sizing remains outside the current model scope.

## Interpretation for the final report

1. **The total delta-v gap is explained by the accounting boundary and trajectory architecture.**
   The model includes LEO injection and no gravity-assist credit; Cassini used a launch vehicle
   and VVEJGA before relying on its onboard system.
2. **The Saturn gap is explained by the target orbit.** The model circularises at `600,000 km`;
   Cassini performed a much smaller SOI burn into a highly elliptical capture orbit and used
   Titan encounters for subsequent orbit changes.
3. **The Titan gap is explained by mission role.** The model includes circular Titan capture;
   Huygens entered the atmosphere ballistically.
4. **The displayed mass is illustrative, not validated.** Its simplified formula produces a
   finite value, while the calibrated coupling model correctly concludes that the assumed
   single-stage architecture is infeasible.

The valid final claim is therefore not that the tool reproduces Cassini–Huygens. It is that the
tool deterministically quantifies why a direct, fully propulsive Earth–Saturn–Titan architecture
requires the architecture choices demonstrated by Cassini: launcher-provided departure energy,
gravity assists, elliptical capture, moon flybys and ballistic atmospheric delivery.
