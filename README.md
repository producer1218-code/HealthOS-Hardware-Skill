# HealthOS Open

[![tests](https://github.com/producer1218-code/healthos-open/actions/workflows/tests.yml/badge.svg)](https://github.com/producer1218-code/healthos-open/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**Understand the wearable you already own. Connect permitted records to your own agent, receive evidence-linked reports, and refine a personal plan through feedback.**

**第一次来？[中文入口](README.zh-CN.md) → [新用户指引](docs/start-here.md) → [直接查看完整报告](docs/sample-health-report.md)。阅读无需安装、登录或密钥。**

## Explore without installing anything

| Your question | Public entry |
| --- | --- |
| Which devices and fields are actually supported? | [Device and field matrix](docs/model-capabilities.md) |
| How do permitted records reach my own agent? | [Guided journey](docs/start-here.md) · [Fitbit / Google access](docs/google-health-connect.md) |
| How does a health method become a suggestion? | [Evidence, calculations, context and feedback](docs/report-methodology.md) |
| What does the output look like? | [Complete synthetic report](docs/sample-health-report.md) · [No-install interactive demo](docs/public-demo.md) |
| Can I replace the LLM, data source and delivery channel? | [Plugin contracts](docs/plugins.md) · [Agent handoff](docs/agent-handoff.md) |
| How do I run it privately after exploring? | [Personal deployment and configuration](docs/install.md) |

## The user journey

Existing wearable + confirmed goals → guided official export or eligible API access → explicit field and purpose consent → quality, missingness and separate personal baselines → periodic report with evidence, questions and small actions → optional model explanation and opted-in delivery → feedback and inspectable memory.

A Fitbit Air user first checks access eligibility and actual fields. Eligible Google projects can try the experimental read-only connector; other users can start with official exports. The agent asks about goals and context, compares comparable records, reports what is known and missing, and uses feedback to pause unsuitable actions. It does not infer illness, emotions or intervention efficacy from wearables.

## Inspect a complete report format

![Synthetic report preview](docs/synthetic-report-ui.png)

[Read the complete synthetic report](docs/sample-health-report.md) directly on GitHub. No author-hosted service is needed. The [standalone HTML demo](docs/public-demo.md) can be downloaded and opened in a browser, with no dependencies or keys. It uses fixed synthetic examples, does not run the production analyzer, and makes no API or model calls.

GitHub Pages deployment files are included. Initial Pages enablement still requires a repository administrator; deployment is skipped until enabled. The [demo guide](docs/public-demo.md) explains publishing. An unverified site URL is not presented as a live demo.

## Current implementation and limits

v0.6 development: observed Fitbit exports; experimental eligible Google Health API / saved v4 JSON; Apple Health XML and saved WHOOP v2 subsets; canonical CSV/JSONL; personal onboarding; deterministic periodic reports; replaceable LLM prose; inspectable memory and optional Feishu transport.

See the [exact field table](docs/start-here.md). The 20-row catalog is research coverage, not 20 verified integrations. Google pauses new project onboarding, checked 2026-10-09; creating an OAuth client is not eligibility. [Official status](https://developers.google.com/health). Live Fitbit Air compatibility remains unverified.

Primary research and guidelines inform general-wellness reasoning. Reports are not clinician-authored; clinical efficacy, live accounts, external delivery and baseline thresholds remain unverified. [Methodology](docs/report-methodology.md) · [Literature](docs/literature.md) · [Security](SECURITY.md).

## Run your own system when ready

Follow [personal deployment](docs/install.md) for installation, credentials, model configuration, recurring execution and delivery. Localhost is a private interface on each operator's computer after startup, not a public repository entry. GitHub does not run private monitoring. Never commit personal records, OAuth credentials or model keys.

For contributors: [AGENTS.md](AGENTS.md), [tests](tests), [plugins](docs/plugins.md), [validation](docs/validation.md). Backend checks cover Linux/Windows on Python 3.10/3.12; public examples use synthetic data.
