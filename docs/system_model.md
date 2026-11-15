# System model and physical baseline

Code: [`src/cyberrel/system_model/`](../src/cyberrel/system_model/) ·
Lesson: [Lesson 1](lessons/01-one-language-for-failure.md) ·
Tests: [`tests/test_system_model.py`](../tests/test_system_model.py),
[`tests/test_cpsrbd_crosscheck.py`](../tests/test_cpsrbd_crosscheck.py)

## Components

A `Component` has a constant failure rate $\lambda$ (exponential up times, so
$\mathrm{MTBF} = 1/\lambda$), a `RepairDistribution` (lognormal by default, exponential or
fixed, parameterised by its mean), and a redundancy `group`. Each component is an alternating
renewal process, and by the renewal-reward theorem

```math
A_i = \frac{\mathrm{MTBF}_i}{\mathrm{MTBF}_i + \mathrm{MTTR}_i}
```

for any repair distribution (Rausand and Høyland, 2004, ch. 7).

## Structures

`KOutOfN(k, children)` with the shorthands `Series` (n-of-n) and `Parallel` (1-of-n) builds
a success-logic structure whose leaves are component names. A name may appear more than once,
so the structure function $\phi$ is coherent but not necessarily series-parallel.
`structure.evaluate` applies $\phi$ to NumPy boolean arrays, one state per element.

## Exact results (`closed_form.py`)

All exact results enumerate the $2^n$ component states (`enumerate_states`), weight them by
independent up-probabilities (`state_weights`) and sum where $\phi = 1$ (`works_probability`):

* steady-state availability, with $p_i = A_i$;
* mission reliability over $t$ hours with no repair, with $p_i = e^{-\lambda_i t}$;
* Birnbaum importance, $I_B(i) = P(\phi(1_i, X) = 1) - P(\phi(0_i, X) = 1)$;
* the system failure frequency, mean up time and mean down time:

```math
\omega = \sum_i \nu_i \, I_B(i), \quad \nu_i = \frac{1}{\mathrm{MTBF}_i + \mathrm{MTTR}_i},
\qquad \mathrm{MTBF}_{\text{sys}} = \frac{A}{\omega}, \qquad \mathrm{MDT}_{\text{sys}} = \frac{1 - A}{\omega}
```

* the FMC / PMC / NMC probabilities (`steady_state_status`).

## The navigation system

`navigation_system(egi_units=2, bus_channels=2, mission_computers=1)` builds the CPS-02
architecture from `data/system_parameters.csv`:

* two GNSS/INS units, each in series with its power bus;
* a dual-channel data bus;
* the mission computer, fed from both power buses.

The power buses are shared, so enumeration (or conditioning on them) is required. Extra units
copy the parameters of unit 1; extra mission computers work in parallel.

## Validation

* Closed forms for series, parallel and k-of-n (Hypothesis over random sizes).
* The Markov result MDT = MTTR/2 for a repairable parallel pair.
* An independent conditioning oracle for the navigation system's availability and mission
  reliability.
* Agreement to $10^{-12}$ with CPS-02 (`cpsrbd` v1.0.0), which computes the same physical
  mission unreliability through a failure-logic DAG.
