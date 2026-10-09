# Agent 带用户完成首次体验

入口是 [START_HERE.md](../START_HERE.md)。用户只需把入口交给能读网页的 Agent；无需先理解 Python、OAuth 或模型设置。首次报告全部为合成数据。

## 仅能阅读网页：马上解释报告

读 [完整合成报告](sample-health-report.md)，结合[设备字段表](model-capabilities.md)解释“我的手环数据能做什么”。不要把演示当真人报告。随后一次问设备型号与一个目标。该模式无需安装、密钥或后台服务，不能自动保存私密记忆或推送。

## 有文件和 Python 工具：一条命令运行

Agent 按宿主权限获取完整仓库，在仓库目录执行：

~~~bash
python scripts/agent_start.py --workspace demo-output/first-experience
~~~

需要 Python 3.10+，无需安装 HealthOS 包、模型 SDK 或 Google 依赖。Windows 环境若缺少时区数据，启动器会明确返回 needs_timezone_data / blocked；按宿主安装规则安装 `tzdata` 后重试，不能说已成功。可先运行 `python scripts/agent_start.py --check`，不创建文件。

脚本用固定的 2026-07 合成记录运行生产 care_once/build_report。结果是 Markdown 报告、JSON 报告、Agent 输入和 start-receipt.json。Agent 读取返回 JSON 中的 report 路径，解释真实生成的内容；无需打开本地网页。没有真实账号、LLM 调用、设备同步、后台调度或外部发送。

已存在的工作目录会拒绝覆盖。重复体验选一个新的目录，不删除用户已有文件。执行失败时用公开报告继续首次讲解，并说明未运行成功。宿主无网络下载工具时可由用户提供仓库 ZIP；仅安装 Skill 文件夹时还需要完整运行时代码。

## 从首次体验到真实使用

1. 确认设备、一个目标和用户运行环境。按实际 adapter 字段决定是否可分析，不把目录里的研究品牌都算支持。
2. 优先指导已支持的官方导出。Fitbit/Google 新 API 项目目前暂停接入；创建 OAuth 客户端不等于有资格。Google 实时接入须按[接入指南](google-health-connect.md)再次核对官方状态。
3. 真实数据新建独立个人档案，确认字段、用途和本地/远程处理位置；不复用合成 profile 或 consents。执行 Agent 可按[个人部署](install.md)完成安装，让用户通过自己的页面选择授权。聊天 Agent 可解读用户选择交给它的报告，但健康文件提供给远程宿主本身就涉及外部分享。
4. 在已有 Agent 宿主解释报告，不要求额外 LLM key。只有用户希望 HealthOS 自身调用独立模型时，才配置 BYO LLM 和单独的聚合分享授权；不要在聊天或仓库写密钥。
5. 持续监控需要用户自己的常驻环境和数据更新路径。Agent 能运行一次不等于能永久运行；纯导出需要刷新文件，真实通知也须配置和验证接收渠道。

## 验收

“开箱即用首次体验”指能阅读公开完整报告，或用一条命令生成报告并解释。没有宣称任意 Agent 的宿主都兼容。持续真人服务仍需要授权、数据来源与可靠运行环境。

Agent Skills 的发现和激活由宿主实现；格式本身不自动提供工具。[官方接入说明](https://agentskills.io/client-implementation/adding-skills-support)。远程工具服务需要实际服务端和客户端支持；本项目尚无公开 MCP 服务。[MCP 架构](https://modelcontextprotocol.io/docs/learn/architecture)。
