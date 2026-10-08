# Evidence map and paper synthesis

Reviewed 2026-10-08. Links lead to the original publisher, public-health organization or PubMed record. This repository paraphrases findings and does not include copyrighted full texts. Evidence supports the **research direction**; it does not validate HealthOS Open's invented rule thresholds.

| Source | What it contributes | What we implement or defer |
| --- | --- | --- |
| [Daniore et al., 2024, *npj Digital Medicine*](https://www.nature.com/articles/s41746-024-01151-3) | A wearable-to-digital-biomarker development framework; stresses fit to research question, collection context, verification and validation. | Keep provenance and an explicit validation plan. Do not claim a digital biomarker yet. |
| [Quintana et al., 2016, GRAPH HRV reporting guidance](https://pmc.ncbi.nlm.nih.gov/articles/PMC5070064/) | HRV research reporting should describe participants, interbeat interval collection, preparation, calculation and device/software. | Keep RMSSD and SDNN separate and record device identity. Signal-processing detail awaits raw-signal adapters. |
| [Laborde et al., 2017, HRV psychophysiology recommendations](https://pmc.ncbi.nlm.nih.gov/articles/PMC5316555/) | HRV interpretation is sensitive to acquisition conditions and physical activity. | Compare per source/device; avoid calling HRV a direct stress measurement. |
| [2025 consumer wrist wearable sleep meta-analysis](https://pmc.ncbi.nlm.nih.gov/articles/PMC11874098/) | PSG comparison shows the need to validate individual sleep metrics and devices. | Start with duration trends. Sleep stages are not used for a health conclusion. |
| [Michie et al., 2011, Behavior Change Wheel](https://pubmed.ncbi.nlm.nih.gov/21513547/) | COM-B models behavior through capability, opportunity and motivation. | Future action engine should ask about constraints and preferences; no automatic causal claim from sensors. |
| [WHO, 2024, WHO-5](https://www.who.int/publications/m/item/WHO-UCN-MSD-MHE-2024.01) | Five-item self-report of well-being over the past two weeks. | Add a separately reviewed questionnaire integration later. Do not reuse its wording or score rules without checking terms and suitable translation. |
| [WHO, 2020, physical activity guidance](https://www.who.int/publications/i/item/9789240014886) | Evidence-based population recommendations for activity. | A future goals layer can use them with population and user context; current algorithm uses no activity threshold. |
| [WHO, 2025, social connection report](https://www.who.int/publications/i/item/978240112360) | Social connection is a health dimension that sensors cannot fully describe. | Future optional self-report and contextual design; never infer loneliness from phone contacts. |
| [FDA, 2026, general wellness guidance](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/general-wellness-policy-low-risk-devices) | Intended use and claims affect product regulatory status in the US. | Keep research output separate from diagnosis; obtain jurisdiction-specific review before commercial claims. |

## From evidence to a testable hypothesis

The first research question is: **Can a person understand and act on a device-specific change in sleep duration, resting heart rate or self-reported energy without unnecessary anxiety?** Feasibility outcomes are valid-data coverage and user comprehension. Later studies must test whether the algorithm detects meaningful changes against appropriate reference data, and whether an intervention helps more than a comparison experience.

The prototype's median/MAD calculations are conventional robust-statistics tools, but the selected windows, floors and trigger criteria are local design choices. We have not found a paper that validates this exact rule as a health outcome predictor. Any public write-up should state that explicitly.
