# Lesson 6 · Cyber-Informed Engineering in numbers, and what is (and isn't) new

> The first five lessons built a model and drew conclusions from it. This one steps back and
> asks three questions a reviewer would ask. Where do the numbers touch the Cyber-Informed
> Engineering framework the project claims to serve? Which assumptions carry the conclusions,
> and which would break them? What, honestly, had nobody done before? A model is only as
> useful as its stated limits, and a portfolio piece is only as credible as its novelty claim.

**Docs:** [`related-work.md`](../related-work.md), [`scope.md`](../scope.md),
[`report.md`](../report.md) ·
**Previous:** [Lesson 5](05-where-mitigation-money-matters.md) ·
**Course index:** [README](README.md)

## Learning objectives

1. Map a quantitative reliability result onto INL's twelve CIE principles, and say where the
   model is silent.
2. List the assumptions behind every headline number and predict what breaks if each fails.
3. Distinguish what is established in the literature from what this project adds.
4. Explain how to replace the illustrative inputs with real ones, and what to measure first.

---

## 1. The twelve principles, and where the numbers touch them

INL's *Cyber-Informed Engineering Implementation Guide* (2023) organises CIE as twelve
principles, each with key questions for the engineering lifecycle. The model speaks to most
of them, sometimes with a number:

| # | principle | what this project says, quantitatively |
|---|---|---|
| 1 | Consequence-focused design | The function ("trusted navigation data reaches the mission computer") is defined first. Every attack is described by its effect on that function (Lesson 2). |
| 2 | Engineered controls | A timing margin that tolerates the delay removes 34 % of unavailability, and a better integrity monitor 14 % (Lesson 5). |
| 3 | Secure information architecture | A shared bus is one attack surface for every channel on it. Its denial is one series block, whatever the channel count (Lesson 3). |
| 4 | Design simplification | A third channel or navigation unit adds parts, *lowers* the FMC rate and buys nothing against the attacks (Lesson 5). |
| 5 | Layered defenses | Onset catch, detection and recovery act in sequence on an episode, and the tornado shows which layer moves the result (Lesson 5). |
| 6 | Active defense | Faster detection and recovery shorten outages but leave system MTBF unchanged (1 087 h across the sweep). They are duration levers, not frequency levers (Lesson 5). |
| 7 | Interdependency evaluation | Shared power buses and a shared data bus make exact enumeration necessary, and they create the common mode (Lessons 1, 3). |
| 8 | Digital asset awareness | Scenarios target *groups*, which requires knowing which components share a medium or a function (Lesson 2). |
| 9 | Cyber-secure supply chain controls | Not modelled. CPS-02's case study has a supply-chain branch, at the effect level. |
| 10 | Planned resilience | Recovery time and degraded modes (PMC) are explicit. The frequency/duration split mirrors the robustness/rapidity ends of a resilience curve (Bruneau et al., 2003). |
| 11 | Engineering information control | Not modelled. The project's own scope rule (effects only, public sources) is a small instance of the principle. |
| 12 | Organizational culture | The point of the shared metric language: one table that a reliability team and a security team can both read (Lesson 4). |

Two principles are untouched (9 and 11), and two more are touched only qualitatively (8 and
12). Saying so is part of the result.

## 2. The assumptions that carry the conclusions

| assumption | where it is used | what breaks if it fails |
|---|---|---|
| Attacks and physical failures are **independent** | product distribution (Lesson 3) | An attack that *causes* hardware damage, or that is timed to coincide with maintenance, makes the joint states dependent. The closed form is then wrong; the simulation can host the dependence. |
| Platforms are **independent** | confidence intervals and fleet totals (Lesson 4) | A fleet-wide campaign hits many platforms at once. Mean rates may survive, but the distribution of simultaneously available aircraft, the number that matters for a surge, does not. |
| Attacks arrive at a **constant rate** and **pause during an episode** | renewal-reward (Lesson 3) | Adaptive adversaries change rates over time. The pause causes the small duration artifact of Lesson 5. |
| **Unlimited repair** resources, **no spares delay** | component availability; no NMCS | Shared repair crews or parts shortages lengthen outages. Physical NMC would then be understated. |
| **Steady state**, continuous possession | every rate | Real fleets alternate flying, ground time and depot visits. Ratios such as "cyber is 85 % of NMC time" are more robust than absolute hours. |
| The **MC mapping**: PMC means degraded redundancy, NMC means function lost | readiness statuses | Real MC status depends on mission-essential equipment lists per mission type. The mapping is a modelling choice, not a reporting rule. |
| **Illustrative attack parameters** | every cyber number | The mitigation *ranking* depends on them. The *structural* results do not: the common-mode identity, MTBF insensitivity to detection, and redundancy paying only at the physical single point of failure. |

The last row matters most. The project's claims that would survive contact with real data
are the structural ones. The percentages are a worked example.

## 3. What is new, and what is not

From [`related-work.md`](../related-work.md), in one paragraph. Measuring security like
reliability goes back to Littlewood et al. (1993). Stochastic attack-and-response models with
means such as MTTSF are established (Madan et al., 2004), and so are adversary-driven state
models (ADVISE, 2011). Putting attack processes into Monte Carlo reliability evaluation and
reading out standard indices has been done for power grids (Tang, Liu and Wang, 2020, with
LOLP and EENS). **None of that is claimed here.** What this project adds:

* the translation into the **aviation and defense readiness language** (dashboard MTBF, MTTR
  and availability from an outage log; FMC/PMC/NMC with a physical/cyber cause split), which
  the reviewed works do not use;
* an **effect-level scenario interface** that maps each attack to an equivalent MTBF and MTTR
  without describing any technique;
* **exact metrics verified two ways** (closed form and an independent simulation with a
  sample-path reduction), tied to CPS-02 at $10^{-12}$;
* the **common-mode identity** for cyber effects made explicit and tested, with its
  consequence for redundancy investment.

The novelty claim is moderate and specific. A systematic search of the defense-readiness
literature is the next step before it goes into a paper.

## 4. Using the model with real inputs

1. **Describe the function and its structure** in `system_parameters.csv` and
   `navigation_system()`, or write your own builder. Use real failure rates and repair-time
   distributions from maintenance data; the Fleet Reliability Dashboard's own formulas apply.
2. **Describe the threat by its effects** in `attack_scenarios.csv`. For arrival rates, a
   time-to-compromise estimate (McQueen et al., 2006) or threat-intelligence frequencies are
   natural inputs. Keep the effect level.
3. **Run** `validation/run_all.py`. It regenerates every table and figure, and the reproduce
   CI job proves the published numbers come from the published inputs.
4. **Spend analysis money where the tornado points.** In the example, the two bus attack rates
   swing the result most, so better estimates of those two numbers are worth more than more
   precision anywhere else.

## 5. Where the series goes next

* **CPS-02** puts the same system in one graph of failure and attack logic, per mission. CPS-01
  is its time-domain, fleet-level companion, and the two agree on the physical baseline.
* **CPS-04** (common-cause cyber failure of redundancy) starts from Lesson 3's identity: what
  happens when channels share some, but not all, of an attack surface.
* The plan's open extension, feeding combined risk into maintenance optimization, needs
  exactly the outage log of Lesson 4.

## Exercises

1. Pick two CIE principles the model does not address, and describe the smallest model
   extension that would let it say something quantitative about each.
2. Suppose attacks are more likely during maintenance (a laptop is connected to the bus).
   Which assumption breaks? Would the closed form over- or understate unavailability?
3. A reviewer says: "Your mitigation ranking is just your made-up rates." Which conclusions
   would you defend, and which would you concede?
4. Why is "cyber effects take 85 % of NMC time" more robust to the steady-state assumption
   than "1 102 hours of cyber NMC per million hours"?
5. In one sentence each, say how this project differs from (a) Tang, Liu and Wang (2020) and
   (b) DO-326A/ED-202A.

### Solutions

1. Principle 9 (supply chain): add a scenario class whose arrival is a one-time event at
   delivery with a long latent period, and track fleet exposure over time. Principle 11
   (engineering information control): make an attack rate depend on what design information
   leaks, as a parameter, and show the sensitivity.
2. Independence between attacks and physical failures. Denials would cluster in states where
   a component is already down for maintenance, which raises the chance of NMC "both" and
   reduces the hours where the attack is the only cause. Total unavailability could go either
   way: overlap with an outage that already took the function down adds no new lost time.
   The NMC cause split and the frequency of losses would both be misjudged. The simulation,
   not the closed form, is the right tool.
3. Defend the structural results: the common-mode series-block identity, detection and
   recovery as duration-only levers, and redundancy paying only at the physical single point
   of failure. Concede the percentages and the exact order of the cyber mitigations, which
   depend on the rates.
4. A ratio of two time shares is less sensitive to how many hours the platform is actually
   possessed or operating, because both shares scale together. Absolute hours scale directly
   with the assumed exposure.
5. (a) Tang et al. compute grid reliability indices for SCADA attacks modelled by
   time-to-compromise. This project computes aviation/defense readiness metrics for
   effect-level scenarios, with exact closed forms and a cause split. (b) DO-326A/ED-202A is
   a qualitative airworthiness security process (threat conditions by safety severity and
   level of threat). This project is a quantitative model of what effects cost in reliability
   and readiness, which could inform but not replace that process.

## References

* V. L. Wright *et al.*, *Cyber-Informed Engineering Implementation Guide*, INL/RPT-23-74072,
  2023 (the twelve principles).
* U.S. Department of Energy, *National Cyber-Informed Engineering Strategy*, June 2022.
* B. Littlewood *et al.*, "Towards operational measures of computer security", *Journal of
  Computer Security*, 2(2–3), 1993.
* B. B. Madan *et al.*, *Performance Evaluation*, 56, 2004 (MTTSF).
* S. Tang, Z. Liu and L. Wang, IEEE/PES T&D 2020 (power-system reliability with SCADA attacks).
* M. Bruneau *et al.*, *Earthquake Spectra*, 19(4), 2003 (resilience).
* RTCA DO-326A / EUROCAE ED-202A, *Airworthiness Security Process Specification*, 2014.
* Full list: [`related-work.md`](../related-work.md).
