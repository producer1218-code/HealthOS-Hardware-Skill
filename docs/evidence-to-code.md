# Evidence → design decision → code → validation gap

This ledger is the fastest way to audit the phrase “paper-based method.” The literature informs **measurement discipline and hypotheses**. It has not validated the exact HealthOS Hardware Skill alert function. A single wearable deviation is not a diagnosis.

| Published source | Supported principle | Implemented here | Remaining gap |
| --- | --- | --- | --- |
| [Daniore et al., 2024](https://www.nature.com/articles/s41746-024-01151-3) | Digital biomarker development needs fit-for-purpose verification, analytical and clinical validation. | `model.py` retains units/source/device; `docs/validation.md` separates validation stages. | No reference-device comparison or clinical endpoint study. |
| [GRAPH HRV reporting guidance, Quintana et al., 2016](https://pmc.ncbi.nlm.nih.gov/articles/PMC5070064/) | HRV methods and context must be reported. | RMSSD and SDNN have distinct names/units; baselines do not cross `source` or `device_id`. | Vendor HRV collection windows and artefact removal are not independently verified. |
| [Laborde et al., 2017](https://pmc.ncbi.nlm.nih.gov/articles/PMC5316555/) | HRV varies with acquisition and behavior conditions. | Per-stream comparisons; notice asks about wear/travel/training. | No automatic confounder model or evidence of psychological stress. |
| [Consumer wrist wearable sleep meta-analysis, 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC11874098/) | Sleep estimates need metric- and device-specific validation against reference methods. | Sleep duration trend only; no stage-based clinical inference. | No device-specific accuracy correction or polysomnography comparison. |
| [Behavior Change Wheel / COM-B, Michie et al., 2011](https://pubmed.ncbi.nlm.nih.gov/21513547/) | Behavior depends on capability, opportunity and motivation. | Optional context questions; no compliance judgement. | No tested intervention, preference model or causal inference. |
| [WHO-5, 2024](https://www.who.int/publications/m/item/WHO-UCN-MSD-MHE-2024.01) | Well-being can be assessed through structured self-report. | Not implemented. A simple energy score is **not** WHO-5. | Licensed/localized questionnaire handling and psychometric validation. |
| [WHO physical activity guidance, 2020](https://www.who.int/publications/i/item/9789240014886) | Population-level activity recommendations exist. | Steps are retained as a trend-only metric. | Individualized recommendation logic and population applicability. |

## Explicit engineering hypotheses

`analysis.py` uses a 28-day baseline window, at least 14 valid baseline dates, three recent valid dates, median/MAD, a directed z gate of 2.5, and metric-specific minimum changes. `monitor.py` adds a seven-day per-stream cooldown and a rolling weekly budget. These are **not thresholds taken from the cited papers**. They are versioned, inspectable starting points for prospective testing. A stable but unhealthy baseline can still pass the rule, and a healthy lifestyle change can trigger it.

## Minimum validation before consumer health claims

1. Technical: compare export fields, units, timestamps and duplicates against known device/app versions.
2. Analytical: compare derived metrics to suitable references by device and population; quantify missingness, bias and drift.
3. Decision: preregister meaningful-change definitions, then measure sensitivity, false-notice rate, notification burden and subgroup differences.
4. Human factors: test comprehension, anxiety, actionability and user control. Include negative results and escalation routes reviewed by clinicians.

The result of unit tests is software correctness on synthetic fixtures. It is not evidence that the system improves health.
