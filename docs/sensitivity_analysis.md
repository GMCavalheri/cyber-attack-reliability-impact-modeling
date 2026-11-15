# Sensitivity analysis

Code: [`src/cyberrel/sensitivity_analysis/`](../src/cyberrel/sensitivity_analysis/) ·
Lesson: [Lesson 5](lessons/05-where-mitigation-money-matters.md) ·
Tests: [`tests/test_sensitivity.py`](../tests/test_sensitivity.py)

## Designs

A `Design` holds redundancy and defender-side changes:

* redundancy: `egi_units`, `bus_channels`, `mission_computers`;
* `detect_scale` and `recover_scale`, multipliers on every scenario's response times;
* `rate_scale`, on every attack rate;
* `miss_scale`, on the missed-detection probability of integrity effects;
* `deadline_ms`, which replaces the delay scenarios' deadline.

`Design.evaluate` returns the exact combined steady state.

## Views

* `redundancy_detection_grid` gives exact metrics over the redundancy and the
  detection-multiplier axes. The tests check that every grid point satisfies
  $A = A_{\text{physical}} \prod_s (1 - P_s(\text{deny}))$, since every library scenario denies a
  whole necessary group.
* `tornado` scales one parameter at a time to × (1 − f) and × (1 + f): attack rates,
  durations, response times, miss probabilities, component failure rates and repair times.
  Bars are sorted by swing. A known artifact: for a persistent integrity scenario, a longer
  sustained duration only lengthens caught (degrading) episodes, which delays the next attack
  and slightly *reduces* denials. The test names this exception.
* `evaluate_mitigations` compares eight candidate changes (`DEFAULT_MITIGATIONS`) by
  unavailability removed, MTBF gain and FMC change. Costs are deliberately absent, because
  they are programme-specific.
