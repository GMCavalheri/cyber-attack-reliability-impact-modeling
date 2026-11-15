# Related work, and what is (and is not) new here

This note places the project among earlier work that measures security in reliability terms,
and states plainly which parts are known and which may be new. Every bibliographic detail
below was checked against the publisher's record or the paper itself (November 2026). The
claims about each work are limited to what its abstract or text says. This is a *targeted*
review, not a systematic one: Section 5 lists what a systematic search would still need to
cover.

## 1. Security measured like reliability: an old idea

* **Littlewood et al. (1993)** proposed *operational* measures of security built on an analogy
  between system failure and security breach. Their key move was to let the attacker's
  **effort** play the role that time plays in reliability, so that security could be stated as
  probabilities such as a mean effort to breach. This project uses the analogy in the other
  direction. It keeps clock time and turns each attack's *effect* into failure-and-repair
  terms.
* **Nicol, Sanders and Trivedi (2004)** surveyed model-based dependability evaluation
  (combinatorial models, Markov and stochastic Petri net models, simulation) and how it was
  being extended to security. They stressed that intentional attacks differ from accidental
  faults. The project's state-based model, renewal arguments and Monte Carlo cross-check sit
  squarely in that tradition.
* **Avizienis, Laprie, Randell and Landwehr (2004)** gave the shared vocabulary: availability
  and integrity are attributes of both dependability and security, and security adds
  confidentiality. The denial and integrity effects in Lesson 2 are attacks on exactly those
  two shared attributes.

## 2. Stochastic models of attack, response and recovery

| work | what is modelled | metric | relation to this project |
|---|---|---|---|
| Madan, Goševa-Popstojanova, Vaidyanathan and Trivedi, *Performance Evaluation* 56, 2004 | attacks and the system's response in an intrusion-tolerant system, as a semi-Markov process | mean time (or effort) to security failure (MTTSF); probabilities of failure by security attribute | Same family: attack and response as a state process with means. MTTSF is an absorbing-state metric; this project uses steady-state renewal metrics (A, MTBF, MDT, MC rate) on a repairable platform. |
| McQueen, Boyer, Flynn and Beitel (INL), *Quality of Protection*, Springer, 2006 | time for an attacker to compromise a visible component, from its known vulnerabilities and the attacker's skill | time-to-compromise (TTC); risk reduction of remediation in a SCADA case study | TTC is an *input*-side quantity: how fast attacks succeed. This project starts after success, at the effect, and measures its consequence on the function. A TTC estimate is one way to set a scenario's arrival rate. |
| LeMay, Ford, Keefe, Sanders and Muehrcke, ADVISE, QEST 2011 (Möbius) | an executable state-based model of system and adversary; the adversary chooses attack steps by looking ahead | model-based security metrics from simulating the adversary; comparison of architecture variants | ADVISE models *how* an adversary progresses, which this project deliberately does not (scope). Both compare architecture variants quantitatively; this project's comparison is in reliability and readiness units. |

## 3. Reliability indices with cyber attacks: power systems got there first

The closest precedent is in **power-system reliability**. **Tang, Liu and Wang (IEEE/PES T&D
2020)** model external and insider attacks on a SCADA system with a semi-Markov process
characterised by mean time-to-compromise. They feed the result into Monte Carlo simulation of
the IEEE RTS-96 test system, and report **loss-of-load probability and expected energy not
supplied** rising as attacks become faster. **Lei, Singh and Sprintson (IEEE Transactions on
Smart Grid 5(5), 2014)** and **Lei's dissertation (Texas A&M, 2016)** build reliability models
of IEC 61850 substation protection systems that include cyber components and cyber-induced
malfunctions in composite reliability evaluation.

So the general move, putting attack processes into a Monte Carlo reliability evaluation and
reading the result as standard reliability indices, **is not new**. It is established for the
electric grid, with that domain's indices (LOLP, EENS).

## 4. Resilience curves and engineering frameworks

* **Bruneau et al. (*Earthquake Spectra* 19(4), 2003)** measure the loss of resilience as the
  degradation in a quality function $Q(t)$ integrated over the time to recovery (their
  Figure 1), with *robustness* and *rapidity* as its two ends. In this project, the denial
  probability per episode and the episode length play those roles. The frequency/duration
  split of Lesson 5 is the same decomposition seen from a reliability engineer's side.
* **Cyber-Informed Engineering** (DOE National CIE Strategy, 2022; INL Implementation Guide,
  INL/RPT-23-74072, 2023) and **CCE** (Bochman and Freeman, CRC Press, 2021) set the frame:
  consequence first, engineered controls, design simplification, planned resilience. They are
  process frameworks with workshops and guiding questions, not quantitative models. This
  project is one quantitative embodiment of the question CIE asks of reliability engineers.
* **DO-326A / ED-202A** (RTCA / EUROCAE, 2014), the airworthiness security process
  specification, assesses each *threat condition* by the severity of its safety effect and the
  level of threat, and judges acceptability against the airworthiness authority's criteria
  (EASA AMC 20-42 gives guidance). It is the aviation analogue of the safety assessment of
  failure conditions, and it is qualitative about likelihood. It does not translate threats into
  fleet reliability or readiness metrics, and it is not meant to.
* **Combined safety and security formalisms** (attack-fault trees, BDMP, STPA-Sec and others)
  are reviewed in CPS-02's related-work note, which this series shares.

## 5. What this project does **not** claim

* That attacks can be modelled as stochastic processes inside availability or reliability
  models. Madan et al. (2004) and the power-system work above already do so.
* That Monte Carlo reliability evaluation with cyber attacks is new. It is established for
  power grids (Tang et al., 2020).
* That the attack rates, durations or response times describe any real system. They are
  illustrative assumptions ([`scope.md`](scope.md)). The ranking of mitigations in Lesson 5
  depends on them, and the structural results do not.
* That the closed forms are new mathematics. Renewal-reward, criticality-based failure
  frequency and common-cause blocks in series are textbook reliability theory (Rausand and
  Høyland, 2004).

## 6. What this project does contribute

| contribution | where | strength of the claim |
|---|---|---|
| **The aviation and defense readiness language.** Attacks translated into the fleet-reliability metrics an airline or air arm already tracks (MTBF, MTTR and availability from an outage log, with the Fleet Reliability Dashboard's own formulas) and into public FMC / PMC / NMC readiness statuses, with NMC time attributed to physical, cyber or both. | `metrics/`, Lessons 1, 3, 4 | The power-system precedent uses grid indices. In the works reviewed, no study expresses cyber effects as MC/FMC rates with a cause split. Moderate, pending the systematic search below. |
| **An effect-level scenario library that maps onto reliability parameters.** Denial, integrity and delay effects with transient/persistent episodes, onset catch probability and a timing deadline, each turned into an equivalent MTBF and MTTR. | `attack_scenario_library/`, Lessons 2–3 | Modest in method, useful as a public, exploit-free interface between security and reliability teams. |
| **Exact steady-state metrics for mixed physical and cyber processes on one structure**, including failure frequency through criticality, validated by an independent discrete-event simulation and an exact sample-path reduction. | `attack_to_metric_translation/`, `combined_monte_carlo_simulation/` | Low novelty in theory, high in verification: two independent computations agree, and the physical baseline matches CPS-02 to $10^{-12}$. |
| **The common-mode result as a proved, tested identity.** A denial of a necessary group acts as one block in series, $A = A_{\text{physical}} \prod_s (1 - P_s)$, so redundancy inside the group has zero value against it. | Lesson 3, `test_translation.py`, `test_sensitivity.py` | Known in spirit (common-cause failures). Making it explicit for cyber effects and showing it numerically for the bus is the practical contribution, and it is the series' bridge to CPS-04. |
| **Mitigations compared on one scale, split into frequency and duration levers.** Detection and recovery leave system MTBF unchanged; hardening and engineered controls raise it; physical redundancy pays only at the physical single point of failure. | `sensitivity_analysis/`, Lesson 5 | A standard reliability decomposition, applied to a mixed portfolio. Useful as a demonstration, not as new theory. |
| **Open, tested, reproducible software and a six-lesson course.** | the repository | Practical, not methodological. |

**Still to search before any claim goes into a paper:**
* defense-readiness modelling literature (RAND and service analyses of MC rates) for any
  cyber-effects treatment;
* the attack-modelling papers that cite Madan et al. (2004) and use steady-state availability
  of repairable systems;
* avionics-specific quantitative security work beyond the process standards.

## References

* A. Avizienis, J.-C. Laprie, B. Randell and C. Landwehr, "Basic concepts and taxonomy of
  dependable and secure computing", *IEEE Transactions on Dependable and Secure Computing*,
  1(1), 2004, pp. 11–33.
* A. A. Bochman and S. Freeman, *Countering Cyber Sabotage: Introducing Consequence-Driven,
  Cyber-Informed Engineering (CCE)*, CRC Press, 2021.
* M. Bruneau, S. E. Chang, R. T. Eguchi, G. C. Lee, T. D. O'Rourke, A. M. Reinhorn, M.
  Shinozuka, K. Tierney, W. A. Wallace and D. von Winterfeldt, "A framework to quantitatively
  assess and enhance the seismic resilience of communities", *Earthquake Spectra*, 19(4), 2003,
  pp. 733–752.
* EASA, AMC 20-42, *Airworthiness information security risk assessment*.
* H. Lei, *Reliability Modeling and Analysis of Cyber Enabled Electric Power Systems*, PhD
  dissertation, Texas A&M University, 2016.
* H. Lei, C. Singh and A. Sprintson, "Reliability modeling and analysis of IEC 61850 based
  substation protection systems", *IEEE Transactions on Smart Grid*, 5(5), 2014,
  pp. 2194–2202.
* E. LeMay, M. D. Ford, K. Keefe, W. H. Sanders and C. Muehrcke, "Model-based security metrics
  using ADversary VIew Security Evaluation (ADVISE)", 8th International Conference on
  Quantitative Evaluation of Systems (QEST), 2011, pp. 191–200.
* B. Littlewood, S. Brocklehurst, N. Fenton, P. Mellor, S. Page, D. Wright, J. Dobson,
  J. McDermid and D. Gollmann, "Towards operational measures of computer security",
  *Journal of Computer Security*, 2(2–3), 1993, pp. 211–229.
* B. B. Madan, K. Goševa-Popstojanova, K. Vaidyanathan and K. S. Trivedi, "A method for
  modeling and quantifying the security attributes of intrusion tolerant systems",
  *Performance Evaluation*, 56(1–4), 2004, pp. 167–186.
* M. A. McQueen, W. F. Boyer, M. A. Flynn and G. A. Beitel, "Time-to-compromise model for cyber
  risk reduction estimation", in *Quality of Protection: Security Measurements and Metrics*,
  Advances in Information Security 23, Springer, 2006, pp. 49–64.
* D. M. Nicol, W. H. Sanders and K. S. Trivedi, "Model-based evaluation: from dependability to
  security", *IEEE Transactions on Dependable and Secure Computing*, 1(1), 2004, pp. 48–64.
* M. Rausand and A. Høyland, *System Reliability Theory*, 2nd ed., Wiley, 2004.
* RTCA DO-326A / EUROCAE ED-202A, *Airworthiness Security Process Specification*, 2014.
* S. Tang, Z. Liu and L. Wang, "Power system reliability analysis considering external and
  insider attacks on the SCADA system", IEEE/PES Transmission and Distribution Conference and
  Exposition (T&D), 2020.
* U.S. Department of Energy, *National Cyber-Informed Engineering Strategy*, June 2022.
* V. L. Wright *et al.*, *Cyber-Informed Engineering Implementation Guide*, Idaho National
  Laboratory, INL/RPT-23-74072, 2023.
* CPS-02, *Related work, and what is (and is not) new here*,
  GMCavalheri/cyber-physical-rbd-attack-trees, `docs/related-work.md`.
