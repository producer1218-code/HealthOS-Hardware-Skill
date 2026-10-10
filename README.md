# HealthOS Hardware Skill

**Your wearable. Your agent. Your health questions.**

![HealthOS methodology: discover permitted data, choose a personal goal, build a comparable baseline, review evidence and learn from explicit feedback](docs/assets/healthos-product-proposition.png)

A methodology for your existing AI agent to discover permitted wearable data, ask what matters to you, and turn records into a personal health observation plan, evidence-linked reports and reviewable feedback.

**Already use an agent and own a wearable? Give it [START_HERE.md](START_HERE.md).** Start with your device and health question. No installation, extra LLM key or demo is required for the planning conversation.

[中文说明](README.zh-CN.md) · [Agent Skill](skills/healthos/SKILL.md) · [Observation method](docs/observation-method.md) · [Implemented fields](docs/start-here.md) · [Evidence](docs/report-methodology.md)

[![tests](https://github.com/producer1218-code/HealthOS-Hardware-Skill/actions/workflows/tests.yml/badge.svg)](https://github.com/producer1218-code/HealthOS-Hardware-Skill/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## From a health question to an observation plan

| Stage | What the agent does | What you gain |
| --- | --- | --- |
| Discover | Identify the actual model, official data route and access eligibility | Understand what your existing device can share |
| Ask | Clarify your question, relevant context and data preferences | A goal that the available records can help describe |
| Plan | Map the question to fields, quality checks, evidence and review cadence | A reviewable personal observation plan |
| Observe | Use permitted comparable records; preserve gaps and source/method differences | Personal trends with explicit uncertainty |
| Report | Separate facts, possible explanations, unknowns and feasible actions | Understandable evidence-linked reports |
| Review | Ask about execution, suitability and self-reported outcome | Authorized memory that can be inspected, corrected and cleared |

For example: “I own a wearable, but feel tired lately.” The agent first asks whether you care about sleep, daytime energy or training recovery, checks what records are accessible, and proposes an observation plan. It does not attribute fatigue to HRV or invent a diagnosis.

The complete [agent protocol](skills/healthos/references/observation-method.md) includes question-to-data mapping, evidence boundaries, feedback and an optional [plan template](skills/healthos/references/observation-plan-v1.json). The template is a proposal format; the runtime does not import it automatically.

## Methodology first, pluggable execution

| Layer | Entry | Current scope |
| --- | --- | --- |
| Agent method | [SKILL.md](skills/healthos/SKILL.md), [observation protocol](docs/observation-method.md) | Read and plan through an existing agent; no additional model key needed |
| Device access | [Fields and adapters](docs/start-here.md), [device research](docs/model-capabilities.md) | Vendor capability and working repository integration are separate |
| Analysis and evidence | [Report methodology](docs/report-methodology.md), [evidence-to-code](docs/evidence-to-code.md) | Deterministic Python prototype; personal baseline thresholds are engineering hypotheses |
| Models and delivery | [Plugin contracts](docs/plugins.md), [handoff](docs/agent-handoff.md) | Optional model explanation and authorized transport |
| Persistence and scheduling | [Private deployment](docs/install.md) | User-operated environment required for real ongoing service |

Current v0.6 development readers include observed Fitbit exports, experimental eligible Google Health API / saved JSON, partial Apple Health XML and saved WHOOP v2 responses, plus canonical CSV/JSONL. The 20-row device catalog is research coverage, not 20 verified integrations. New Google Health projects are currently paused, checked 2026-10-09; verify [official access status](https://developers.google.com/health/about) before setup. Live device/account compatibility remains unverified.

Public literature supports measurement discipline and general-wellness discussion. It does not validate this project's thresholds or health outcomes. Reports are not clinician-authored. See [literature](docs/literature.md) and [security](SECURITY.md).

## Explore or execute when ready

Read the [complete synthetic report](docs/sample-health-report.md) to see the output. The [optional one-command demo](docs/agent-quickstart.md) runs without an LLM key; the [standalone HTML demo](docs/public-demo.md) uses fixed synthetic examples. Neither starts personal monitoring. Pages deployment has not been verified.

Use [personal deployment](docs/install.md) after deciding what to analyze and where. Reading a GitHub URL does not install a Skill, link accounts, create durable memory or schedule reports. Real records and credentials belong in your chosen private environment.

The public repository is HealthOS-Hardware-Skill; the Python package remains healthos-open. Factual discovery entrypoints: [llms.txt](llms.txt), [AI_CONTEXT.md](AI_CONTEXT.md), [capability manifest](healthos-skill.json), [FAQ](docs/faq.md). These help an agent assess relevance; they do not guarantee search ranking or automatic discovery.

For contributors: [AGENTS.md](AGENTS.md), [tests](tests), [validation](docs/validation.md). All public examples are synthetic.
