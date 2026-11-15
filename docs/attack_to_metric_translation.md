# Attack-to-metric translation

Code: [`src/cyberrel/attack_to_metric_translation/`](../src/cyberrel/attack_to_metric_translation/) ·
Lesson: [Lesson 3](lessons/03-a-cyber-attack-as-a-failure-event.md) ·
Tests: [`tests/test_translation.py`](../tests/test_translation.py)

## One scenario (`episodes.py`)

Idle periods are $\text{Exp}(\lambda_a)$. An episode denies with probability $p$ (mean length
$L_d$) or degrades (mean $L_g$). By renewal-reward:

```math
C = \frac{1}{\lambda_a} + p L_d + (1 - p) L_g, \quad
P(\text{deny}) = \frac{p L_d}{C}, \quad P(\text{degrade}) = \frac{(1 - p) L_g}{C}, \quad
\nu_a = \frac{p}{C}
```

The equivalent MTBF is $(1 - P(\text{deny}))/\nu_a$ and the equivalent MTTR is $L_d$.
`mean_min` gives $E[\min(D, c)]$ exactly: $m(1 - e^{-c/m})$ for exponential $D$, the
lognormal partial expectation, and $\min(m, c)$ for a fixed $D$. It is tested against
numerical integration. `episode_timeline` samples the process over a horizon.

## Physical and cyber together (`combined.py`)

Components (up or down) and scenarios (idle, degrade or deny) are independent, so the
stationary joint distribution is a product. `joint_states` enumerates it
($2^n \cdot 3^k$ states). While a scenario denies, every component of its target group counts
as down, and `function_up` evaluates $\phi$ on those effective states. `combined_steady_state`
returns the availability, the failure frequency, MTBF and MDT, and the FMC / PMC / NMC-by-cause
probabilities, with

```math
\omega = \sum_i \nu_i \, P(i \text{ critical}) + \sum_s \nu_s \, P(s \text{ critical}).
```

## Translation and ranking (`translation.py`)

`translate` gives a scenario's equivalent MTBF and MTTR and its impact relative to the
physical baseline:

* $\Delta A$, and the added unavailability as a multiple of the physical unavailability;
* the MTBF ratio;
* $\Delta$MC and $\Delta$FMC.

`rank_scenarios` sorts scenarios by any of these. `common_mode_factor` checks the series-block
identity $A_{\text{attacked}} = A_{\text{physical}}(1 - P(\text{deny}))$ for a denial of a
necessary group.

## Validation

* Reduction to the physical baseline to $10^{-12}$.
* The series-block identity for one, two and three bus channels.
* A hand-derived partial-group denial.
* The two-process failure frequency.
* Monte Carlo timelines against the renewal formula.
* Hypothesis monotonicity in duration, detection, recovery and rate, and a step in latency.
