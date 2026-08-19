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

## Saturn & Titan studies page shared between two menus

`pages/saturn_system_studies.py` renders all four of its blocks (the
authoritative connected model plus three legacy/preliminary studies)
unconditionally, and is linked from both *Technical details* and *Isolated
studies* with a `section` query parameter that only changes one explanatory
caption. This is documented as intentional in the file's own header comment,
not a duplication bug — see the wording-and-scope batch report (§1.4) for the
full analysis. Left open pending an explicit decision on whether the two
menu entries should instead show different content.
