# Attack scenario library

Code: [`src/cyberrel/attack_scenario_library/`](../src/cyberrel/attack_scenario_library/) ·
Data: [`attack_scenarios.csv`](../src/cyberrel/data/attack_scenarios.csv) ·
Lesson: [Lesson 2](lessons/02-describing-an-attack-by-what-it-does.md) ·
Scope: [`scope.md`](scope.md) ·
Tests: [`tests/test_attack_scenarios.py`](../tests/test_attack_scenarios.py)

## A scenario is an effect, a frequency and a response

An `AttackScenario` has:

* an `EffectKind`: `DENIAL`, `INTEGRITY` or `DELAY`;
* the component `target_group` it acts on;
* `rate_per_hour`, the arrivals while no episode of the scenario is active;
* `duration`, how long the adversary sustains the effect;
* `time_to_detect` and `time_to_recover`;
* `persistent`, `catch_probability` (integrity effects only), and `added_latency_ms` with
  `deadline_ms` (delay effects only);
* an optional ATT&CK for ICS `technique`, from a verified list.

## Episodes

With $D$ the sustained duration and $c = T_d + T_r$:

| case | denies the function? | length |
|---|---|---|
| denial, transient | yes | $\min(D, c)$ |
| any effect, persistent | as for its kind | $c$ |
| integrity, caught at onset (probability $q$) | no, degrades | $D$ |
| integrity, missed | yes | the transient or persistent rule |
| delay, latency above the deadline | yes | the transient or persistent rule |
| delay, latency within the deadline | no, degrades | the transient or persistent rule |

`sample_episodes` draws episodes. Lengths are monotone non-decreasing in $D$, $T_d$ and $T_r$
(a Hypothesis test checks this). Denials act on the whole target group, so they are
common-mode.

## The library

| scenario | effect | target | ATT&CK for ICS |
|---|---|---|---|
| `bus_flood_dos` | denial, transient | data bus | T0814 Denial of Service |
| `gnss_spoofing` | integrity, persistent, 90 % caught | navigation sources | none (RF domain) |
| `false_nav_injection` | integrity, persistent, 50 % caught | data bus | T0856 Spoof Reporting Message |
| `message_delay_replay` | delay of 80 ms against a 50 ms deadline, transient | data bus | T0830 Adversary-in-the-Middle |

Every rate and time is an illustrative assumption, and every row says so.
