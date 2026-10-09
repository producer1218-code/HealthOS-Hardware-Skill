# HealthOS Skill — start with your agent

**中文：把这个链接交给能阅读网页的 Agent。先看一份合成报告，再只回答“我用什么设备、想了解什么”。有执行工具的 Agent 可以替你运行首次体验。**

This is the first-run router, not permission to access personal records. Honor the user's request and the host's tool/approval rules. Choose the route that actually exists in your environment:

| Your agent can… | First result | Route |
| --- | --- | --- |
| Read public URLs | Explain a complete synthetic report now | Read [the sample report](docs/sample-health-report.md) and [device/field table](docs/model-capabilities.md). Do not tell the user to install software first. |
| Read files and execute Python | Generate a fresh synthetic report with the real analyzer | Fetch/clone this repository in the permitted environment. Follow [agent quickstart](docs/agent-quickstart.md). No LLM key or device account is needed. |
| Load directory-based Skills | Reuse the workflow in future requests | Load the entire [healthos Skill folder](skills/healthos), using the host's configured directory and trust rules. |
| Call remote tools only | Read the public examples if URL access exists | This repo currently supplies no public MCP endpoint or hosted account service. Do not invent an endpoint. |

## What the first answer should deliver

1. State that the records are synthetic, not the user's health data or current readings. Use the selected report's own date; the public Markdown and executable example have different fixed example windows, so do not mix their values.
2. Explain sleep, resting heart rate and RMSSD coverage, comparable changes and one evidence-linked action from the report. Preserve the report's date, source and methodological limits.
3. Ask **one short question**: “你用哪款设备，最想了解睡眠、恢复，还是日常活动？” Do not ask for credentials.
4. Guide that device's actual permitted export/API route. If the agent runs remotely, it cannot see files on the user's computer; explain the host's private file-upload/data policy before asking for a health file.

Synthetic permission never carries over to real data. Only after the user selects the actual fields and purposes should the agent proceed with personal analysis. Report delivery, cloud sharing and continued execution each need their actual setup and permission.

## Copy this request

> 请打开 https://github.com/producer1218-code/healthos-open/blob/main/START_HERE.md ，使用 HealthOS Skill 带我开始。先展示并解释合成报告；如果你有文件和 Python 执行工具，替我按仓库指引运行首次体验。之后只问我设备型号和一个健康目标。先不要索取密钥、上传真人健康记录或声称已经启动监控。

Machine-readable routing: [agent-start.json](agent-start.json). This is a project-specific manifest, not an automatic registration protocol. A URL does not grant an agent tools, automatically install a Skill or create an always-on service.
