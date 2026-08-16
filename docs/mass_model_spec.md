# Spacecraft mass model specification

Status: implementation specification derived from `mission_design_tool.xlsx` and calibrated against
the published Hesperos Venus-orbiter concept study.
No numerical mass result from the workbook is accepted as a validated mission baseline because
the component catalogues are empty and the propulsion inputs are incomplete.

## 1. Scope

The future engine shall size two independently identifiable elements:

- the Saturn orbiter, which also carries the Titan entry vehicle until separation;
- the Titan entry vehicle (called `lander` in the workbook).

It shall compute subsystem mass, payload mass, dry mass, power-system mass, manoeuvre-by-manoeuvre
propellant mass, launch wet mass, and an auditable breakdown. It shall remain separate from the
trajectory solvers: trajectory code supplies manoeuvres and delta-v; sizing code consumes them.

Because the workbook component catalogues are empty, the first implementation shall use a
parametric subsystem model rather than manufacture fictitious component data. It shall retain the
workbook's deterministic power and rocket-equation relationships. Communication-link design,
detailed thermal sizing, structural finite-element analysis, Titan EDL aerodynamics, and RTG sizing
are excluded until separately specified.

## 2. Workbook mapping and authority

The workbook uses these relevant sheets:

- `Science`: payload mass, maximum power, and data-rate catalogues for orbiter and lander;
- `Data Handling`, `Communication`, `Thermal`, `Pointing Control`, and `Propulsion`: component
  catalogues with quantity, unit mass, total mass, and maximum power;
- `Power Budget`: operational scenarios, battery sizing, and solar-array sizing;
- `Structure`: geometric wall-volume calculations, currently disconnected from dry mass;
- `Dry Mass`: subsystem aggregation, harness, structure allowance, and maturity margin;
- `Propellant and Total Mass`: reverse rocket-equation calculation for the manoeuvre sequence.

The formulas in this specification are authoritative for the Python port. Workbook formulas that
are internally inconsistent are documented below and shall not be copied as-is.

## 3. Units and numerical conventions

- Mass: kg.
- Power: W.
- Energy: Wh.
- Specific energy: Wh/kg.
- Delta-v: m/s.
- Specific impulse: s.
- Standard gravity: use the project's canonical `G0_M_S2`, not the workbook's rounded `9.8 m/s²`.
- Time: s internally; hours may be accepted at the input boundary and converted explicitly.
- Distance: m; area: m²; density: kg/L only where tank-volume reporting is requested.
- Fractions are dimensionless values in `[0, 1)`.

All public inputs and outputs shall carry the unit in their field name unless represented by a
unit-aware type. NaN, infinity, negative mass, negative power, non-positive Isp, and negative
delta-v are invalid.

## 4. Reference calibration

Hesperos is an interplanetary Venus orbiter concept produced from the ESA/FFG Alpbach design
exercise and published in *Advances in Space Research*. Its orbiter dry-mass budget is:

- payload: `271.2 kg` (`18.2%` of total dry mass);
- propulsion hardware, including propellant tanks: `732.0 kg` (`49.1%`);
- AOCS: `59.6 kg` (`4.0%`);
- communications: `68.0 kg` (`4.6%`);
- C&DH/OBDH: `53.8 kg` (`3.6%`);
- thermal: `5.3 kg` (`0.4%`);
- power: `50.4 kg` (`3.4%`);
- structure and mechanisms: `250.1 kg` (`16.8%`);
- total orbiter dry mass: `1490.4 kg`.

The same study reports `2101.6 kg` of propellant for the overall spacecraft. Therefore the only
propulsion coefficient directly derivable from this source is:

`hesperos_propulsion_dry_to_propellant = 732.0 / 2101.6 = 0.3483060525`

Hesperos does **not** establish a generic `0.10–0.15` dry-propulsion/propellant ratio. Such a value
may later be tested as an explicitly sourced sensitivity case, but it shall not be labelled a
Hesperos calibration.

For a payload-driven model, normalise the non-propulsion dry mass (`758.4 kg`) to the payload:

- AOCS/payload: `0.2197640118`;
- communications/payload: `0.2507374631`;
- data handling/payload: `0.1983775811`;
- thermal/payload: `0.0195427729`;
- power/payload: `0.1858407080`;
- structure and mechanisms/payload: `0.9221976401`.

These ratios reproduce Hesperos exactly when the payload is `271.2 kg`. They are a single-mission
analogy, not universal spacecraft constants. In particular, structure is `16.8%` of total Hesperos
dry mass but `33.0%` of its dry mass excluding propulsion; those denominators must never be mixed.

Primary reference: R.-J. Koopmans et al., *Hesperos: A geophysical mission to Venus*, 2018,
Table 7 and Table 10, <https://arxiv.org/abs/1803.06652>.

## 5. Typed input contract

The implementation should introduce immutable dataclasses equivalent to:

```python
@dataclass(frozen=True)
class PayloadItem:
    name: str
    mass_kg: float
    max_power_w: float
    data_rate_bps: float = 0.0

@dataclass(frozen=True)
class PowerScenario:
    name: str
    active_subsystems: frozenset[str]

@dataclass(frozen=True)
class Manoeuvre:
    name: str
    delta_v_m_s: float
    isp_s: float
    vehicle: Literal["orbiter", "lander"]

@dataclass(frozen=True)
class ParametricBusCoefficients:
    aocs_per_payload: float = 0.2197640118
    communications_per_payload: float = 0.2507374631
    data_handling_per_payload: float = 0.1983775811
    thermal_per_payload: float = 0.0195427729
    power_per_payload: float = 0.1858407080
    structure_per_payload: float = 0.9221976401
    propulsion_dry_per_propellant: float = 0.3483060525
    system_margin_fraction: float = 0.20

@dataclass(frozen=True)
class ParametricMassModelInputs:
    payload: tuple[PayloadItem, ...]
    coefficients: ParametricBusCoefficients
    manoeuvres: tuple[Manoeuvre, ...]
    power_scenarios: tuple[PowerScenario, ...] = ()
    battery_depth_factor: float = 2.0
    battery_specific_energy_wh_kg: float = 200.0
    power_margin_factor: float = 1.20
```

Solar-array inputs shall be a separate optional configuration. They must not be the implicit default
for a Saturn mission because the workbook does not model an RTG and its solar formula produces an
architecture-dependent result.

## 6. Parametric subsystem aggregation

Payload mass, maximum power, and data rate are direct sums of payload items. Each non-propulsion
subsystem mass is then:

`subsystem_mass_kg = payload_mass_kg * subsystem_per_payload`

and:

`fixed_unmargined_mass_kg = payload_mass_kg + sum(non_propulsion_subsystem_masses)`

The propulsion hardware is computed separately because it is coupled to propellant mass. Empty
payloads are valid only for intermediate editing and shall mark the result as `incomplete`; they
shall not be presented as a validated zero-mass spacecraft.

## 7. Operational power model

For each scenario, the scenario demand is the sum of the maximum powers of active subsystems. The
orbiter workbook scenarios are launch, cruise, science, and communication; the lander scenarios are
landing, science, and communication.

`worst_case_power_w = max(scenario_power_w)`

Battery sizing follows the workbook:

`stored_energy_wh = worst_case_power_w * unpowered_duration_h`

`battery_capacity_wh = stored_energy_wh * battery_depth_factor`

`battery_mass_kg = battery_capacity_wh / battery_specific_energy_wh_kg`

`recharge_power_w = stored_energy_wh / powered_duration_h`

The default workbook values are a depth factor of `2.0` and specific energy of `200 Wh/kg`. Both
durations must be strictly positive where used.

If solar arrays are explicitly enabled, the workbook relationships are:

`generation_at_destination_w_m2 = generation_at_earth_w_m2 * (earth_sun_distance_m / destination_sun_distance_m) ** 2`

`required_generation_w = (worst_case_power_w + recharge_power_w) * power_margin_factor`

`panel_area_m2 = required_generation_w / generation_at_destination_w_m2`

`panel_mass_kg = panel_area_m2 * panel_areal_density_kg_m2`

Workbook defaults are `270 W/m²` at Earth, a power factor of `1.20`, and `3.3 kg/m²`. These are
engineering assumptions, not universal constants. For Titan, the Sun distance is Saturn-centred at
this model fidelity. An RTG configuration requires a later dedicated model and shall initially be an
explicit externally supplied power-system mass.

## 8. Dry-mass hierarchy

Payload must remain visible as a separate line item. In the parametric model, Hesperos structure and
mechanisms replaces the workbook's independent harness and 20% structure heuristics. Adding both
would double-count structural accommodation. The system-level margin is applied once:

`dry_mass_kg = (fixed_unmargined_mass_kg + propulsion_dry_mass_kg) * (1 + system_margin_fraction)`

The result must expose fixed bus, propulsion dry mass, and margin separately.

The geometric `Structure` sheet is not connected to `Dry Mass`. Therefore its wall-volume method
shall not be combined with the 20% structural allowance in version 1; doing so would risk double
counting. A future structure model may replace, but not supplement, that allowance.

## 9. Vehicle hierarchy and separation

The orbiter carries the lander before Titan separation. The sizing engine shall therefore model the
sequence backwards from final dry configurations:

1. compute lander dry mass;
2. apply lander-only manoeuvres backwards to obtain lander wet mass at separation;
3. compute orbiter dry mass;
4. initialise the post-separation orbiter terminal mass with orbiter dry mass;
5. for every pre-separation orbiter manoeuvre, include the complete lander wet mass as carried mass;
6. never add the lander dry or propellant mass a second time to launch wet mass.

The separation event must be explicit. A manoeuvre cannot silently change vehicles or Isp.

## 10. Coupled propellant and propulsion-hardware calculation

For one manoeuvre evaluated backwards in time:

`mass_before_kg = mass_after_kg * exp(delta_v_m_s / (isp_s * G0_M_S2))`

`propellant_kg = mass_before_kg - mass_after_kg`

For a sequence, traverse manoeuvres in reverse chronological order, feeding each `mass_before_kg`
into the preceding manoeuvre. Store mass before, mass after, propellant, Isp, and delta-v for every
step. Do not collapse different propulsion systems into one equivalent Isp.

The trajectory-to-sizing adapter shall use the canonical mission delta-v components already exposed
by `mission.dv_budget`. DSM is included only when it represents a propulsive burn; gravity-assist
velocity changes are not propellant-consuming delta-v. Atmospheric braking is also not passed to the
rocket equation.

Because propulsion dry mass depends on propellant while propellant depends on dry mass, the solver
shall iterate the complete manoeuvre ledger to a relative tolerance of `1e-10`, with a maximum of 200
iterations:

1. start with zero propulsion dry mass;
2. compute margined dry mass;
3. run the reverse manoeuvre ledger and obtain propellant mass;
4. set `propulsion_dry_mass_kg = coefficient * propellant_mass_kg`;
5. repeat until converged.

Failure to converge, non-finite mass, or monotonically diverging mass shall raise a
`MassArchitectureInfeasibleError`. This is expected for some high-delta-v, single-stage chemical
architectures and is a scientific result, not a number to suppress. An analytic feasibility check may
be used for the single-Isp case, but the iterative ledger remains authoritative for mixed-Isp burns.

## 11. Output contract

The result shall provide at least:

- orbiter and lander payload mass;
- subsystem mass and maximum-power breakdowns;
- worst-case scenario power and scenario name;
- battery capacity and mass;
- power-generation system mass and model identifier;
- calibration identifier and every subsystem coefficient;
- fixed bus, propulsion dry mass, structure/mechanisms, and system margin;
- orbiter and lander dry masses;
- per-manoeuvre mass ledger;
- orbiter propellant, lander propellant, and total propellant;
- launch wet mass and overall mass ratio;
- completeness status plus missing-input messages;
- assumption/version identifier, initially `hesperos_payload_scaled_v1`.

## 12. Workbook defects and deliberate corrections

The following workbook behaviours must not be reproduced:

- Orbiter and lander totals in `Dry Mass` omit their instrument rows.
- Orbiter pointing-control mass adds the lander pointing-control total, then the lander also counts it.
- The `Structure` result is disconnected from dry-mass aggregation while a separate 20% structure
  allowance is used.
- Several component total rows cover ranges beyond the displayed component table.
- Some propulsion manoeuvre rows reference the following row's delta-v, creating off-by-one coupling.
- Standard gravity is rounded to `9.8 m/s²` instead of using the project constant.
- Empty propulsion inputs cause `#DIV/0!`; Python must raise a clear validation error instead.
- The workbook labels panel mass with `kg/m²` although the computed quantity is kg.
- The workbook is a generic solar-power template; it does not establish a Saturn/Titan power-source
  architecture.

## 13. Validation and regression requirements

Before UI integration, tests shall prove:

- exact reproduction of the Hesperos subsystem masses from a `271.2 kg` payload before the separate
  system-level margin;
- coefficient scaling and independent payload power/data summation;
- scenario switching and worst-case selection;
- battery energy, battery mass, recharge power, and optional solar inverse-square scaling;
- exact structure/mechanisms, system-margin, and payload inclusion rules;
- no orbiter/lander subsystem double counting;
- correct carried-lander's mass before separation and absence of it afterwards;
- a two-burn reverse rocket-equation result against a hand-calculated reference;
- distinct Isp values are applied to the correct burns;
- propulsion dry mass and propellant converge for a feasible reference case;
- an infeasible high-delta-v chemical case raises `MassArchitectureInfeasibleError`;
- zero delta-v consumes zero propellant;
- invalid Isp, duration, distance, fraction, mass, power, and non-finite values fail clearly;
- the current trajectory regression values remain unchanged;
- the workbook's blank template returns `incomplete`, never a scientifically meaningful zero result.

No nominal mass or power regression value is declared from the attached workbook: its populated
values are zero and its wet-mass cells contain division errors. A numerical baseline must be added
only after the component catalogues and power-source architecture have been supplied and reviewed.

## 14. Recommended implementation boundary

Implement the model in a new pure module such as `mission/mass_model.py`. Keep `mission/sizing.py` as
the existing preliminary payload-scaling API until the new engine is regression-tested. Add an
adapter from `MissionDeltaVBudget` only after the pure mass tests pass. Streamlit integration comes
last and must label incomplete inputs rather than substituting zero.
