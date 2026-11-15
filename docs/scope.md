# Scope and modelling boundaries

This repository is a **methodology and software** project. Everything in it is meant to be safe
to publish, and these rules keep it that way.

## What is modelled

* **A synthetic system.** The navigation chain feeding a mission computer is a generic,
  defense-*representative* architecture, shared with CPS-02
  (GMCavalheri/cyber-physical-rbd-attack-trees). It does not describe any real platform,
  product, operator or programme, and none of its numbers come from one.
* **Physical failures** through constant failure rates and repair-time distributions. Every
  value is a round, plausible assumption, stated row by row in
  [`system_parameters.csv`](../src/cyberrel/data/system_parameters.csv). The failure rates
  are CPS-02's, so the two projects analyse the same system.
* **Cyber attacks at the effect level only.** A scenario says *what the attack does to the
  system's function*: the data bus stops delivering messages, the navigation units deliver
  false positions, or messages arrive late. It also says how often that happens, how long it
  lasts, and how long the defenders take to detect and recover. It never says *how* to do it:
  no vulnerabilities, exploit procedures, tools, protocol details or configurations. The
  scenarios are in [`attack_scenarios.csv`](../src/cyberrel/data/attack_scenarios.csv).

## Public sources only

* **Cyber-Informed Engineering (CIE).** The U.S. Department of Energy's *National
  Cyber-Informed Engineering Strategy* (June 2022) and Idaho National Laboratory's *Cyber-
  Informed Engineering Implementation Guide* (INL/RPT-23-74072, 2023), with its twelve
  principles. [`report.md`](report.md) maps the project onto them.
* **MITRE ATT&CK for ICS**, used only as a **vocabulary**. A scenario carries the ID of the
  technique whose effect it represents (T0814 Denial of Service, T0856 Spoof Reporting
  Message, T0830 Adversary-in-the-Middle), with the names checked on
  <https://attack.mitre.org/techniques/ics/> on 2026-11-15. The tests keep the list of IDs.
  GNSS spoofing is a radio-frequency effect, and no ICS technique is claimed for it.
* **Public readiness definitions.** FMC, PMC, MC and NMC follow U.S. GAO reports GAO-03-300
  and GAO-23-106217.
* **Textbooks and peer-reviewed papers** on reliability and on quantitative security
  modelling, cited in the lessons and in [`related-work.md`](related-work.md).

## How to read the numbers

* Physical metrics are only as good as the failure rates and repair times, and those are
  assumptions.
* Attack rates, durations and response times are **illustrative assumptions**, chosen so
  that the scenarios differ in instructive ways. They are not threat intelligence or field
  statistics, and no availability or MC rate in this repository is a forecast for any real
  system.
* The results that carry over to real systems are **structural**:
  * a common-mode cyber effect is not diluted by redundancy;
  * detection and recovery time sets the outage length;
  * the ranking of scenarios and mitigations moves predictably with the parameters.
* Every result in [`validation/results/`](../validation/results/) is reproducible from the two
  parameter tables, so anyone can replace the assumptions with their own and rerun.

## Out of scope

* Real system data, classified or export-controlled information, or anything obtained under a
  non-disclosure agreement.
* Offensive tooling, exploit development, or guidance for attacking any system.
