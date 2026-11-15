# Metrics: MTBF, MTTR, availability and readiness

Code: [`src/cyberrel/metrics/`](../src/cyberrel/metrics/) ·
Lessons: [Lesson 1](lessons/01-one-language-for-failure.md),
[Lesson 4](lessons/04-the-total-risk-picture.md) ·
Tests: [`tests/test_metrics.py`](../tests/test_metrics.py)

## Reliability KPIs from a log (`reliability.py`)

These are the Fleet Reliability Dashboard's definitions:

* MTBF is operating hours over the number of failures.
* MTTR is the mean repair duration.
* $A = \mathrm{MTBF}/(\mathrm{MTBF} + \mathrm{MTTR})$.

`reliability_kpis` reproduces the dashboard's own known-answer fixture. `kpis_from_outages`
applies the formulas to a list of `Outage(platform, start, end, cause)` records over a span of
possessed hours. Operating hours are taken as the up time, which makes $A$ exactly the fraction
of time up. The `causes` argument gives a by-cause view: the failure count and MTTR use only
the selected outages, and the operating hours still exclude all down time.

## Readiness (`readiness.py`)

These are the public definitions (GAO-03-300, GAO-23-106217):

* FMC means able to do all missions.
* PMC means able to do at least one mission, but not all.
* MC = FMC + PMC.
* Each rate is hours in the status over possessed hours.

The model's mapping, a stated choice rather than a reporting rule:

| model state | status |
|---|---|
| everything up, no cyber effect | FMC |
| function up, something degraded | PMC |
| function down, physical failures alone would cause it | NMC, maintenance |
| function down, cyber effects alone would cause it | NMC, cyber |
| function down otherwise (both suffice, or only the combination does) | NMC, both |

`classify` maps states or simulated intervals to these five statuses, and `status_hours` sums
hours or probabilities by status. The cyber split is an attribution added by this project,
not an official status code. Spares are assumed to be available, so there is no NMCS.
