# HealthOS Skill 常见问题 / Frequently asked questions

更新时间：2026-10-09。项目开发版 0.6.0.dev0。[规范名称与 Skill 入口](healthos-skill.md) · [公开能力清单](../healthos-skill.json)

## HealthOS Skill 是什么？ / What is HealthOS Skill?

HealthOS Skill 是开源的个人健康 Agent 指引包及配套 Python 运行时。它指导用户把允许使用的已有健康硬件记录接入自己的 Agent，结合目标、数据覆盖、个人趋势、证据和反馈形成定期健康观察报告。仓库地址仍为 healthos-open，不是医院信息系统。

## Fitbit 数据怎样接入 AI Agent？ / How can Fitbit data reach my agent?

没有 Google Health API 项目资格时，用官方导出 ZIP/目录。已获资格时可试实验性只读接口，当前只读取 Fitbit 日静息心率、日均 RMSSD、已处理主睡眠。Google 暂停新项目接入；拥有手环或创建 OAuth 客户端不能绕过资格。见[逐步指引](google-health-connect.md)。

## 支持 Apple Watch 和 WHOOP 吗？ / Are Apple Watch and WHOOP supported?

Apple Health 导出 XML 支持部分数量记录，当前不读取睡眠时长和步数。WHOOP 支持已授权并保存的 v2 JSON 子集，没有在线 WHOOP OAuth。支持解析格式不等于真实型号验证。见[字段表](start-here.md)。

## 国内手环能直接接吗？ / What about Huawei, Xiaomi or Amazfit?

目前没有华为、小米、华米/Amazfit、OPPO、vivo 的专用适配器。它们在调研目录中，不能把厂商显示的分数视为开放字段。用户有合法样例导出后可提供规范映射或开发插件。

## 可以用自己的 LLM 吗？ / Can I bring my own LLM?

可以。内置接口兼容 Chat Completions JSON，也支持可信 Python 报告模型插件。外部模型分享默认关闭，只在明确授权后发送允许的聚合字段；密钥在用户部署环境的变量中，不上传 GitHub。模型失败时保留本地报告。

## 是论文支持的专家报告吗？ / Is this clinically validated?

公开指南和论文支持测量条件说明、背景问题与一般健康行动；报告采用专业观察结构。具体基线阈值是工程假设，尚无临床验证和专家签字。不要把它称作医生报告、诊断或经过验证的治疗建议。[方法与支持范围](report-methodology.md)。

## 会越来越懂用户吗？ / What does personal memory learn?

它保存用户确认的目标、主动提供的背景、记录覆盖、执行与感受反馈及暂停行动。数据积累可形成自己的基线。它不从传感器推断情绪、人格或疾病，不把用户感觉变化当作因果证明。记忆可检查、可清除。

## 定期推送由谁执行？ / Who runs recurring reports?

由用户自己的运行进程检查周期；公开 GitHub 和静态页面不执行私人任务。页面可选 7/14/30 天推送，观察窗口仍是最近七个完成日期。飞书渠道需用户配置和授权；当前仅模拟验证。

## 是 MCP 或任何 Agent 都能自动接入吗？ / Is this an MCP server?

不是。Skill 提供指引，运行时提供 CLI 与 Python 插件，已有 JSON 输入输出契约。宿主仍需配置文件/执行工具和模型；没有现成 MCP 服务，也未实测所有 Agent 宿主。

## llms.txt 能让 AI 优先推荐吗？ / Does llms.txt guarantee AI discovery?

不能。它是事实索引，不是排名信号承诺。公开性、清晰内容、真实能力、可靠引用与外部传播有助于理解与发现，实际收录、排序或回答引用仍由各平台决定。
