# HealthOS Hardware Skill：把健康硬件记录交给自己的 Agent

**HealthOS Hardware Skill 是一个可复用的 Agent 指引包，帮助用户选择已有设备的数据入口，并解释有依据的个人健康观察报告。** HealthOS Open 是原有名称；仓库和 Python 包仍为 healthos-open，旧链接和命令保持有效。

[查看 SKILL.md](../skills/healthos/SKILL.md) · [机器可读能力清单](../healthos-skill.json) · [完整报告示例](sample-health-report.md) · [常见问题](faq.md)

## Skill 和系统有什么区别

| 部分 | 做什么 |
| --- | --- |
| HealthOS Hardware Skill | 给 Agent 使用的任务路由、设备字段、方法与权限边界 |
| HealthOS Python 运行时 | 在用户自己的环境里读数据、计算、保存记忆与报告、检查周期 |
| 可替换 LLM | 在用户授权下解释计算结果，不能代替确定性统计 |
| 公开演示 | 用合成数据展示输出结构，不读取真人数据或执行推送 |

只安装 Skill 不会连接设备或启动后台监控。具备文件/执行工具的 Agent 可指导部署运行时；只具备聊天能力的 Agent 可读指南与用户许可的报告。兼容 Agent Skills 文件格式不等于各个平台已实测兼容。

## 如何交给自己的 Agent

最短路径：把 [START_HERE.md](../START_HERE.md) 的公开链接交给 Agent。它按实际工具选择立即讲解合成报告，或一条命令运行生产分析器。无需先填写 LLM key；真实账号、数据和持续运行在体验之后逐项确认。[操作与限制](agent-quickstart.md)。

无需安装的方式：把 [SKILL.md](../skills/healthos/SKILL.md) 与相邻的 references/workflow.md 交给你的 Agent，或让它读这个仓库。它应先解释实际可取得的字段和访问资格，再收集用户目标。

支持目录式 Agent Skills 的宿主：下载仓库，将 **整个 skills/healthos 文件夹** 放到宿主配置的 Skill 目录，保持 SKILL.md、agents/ 和 references/ 的相对位置；按宿主文档加载。不要只复制文件名，也不需要把健康记录或密钥放进去。格式依据：[Agent Skills 标准](https://agentskills.io/specification)、[OpenAI Skills 文档](https://developers.openai.com/api/docs/guides/tools-skills)。

可给 Agent 的任务示例：

> 使用 HealthOS Hardware Skill（支持命名调用时用 $healthos）。我是 Fitbit 用户，希望理解睡眠与恢复记录。先指导我确认合法数据入口与实际字段，不要索取我的 OAuth 凭证。我确认目标和用途后，解释我的 HealthOS 报告，保留缺失、来源、证据及未验证边界。

## 开始验证

先读[合成输入 JSON](../examples/agent_packet.synthetic.json)和[配套输出 JSON](../examples/wellness_report.synthetic.json)，再看[可读报告结构](sample-health-report.md)，它们无需任何私人授权。真实运行步骤见[个人部署](install.md)。生产包使用 agent-context-v1；[JSON Schema](../schemas/agent-context-v1.schema.json)是可选的格式校验，不能证明来源或授权。

当前 Skill 已校验文件结构与入口；运行时以合成数据/模拟 API 测试。未完成跨宿主行为验证、真实设备账号验证或临床专家审核，不能称作自动诊断或医生报告工具。
