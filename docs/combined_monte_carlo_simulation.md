# Combined Monte Carlo simulation

Code: [`src/cyberrel/combined_monte_carlo_simulation/`](../src/cyberrel/combined_monte_carlo_simulation/) ·
Lesson: [Lesson 4](lessons/04-the-total-risk-picture.md) ·
Tests: [`tests/test_simulation.py`](../tests/test_simulation.py)

## Algorithm (`simulate_platform`)

1. **Physical timelines.** `down_intervals` draws the alternating up and down periods of each
   component, in vectorised batches, starting up at time 0.
2. **Attack timelines.** `episode_timeline` draws each scenario's episodes, starting idle.
3. **Segments.** All interval boundaries are sorted. On each segment between consecutive
   boundaries every state is constant, and is found by binary search at the midpoint. The
   function is evaluated with the same `function_up` as the closed form, and classified with
   the same `classify`.
4. **Log.** Maximal down runs become `Outage` records with cause `physical`, `cyber` or
   `both`.

There is no time step: the result is exact for each sample path.

## Streams and reductions

Each process uses `SeedSequence(seed, spawn_key=(platform, kind, index))`, so adding a scenario
never changes another process's draws. Two tests rely on this:

* zero-rate scenarios leave the log identical;
* in an attacked run, the physical-alone down hours equal the physical-only run's down hours,
  platform by platform.

## Fleet and intervals

`simulate_fleet` runs independent platforms. `FleetResult` provides:

* the outage log, and dashboard KPIs from it (optionally by cause);
* fleet status hours;
* `estimate(metric)`, a Student-$t$ interval across platforms for availability, failure
  frequency or any status share.

The tests check 99.9 % intervals against the exact steady state, with and without attacks.
