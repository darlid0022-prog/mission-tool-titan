# Open questions

## Maximum feasible single-stage delta-v (3,833.463 m/s)

`maximum_feasible_delta_v_m_s` in the isolated single-stage feasibility study
(`mission/feasibility_check.py:52`, model version `hesperos_payload_scaled_v1`
in `mission/mass_model.py:10`) is the single most structural number the
isolated feasibility study produces: it drives the 3.269× exceedance factor
and therefore the study's infeasibility finding. It is not auditable as it
stands.

It follows from `ParametricBusCoefficients` (`mission/mass_model.py:63-`):
`propulsion_dry_per_propellant` and `system_margin_fraction`, combined into a
70.5% allowable propellant fraction at 320 s Isp. `hesperos_payload_scaled_v1`
is a version label, not a calibration source.

Requested before this number can be trusted for a feasibility conclusion:

- documented structural mass basis (bus structure, harness, margins) behind
  `propulsion_dry_per_propellant` and `system_margin_fraction`;
- tank/propellant-system mass assumptions;
- the calibration reference ("Hesperos") itself: what vehicle or design this
  was fit against, and where that source is recorded;
- the complete derivation connecting those assumptions to 3,833.463 m/s, so
  the number can be reproduced independently of `mission/mass_model.py`.

Do not modify, recompute, or reuse this value differently until this
derivation exists and is reviewed.

## Second Venus flyby demonstrator

`pages/gravity_assists.py` renders three isolated flyby demonstrators (Venus,
Earth, Jupiter), one call each to
`mission.gravity_assist.compute_*_flyby_demonstration()`. The reference
VVEJGA architecture (`mission/gravity_assist.py`, real Cassini chain) flies
two Venus flybys, and the underlying model already supports both (see the
first/second Venus flyby legs in `mission/gravity_assist.py:471-541`). The
demonstrator page shows only one. Confirm whether a second, independent Venus
flyby demonstrator should be added, or whether one demonstrator per body is
the intended scope.

## Saturn & Titan studies page shared between two menus — resolved

`pages/saturn_system_studies.py` renders all four of its blocks (the
authoritative connected model plus three legacy/preliminary studies)
unconditionally, and is linked from both *Technical details* and *Isolated
studies* with a `section` query parameter that only changes one explanatory
caption. This is documented as intentional in the file's own header comment,
not a duplication bug — see the wording-and-scope batch report (§1.4) for the
full analysis. **Decision (wording-and-scope follow-up batch, §0): accepted
as-is, no correction.** A single page reachable from two menus is the
intended behavior.

## Display order when entering via Isolated studies

A narrower question survives the decision above: when arriving via
*Isolated studies* (`?section=isolated`), the FIRST block rendered on
`pages/saturn_system_studies.py` is still "Saturn hyperbolic arrival &
capture — authoritative model" — the block that feeds the connected budget.
A reader who followed the *Isolated studies* menu specifically to see
excluded/legacy content sees the connected model first, which cuts against
that menu's own framing. Should the page reorder its blocks based on the
`section` query parameter, or should the page be split so each menu entry
shows only its own content?

## "baseline" naming in the Pareto front

`select_pareto_highlights` (`mission/pareto_plot.py`) names its
locked-minimum-departure-v-infinity point `baseline`. The name alone does
not convey that the selection criterion is minimum departure v∞, not
(for example) minimum delta-v or the literal default scenario. Worth
clarifying the vocabulary — e.g. `locked_departure_baseline` or a docstring
callout at the call sites — so a future reader does not assume it means
"the point currently displayed as the default mission."
