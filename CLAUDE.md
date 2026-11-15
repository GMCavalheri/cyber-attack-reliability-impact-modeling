# CLAUDE.md

Cyber attacks measured in the units of reliability engineering. A synthetic, defense-
representative cyber-physical system (sensors feeding a mission computer over a shared data
bus) is simulated under physical failures and effect-level cyber attack scenarios, and the
result is reported as MTBF, availability and mission-capable (MC) rate, following the
Cyber-Informed Engineering (CIE) idea that cyber risk should be engineered with the same rigor,
and in the same units, as physical failure.
Plan: `CPS-01-cyber-attack-reliability-impact-modeling-PLAN.md` (tick the phase checkboxes as
phases land). The synthetic system is the one in CPS-02
(`GMCavalheri/cyber-physical-rbd-attack-trees`, package `cpsrbd`); keep the two consistent.

## Commands
- `uv sync` — install (Python ≥ 3.11; CI runs 3.11, 3.12 and 3.13)
- `uv run pytest --cov` — tests with the 90 % coverage gate
- `uv run ruff check .` and `uv run ruff format --check .` — lint/format. Ruff also formats
  the ```python blocks inside Markdown, so run it after editing docs too
- `uv run mypy` — strict type check of `src/`
- `uv run python validation/<script>.py` — regenerate one phase's tables
  (`validation/results/`) and figures (`docs/figures/`); `validation/run_all.py` runs them all
- `uv run python notebooks/build_notebooks.py` — regenerate and execute the notebooks

## Layout
- `src/cyberrel/` — single package; subpackages mirror the plan:
  `system_model` (components, k-of-n groups, the navigation system, closed forms), `metrics`
  (MTBF/MTTR/availability from an event log, MC/FMC/PMC/NMC), `attack_scenario_library`
  (effect-level scenarios), `attack_to_metric_translation` (attacks as outage events, closed
  forms), `combined_monte_carlo_simulation` (discrete-event fleet simulation),
  `sensitivity_analysis`; plus `plotting.py`.
- `src/cyberrel/data/` — system and scenario parameters (CSV); every value is labelled an
  assumption or carries its source.
- `tests/` — pytest + Hypothesis. `validation/` — one script per phase, `results/` tables.
- `docs/` — theory note per module, `scope.md`, `related-work.md`, `report.md`;
  `docs/lessons/` is the course (keep its numbers in sync with `validation/results/`).
  `notebooks/` — one executed demo per lesson.

## Conventions
- Time is in hours. Physical failures are exponential (constant rate λ); repairs have a mean
  (MTTR) and a stated distribution. Components fail and are repaired independently unless a
  cyber scenario says otherwise.
- A cyber attack is modelled by its **effect** on the system (which function or components
  it makes unavailable or untrustworthy, for how long, and how long detection and recovery
  take), and enters the same event log as a physical failure. Never present an attack rate as
  field data: it is an explicit, illustrative assumption.
- Simulations take a seeded `numpy.random.Generator`; with no attack scenarios the simulation
  must reproduce the physical-only run exactly (same seed, same event log).
- Exact results (closed forms) are compared with tolerance 1e-12; Monte Carlo against its own
  confidence interval.

## Scope (public repo)
- Synthetic system, public methodology (INL CIE/CCE, DOE National CIE Strategy, MITRE ATT&CK
  for ICS, public USAF/GAO readiness definitions) only. Attacks are modelled at the **effect
  level**, never as exploit procedures. See `docs/scope.md`.
- Never mention the author's employer or day job in any file, commit message or doc.

## Docs (GitHub-rendered math)
- Display equations go in ```` ```math ```` fences (no Markdown processing inside).
- Inline `$...$` is processed as Markdown first: no `\,` or `\;`, no `\\` row breaks, and no
  `_` right after `}` `)` `]`. `tests/test_docs.py` guards this.

## Testing rules
- Every test asserts against a closed-form result, an independent oracle (CPS-02's `cpsrbd`,
  exhaustive enumeration) or a cited published value; name the source in a comment.
- Never loosen a tolerance to make a failing test pass without explaining why.
- Properties that must hold for every parameter set (monotonicity in attack duration and
  detection time, zero attacks = physical baseline) are Hypothesis tests.

## Workflow
- Commit small logical changes directly to `main`; push after ruff, mypy and pytest pass,
  each run as its own command (no pipes: a pipe hides the exit code). Stage explicit paths.
- Each phase lands as code + tests, then validation results, then its lesson in
  `docs/lessons/` as a separate commit. Confirm CI is green after each push.
