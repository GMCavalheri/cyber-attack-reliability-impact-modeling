# Lesson 2 · Describing an attack by what it does

> A reliability engineer does not need to know *how* a transceiver fails to model it. A
> failure rate, a repair time and the place of the transceiver in the structure are enough.
> This lesson does the same for cyber attacks. Each scenario is written as an **effect** on
> the system's function, with an arrival rate, a duration and a detection-and-recovery time.
> That is exactly the shape a reliability model can consume, and it is also the level at which
> a public, ethical project should work.

**Code:** [`src/cyberrel/attack_scenario_library/`](../../src/cyberrel/attack_scenario_library/) ·
**Data:** [`attack_scenarios.csv`](../../src/cyberrel/data/attack_scenarios.csv) ·
**Tests:** [`tests/test_attack_scenarios.py`](../../tests/test_attack_scenarios.py) ·
**Results:** [`validation/results/scenarios.md`](../../validation/results/scenarios.md) ·
**Scope:** [`docs/scope.md`](../scope.md) ·
**Previous:** [Lesson 1](01-one-language-for-failure.md) ·
**Next:** [Lesson 3](03-a-cyber-attack-as-a-failure-event.md)

## Learning objectives

1. Explain why an effect-level description is both sufficient for reliability analysis and
   the right boundary for public work.
2. Classify an attack's effect as loss of availability, integrity or timeliness, and say how
   each one defeats a system function.
3. Compute the expected length of an attack episode from its duration, detection time and
   recovery time, for transient and persistent effects.
4. Explain why scenarios target a *group* of components, and what "common mode" means here.
5. Use MITRE ATT&CK for ICS as a vocabulary without turning a model into a playbook.

---

## 1. Why the effect level

Cyber-Informed Engineering starts from consequences. The first of its twelve principles in
INL's implementation guide is *consequence-focused design*: decide which functions must be
assured and which outcomes must not happen, before anything else. For a reliability model
the consequence is already defined: the function "trusted navigation data reaches the
mission computer" is up or down. All an attack has to tell the model is:

* **what** it does to the function (which part of the system it makes unusable, and in which
  way),
* **how often** it starts, **how long** the adversary sustains it, and
* **how long** the defenders take to notice it and to restore the function.

Nothing about the attack's technique enters the arithmetic, so leaving it out costs nothing
analytically. It also keeps the project publishable: no vulnerabilities, procedures or
tooling, only effects and times ([`scope.md`](../scope.md)).

## 2. Three ways to defeat a data function

Data that a function depends on can be lost in three ways, and the library has one effect
kind for each:

| effect | what the function sees | example in the library | reliability analogue |
|---|---|---|---|
| **denial** | no data | `bus_flood_dos`: a bus node floods both channels | an outage |
| **integrity** | wrong data | `gnss_spoofing`, `false_nav_injection` | an undetected failure |
| **delay** | late data | `message_delay_replay`: messages arrive 80 ms late | a timing failure |

**Integrity** is the dangerous one. Missing data are noticed immediately; wrong data look
like data. The function is called *trusted* navigation data, so wrong data that are accepted
count as a loss of the function, just as a hazardously misleading output does in avionics
integrity analysis. An **integrity monitor** (a cross-check between sources, or plausibility
checks on messages) catches a fraction of these episodes at onset, `catch_probability`. A
caught episode is rejected: the function continues on the remaining sources, degraded but up.
A missed one is used until someone detects it.

**Delay** is a threshold effect. The mission computer needs navigation data within a deadline
(50 ms in the library, an illustrative value). Added latency below the deadline costs margin
but not the function. Above it, every late message is as useless as a missing one.

## 3. Anatomy of an episode

An attack starts an **episode**. Let $D$ be how long the adversary sustains the effect, and
$T_d$ and $T_r$ the times to detect it and to recover. Once the defenders have detected and
responded, the effect is over. Two cases:

* **Transient** effect (flooding, delaying): it stops when the adversary stops *or* when the
  response completes, whichever comes first. Its length is $\min(D, T_d + T_r)$.
* **Persistent** effect (a corrupted navigation solution): even after the adversary stops,
  the damage stays until someone notices and re-validates. Its length is $T_d + T_r$.

For the expected length we need $E[\min(D, c)]$ with $c = T_d + T_r$. For any non-negative
$D$, $E[\min(D, c)] = \int_0^c P(D > t) dt$, so for exponential $D$ with mean $m$

```math
E[\min(D, c)] = \int_0^c e^{-t/m}\, dt = m \bigl(1 - e^{-c/m}\bigr).
```

Check against the results table:

* `bus_flood_dos` has $m = 2$ h and $c = 0.25 + 1 = 1.25$ h, so
  $2(1 - e^{-0.625}) = 0.931$ h. The table's sampled mean is 0.9306 h.
* `message_delay_replay` has $m = 3$ h and $c = 2$ h, so $3(1 - e^{-2/3}) = 1.459$ h. The
  sampled mean is 1.459 h.

Two properties will carry the rest of the project:

* The episode length is **monotone non-decreasing** in $D$, $T_d$ and $T_r$. A longer
  attack or a slower response never shortens an outage. A Hypothesis test checks this over
  random parameters.
* **Faster response caps the damage.** However long the adversary could sustain a transient
  effect, the outage never exceeds $T_d + T_r$. This is the lever Lesson 5 prices.

### Integrity episodes split in two

An integrity episode is *caught* with probability $q$ and degrades the function for $D$ (the
spoof lasts, but it is being rejected). With probability $1 - q$ it is *missed* and denies the
function for the persistent length $T_d + T_r$. For `gnss_spoofing` ($q = 0.9$, CPS-02's
missed-detection probability of 0.1):

* the expected denial per episode is $0.1 \times 2.5 = 0.25$ h;
* the expected degradation per episode is $0.9 \times 1.0 = 0.9$ h.

The sampled shares (0.0995 missed, mean lengths 2.5 h and 1.0 h) match.

## 4. Common mode: attacks target groups

A scenario targets a **component group**, not a unit. `bus_flood_dos` denies the group
`data_bus`, which in the baseline is channels A and B *together*. That is the point of
flooding a shared bus: every channel carries the same traffic. Physical failures of the two
channels are independent, and that is what makes the second channel worth having. A cyber
denial takes both down at once, so it is a **common-mode** event.

Defining the target as a group keeps this true when the architecture changes. Add a third
channel (`navigation_system(bus_channels=3)`) and the scenario still denies all three. Lesson 3
shows what that does to the value of redundancy.

## 5. ATT&CK for ICS as vocabulary

Each scenario carries the MITRE ATT&CK for ICS technique whose *effect* it represents,
checked on attack.mitre.org:

* T0814 *Denial of Service* for the bus flood;
* T0856 *Spoof Reporting Message* for injected navigation messages;
* T0830 *Adversary-in-the-Middle* for delay and replay (an adversary in the middle can block
  or modify traffic, the closest listed technique).

GNSS spoofing is a radio-frequency effect with no ICS technique, and the library claims none.
The tags help a security reader place each scenario. The model never uses them.

## 6. Code walkthrough

```python
import numpy as np

from cyberrel.attack_scenario_library import load_scenarios

lib = load_scenarios()  # four scenarios from data/attack_scenarios.csv
dos = lib["bus_flood_dos"]
print(dos.kind, dos.target_group, dos.rate_per_hour, dos.response_time)  # denial, data_bus, ...
deny, length = dos.sample_episodes(np.random.default_rng(0), 5)
print(deny, length)  # every episode denies; each lasts min(D, 1.25 h)

slower = dos.with_changes(time_to_detect=2.0)  # a sensitivity case
print(lib["message_delay_replay"].with_changes(added_latency_ms=40).deny_probability)  # 0.0
```

* `AttackScenario` validates itself. Only integrity effects can be caught at onset, only
  delay effects have a latency and a deadline, and every time is non-negative.
* `sample_episodes` returns, for each episode, whether it denies the target and how long it
  lasts (deny length, or degrade length for caught integrity episodes).
* `check_targets` refuses a scenario whose group the system does not have.

## Exercises

1. A denial attack is sustained for an exponential time with mean 2 h. Detection takes 0.25 h
   and recovery 0.25 h. What is the expected outage? What would it be with no response at all?
2. Show that a persistent episode is never shorter than the transient one with the same
   parameters.
3. `gnss_spoofing` has $q = 0.9$. What is the expected denial time per episode if a better
   cross-check raises $q$ to 0.99? By what factor did it fall?
4. The delay scenario's added latency drops from 80 ms to 45 ms. What happens to its denial
   probability, and what kind of function is $P(\text{deny})$ of the latency?
5. Why would it be wrong to model `bus_flood_dos` as an attack on `bus_ch_a` alone?
6. Describe, at the effect level only, a scenario in which the mission computer's software is
   made unusable until it is reloaded (4 h). Give its kind, target group and whether it is
   persistent.

### Solutions

1. $c = 0.5$ h: $2(1 - e^{-0.25}) = 0.442$ h. With no response the outage lasts as long as the
   adversary sustains it, with mean 2 h. The response cuts the expected outage by 78 %.
2. The transient length is $\min(D, T_d + T_r) \le T_d + T_r$, which is the persistent length.
3. $0.01 \times 2.5 = 0.025$ h, a tenfold fall. The missed-detection probability is what
   matters, and it fell from 0.1 to 0.01.
4. 45 ms is below the 50 ms deadline, so $P(\text{deny}) = 0$, and episodes only degrade. As a
   function of latency $L$, $P(\text{deny})$ is a step: 0 for $L \le 50$ ms and 1 above. It is
   monotone but not continuous.
5. Channel B would keep delivering, so the model would credit redundancy against an attack
   that, by its nature (flooding a shared medium), defeats both channels at once. It would
   understate the impact.
6. Kind: denial. Target group: `mission_computer`. Persistent: yes, because the function does
   not return when the adversary stops, only after the reload, so the outage is
   $T_d + 4$ h. This is a description of an effect, with no method.

## References

* V. L. Wright *et al.*, *Cyber-Informed Engineering Implementation Guide*, Idaho National
  Laboratory, INL/RPT-23-74072, 2023 (the twelve CIE principles; principle 1,
  consequence-focused design).
* U.S. Department of Energy, *National Cyber-Informed Engineering Strategy*, June 2022.
* MITRE ATT&CK for ICS, <https://attack.mitre.org/techniques/ics/>: T0814, T0830, T0856
  (checked 2026-11-15).
* S. M. Ross, *Introduction to Probability Models*, 11th ed., Academic Press, 2014 (expectation
  of a non-negative variable as the integral of its survival function).
