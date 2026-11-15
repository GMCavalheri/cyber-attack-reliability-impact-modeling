# PLAN.md — CPS-01: Cyber Attack Impact Modeling on Reliability Metrics

## Overview
A foundational project in cyber-physical reliability engineering: simulating how cyber attacks against a defense-representative cyber-physical system (a networked sensor/control architecture, generic and synthetic) propagate into degradation of classical reliability metrics — MTBF, availability, dispatch/mission readiness — using the reliability frameworks already built across the portfolio (Fleet Reliability Dashboard, Mission Capable Rate Analysis).

## Objective
Build a simulation framework where injected cyber attack scenarios (denial of service on a data bus, sensor spoofing, message injection/delay) produce measurable, quantifiable degradation in standard reliability metrics — establishing a common quantitative language between cybersecurity events and reliability engineering outcomes, which today are usually analyzed by two separate teams using two separate vocabularies.

## Why This Project
This is the entry point into the field of Cyber-Informed Engineering (CIE), a framework formalized by Idaho National Laboratory and adopted as a U.S. national strategy since 2022. CIE's core premise is that cybersecurity should be engineered in from the design stage using the same rigor as physical safety/reliability — and the first step toward that is being able to *measure* cyber impact in the same units engineers already use for physical failure (MTBF, availability). Almost no reliability engineers build this bridge quantitatively; almost no cybersecurity engineers think in MTBF/availability terms. This project builds the bridge.

## Knowledge Covered
1. **Generic Cyber-Physical System Model**: define a simplified, synthetic networked system representative of a defense sensor/control architecture (e.g., a set of sensors feeding a control/decision node over a shared data bus), with a defined physical reliability model (component failure rates, redundancy) as a baseline.
2. **Attack Scenario Library**: define a library of representative cyber attack scenarios and their direct technical effect on the system (denial of service → data unavailability for a duration; spoofing → corrupted sensor readings; message injection/replay → delayed or duplicated commands) — conceptual/effect-level modeling, not exploit development.
3. **Attack-to-Reliability-Metric Translation**: implement the core contribution — a simulation layer that translates each attack scenario's technical effect into its impact on MTBF, availability, and mission-capable-rate-style metrics, exactly as if it were a physical failure event, and compares magnitude of impact across attack types.
4. **Combined Physical + Cyber Threat Simulation**: run Monte Carlo simulations combining both physical failure events and cyber attack events on the same system model, producing a combined reliability metric that reflects the *total* risk picture rather than treating cyber and physical failure separately.
5. **Sensitivity to Redundancy and Detection Time**: analyze how system redundancy and time-to-detect-and-recover from a cyber event affect the resulting metric degradation — directly informing where mitigation investment matters most.

## Prerequisites / Background
- The MTBF/MTTR/availability methodology from the Fleet Reliability Dashboard project
- The Mission Capable Rate framework from the Mission Capable Rate Analysis project
- Basic cybersecurity concepts: denial of service, spoofing, message injection/replay (conceptual level, not offensive tooling)

## Data / Dataset
- **Synthetic system model**: a generic networked sensor/control architecture with physical reliability parameters (failure rates, repair times) reused from the portfolio's reliability modules.
- **Attack effect library**: effect-level scenarios (denial duration, corruption magnitude, delay), defined from public literature and, optionally, MITRE ATT&CK for ICS.
- **Simulation outputs**: Monte Carlo runs producing reliability metrics with and without attacks.
- No real system configurations, vulnerabilities, or non-public data are used.

## Tech Stack
- Python, NumPy, SciPy (Monte Carlo simulation)
- Reuses the reliability metric calculation modules from the Fleet Reliability Dashboard and Mission Capable Rate Analysis projects
- Matplotlib/Plotly for combined risk visualization, attack-scenario impact comparison charts

## Repository Structure
```
cyber-attack-reliability-impact-modeling/
  src/
    system_model/
    attack_scenario_library/
    attack_to_metric_translation/
    combined_monte_carlo_simulation/
    sensitivity_analysis/
  external/                 # reused reliability metric modules from prior projects
  docs/                     # scope notes: conceptual/effect-level modeling only
  notebooks/
  tests/
```

## Execution Plan
- [x] **Phase 1 — System model and physical baseline**: define the synthetic cyber-physical system and its physical reliability baseline (reusing prior modules).
- [x] **Phase 2 — Attack scenario library**: define representative attack scenarios at the effect level (duration of denial, magnitude of data corruption, delay introduced).
- [ ] **Phase 3 — Attack-to-metric translation**: implement the simulation layer converting attack effects into MTBF/availability/mission-capable-rate impact.
- [ ] **Phase 4 — Combined simulation**: run Monte Carlo simulation combining physical and cyber events, produce combined risk metrics.
- [ ] **Phase 5 — Sensitivity analysis**: analyze redundancy and detection-time sensitivity.
- [ ] **Phase 6 — Documentation and publishing**: written explanation connecting the methodology explicitly to the Cyber-Informed Engineering framework, with clear sourcing.

## Validation Strategy
- Physical-only baseline validated for consistency against the original Fleet Reliability Dashboard/Mission Capable Rate Analysis methodology (should reduce to the same results with zero cyber attack scenarios).
- Attack impact magnitudes checked for directional sensibility (longer denial-of-service duration → larger availability impact, monotonically).

## Deliverables
- Public repository with a documented attack-to-reliability-metric simulation framework
- A written report explicitly framed around Cyber-Informed Engineering methodology
- Visualizations: combined risk metrics, attack scenario impact comparison, redundancy/detection-time sensitivity

## Portfolio Differentiators
- Directly and explicitly aligned with a real, named, institutionally-backed framework (CIE/INL), rather than an ad hoc "cybersecurity meets reliability" idea — this is a significant credibility signal.
- Establishes the common metric language (MTBF/availability) that the rest of the cyber-physical reliability project series builds on.

## Possible Extensions
- Extend the attack scenario library using publicly documented MITRE ATT&CK for ICS tactics/techniques (at the conceptual/effect level) for broader realism
- Feed combined risk output into the Preventive Maintenance Optimization project as an additional risk input alongside physical failure risk
