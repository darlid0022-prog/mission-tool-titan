# Cassini–Huygens order-of-magnitude validation

Status: **major architecture mismatch — not validated as a Cassini-like mission**.

## Model case used

The deterministic comparison uses the current nominal connected chain:

- LEO departure at 250 km;
- Saturn arrival periapsis radius: 62,330 km;
- Saturn staging circular-orbit radius: 600,000 km;
- Titan capture altitude: 1,500 km;
- main-engine specific impulse: 320 s;
- illustrative instrument mass: 10 kg.

| Model term | Delta-v |
| --- | ---: |
| Earth departure injection | 7,381.480 m/s |
| DSM / fly-by corrections | 0.000 m/s |
| Saturn capture to transfer ellipse | 2,280.780 m/s |
| Saturn staging circularisation | 4,501.574 m/s |
| Saturn staging to Titan transfer | 1,257.575 m/s |
| Titan circular capture | 862.726 m/s |
| **Connected total** | **16,284.134 m/s** |

The current single-stage rocket-equation sizing gives a mass ratio of about 179.3 and,
for the illustrative 15.6 kg dry mass, 2,781.7 kg of propellant and 2,797.3 kg wet mass.

## Official Cassini–Huygens reference points

- NASA reports a 5,712 kg launch mass and 2,978 kg of loaded propellant. It also reports
  a 2,125 kg end-of-mission orbiter mass. Source: [NASA Cassini quick facts](https://science.nasa.gov/mission/cassini/quick-facts/).
- The Cassini press kit gives a 2,125 kg orbiter, a 320 kg Huygens probe, 3,132 kg of
  propellant, and 5,712 kg at launch including the adapter. Source:
  [NASA/JPL Cassini press kit](https://www.jpl.nasa.gov/news/press_kits/cassini.pdf).
- A NASA propulsion study states a 5,609 kg beginning-of-life mass, 312 s propulsion
  performance, and 2,039 m/s axial-propulsion delta-v capability. Source:
  [NASA/TM—2005-214025](https://ntrs.nasa.gov/api/citations/20060000023/downloads/20060000023.pdf).
- Cassini's Saturn Orbit Insertion was a 626 m/s burn. Source:
  [JPL navigation performance assessment](https://descanso.jpl.nasa.gov/DPSummary/DESCANSO17_Cassini_RevA.pdf).
- Cassini reached Saturn after four gravity assists: Venus twice, Earth, and Jupiter.
  Source: [NASA Cassini navigation](https://science.nasa.gov/mission/cassini/spacecraft/navigation/).
- ESA reports that Huygens separated onto a ballistic 22-day trajectory to Titan; it was
  not inserted into a circular Titan orbit. Source:
  [ESA Cassini–Huygens factsheet](https://www.esa.int/Science_Exploration/Space_Science/Cassini-Huygens/Cassini-Huygens_factsheet2).

Reference masses vary slightly with date and accounting boundary (adapter, probe support
equipment, and loaded versus used propellant). This does not affect the conclusion.

## Findings

1. **The 16.284 km/s model total is not comparable to Cassini onboard delta-v.** The model
   charges LEO injection to the spacecraft, while Cassini's Titan IVB/Centaur supplied Earth
   escape and gravity assists supplied most heliocentric energy.
2. **The Saturn phase is intentionally much more expensive.** The model spends
   6.782 km/s to capture and circularise at 600,000 km. Cassini used a roughly 0.626 km/s SOI
   into a highly elliptical orbit and then exploited Titan flybys instead of circularising into
   the model's staging orbit.
3. **The Titan endpoint differs.** The model includes 0.863 km/s for circular Titan capture;
   Huygens performed atmospheric entry after ballistic delivery.
4. **The apparent wet-mass similarity is not validation.** The model's 2.797 t wet mass is
   generated from only 15.6 kg dry mass and a mass ratio near 179. Cassini had tonne-scale dry
   hardware and a wet-to-non-propellant ratio near 2. The current dry-mass model represents only
   instrument-derived scaling, not a complete spacecraft bus.

## Decision before final claims

Do not claim Cassini-like feasibility or use the current wet mass as a final spacecraft mass.
Before final validation, choose and document one architecture:

1. a Cassini-like architecture using launch-vehicle injection, planetary gravity assists,
   elliptical Saturn capture, Titan flybys, and ballistic/atmospheric Titan delivery; or
2. the current fully propulsive Titan-orbiter architecture, with launch injection accounted
   separately, a staged or high-performance propulsion system, and a complete dry-mass model.

The implemented calculations remain useful as deterministic first-order phase studies, but the
combined mass result is a rocket-equation consequence, not yet a mission-level validation.
