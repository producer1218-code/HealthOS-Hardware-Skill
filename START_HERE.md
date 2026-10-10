# HealthOS Hardware Skill — start with your health question

**把这个入口交给已有的 Agent：让它了解你的设备、你关心的健康问题，并提出一份有依据、可检查的观察方案。** 无需先安装或提供额外 LLM key。

This router supports an existing agent. Reading it grants no access to records, installation or recurring execution. Reuse answers already in the conversation.

## Begin with the person

1. Ask: **“你用什么型号的手环或健康设备，最想用它了解什么？”** If known, proceed to the missing information.
2. Read the [observation method](skills/healthos/references/observation-method.md). Clarify the question and only the relevant context; do not guess causes from wearable scores.
3. Check [actual parsed fields](docs/start-here.md) and [device capabilities](docs/model-capabilities.md). Explain official API eligibility, mobile bridges or exports; distinguish vendor openness from implemented connectors. Verify current official access conditions before giving setup instructions.
4. Deliver a short observation plan: question, actual data, permissions still needed, measurement/quality method, evidence boundaries, report cadence, feedback and a feasible next step. Optional [interchange template](skills/healthos/references/observation-plan-v1.json); not an executable profile or consent record.
5. Only after the user chooses fields, purposes and processing location, continue to real-data access. Model sharing, storage and delivery need their own choices. Never request credentials in chat or public files.

## Choose the execution route only when needed

| Agent capability | What can happen |
| --- | --- |
| Read public URLs | Explain access and create a proposed observation plan immediately; optionally read the [synthetic report](docs/sample-health-report.md). No private memory or background work is implied. |
| Read files and execute Python | After host permission and user setup, use [personal deployment](docs/install.md). For an optional synthetic demo, follow [quickstart](docs/agent-quickstart.md). |
| Load directory-based Skills | Load the entire [healthos folder](skills/healthos) through the host's trust/install rules. Method references travel with it. |
| Remote tools only | Read these public instructions if URL access exists. No public MCP endpoint or hosted account-link service is supplied. |

An optional demo uses synthetic records only; preserve its own dates and never carry its example permissions into real data. Claim execution only after checking outputs. Scheduling and delivery require actual tools and a running environment.

## Copy this request

> 请读 https://github.com/producer1218-code/HealthOS-Hardware-Skill/blob/main/START_HERE.md ，使用 HealthOS Hardware Skill。先了解我的设备型号和关心的健康问题，解释可以开放哪些数据、实际能怎样接入，再提出有证据与未知说明的个人观察方案。不要默认安装、索取密钥或启动监控；需要时再给我看合成报告。

Machine-readable routing: [agent-start.json](agent-start.json). This is a project-specific manifest, not automatic registration or a guarantee that an agent will discover the repository.
