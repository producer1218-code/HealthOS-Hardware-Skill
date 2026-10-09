# 个人部署：运行你自己的 HealthOS

这里是安装后的私人使用说明。想了解项目或查看报告，先读[公开新用户指引](start-here.md)和[无需安装的演示](public-demo.md)。GitHub 阅读与个人部署是两个入口；只阅读仓库无需开启监听服务。

## 先体验，不需要账号或密钥

需要 Python 3.10+。首次安装属于开发者操作；安装后使用本地网页。

~~~bash
git clone https://github.com/producer1218-code/healthos-open.git
cd healthos-open
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# macOS / Linux 使用 source .venv/bin/activate
python -m pip install -e .
python examples/create_report_demo.py
healthos serve --workspace data/private/report-demo
~~~

**仅在你自己的电脑完成上述安装并启动服务之后**，在同一台电脑的浏览器打开 `http://127.0.0.1:8765`。这个地址指向访问者自己的电脑，不是作者服务器或公开演示地址。查看合成报告、数据覆盖、行动与反馈。示例授权只针对合成数据；真实档案需要重新选择字段和用途。

## 用自己的数据建立系统

运行 healthos serve，按页面顺序完成：

1. 描述你想改善什么，确认目标，补充愿意分享的生活背景。
2. 选择数据入口：导出模式选文件，API 模式先完成[Google 接入指南](google-health-connect.md)，再填 connection 目录。
3. 逐项选择指标，分别授权本地分析、主动通知、外部推送。每项默认关闭；Google OAuth 范围需要单独同意。
4. 开启报告，选择每 7、14 或 30 天；第一份在下一轮检查生成，以后按周期运行。
5. 记录行动是否执行、是否适合，以及自述感受。下次保留背景、重新检查数据，并暂停你拒绝或感觉更差的行动。

先保存档案、后开启报告时，点击“检查更新”即可生成第一份。serve 默认每小时检查；电脑和进程必须运行。停止时不发送，重启后检查到期情况。GitHub 本身不托管、存储或推送你的私人健康记录。

## 插入你自己的 LLM

不配模型也有完整的本地报告。模型解释已算好的事实并提出澄清问题；证据、数值、基线规则和行动由 HealthOS 保留。

复制 examples/report_settings_llm.json 到 data/private/personal/report-settings.local.json，填写服务地址、模型名称和密钥环境变量名称。配置文件不放实际密钥。

~~~powershell
$env:HEALTHOS_LLM_API_KEY = "你的密钥"
healthos configure-reports --settings data/private/personal/report-settings.local.json --allow-cloud-report
healthos serve
~~~

兼容接口使用 Chat Completions JSON 格式；其他接口可实现 module:Class 的 render(aggregate_packet, settings)。默认模型接收目标标识、分开排列的聚合指标、缺失天数、趋势状态和反馈计数。不发送身份、设备标识、原始记录、路径、密钥和生活背景原文。页面显示配置的接收方，你可以关闭模型分享。

AI 文字标为未经专家审核的草稿；格式、新增数字或链接不合要求、调用失败时，仍交付本地报告。格式校验不能证明解释正确。Google API 派生和聚合数据仍适用[官方用户数据政策](https://developers.google.com/health/policies/health-api-developer-user-data-policy)；你配置的服务须符合相应用途和分享条件。

## 报告怎么越来越了解你

报告包含目标与覆盖、本周及上周有效天数与中位数、独立设备的个人基线、解释边界、下周小行动、复盘方式、原始证据和下一次问题。[完整示例](sample-health-report.md)可以直接阅读。

个人记忆是可检查的记录：确认的目标、主动补充的背景、测量覆盖、执行与感受反馈、已暂停行动。它随记录更新；不会从 HRV 推断情绪或人格，不自动改变临床阈值，不把“感觉更好”当作效果证明。网页和 healthos forget-memory 可清除本地报告、背景回答及反馈，保留导出和目标；外部已发送副本需在接收服务另行删除。

已有 Agent？让它先读 [Agent 交接说明](agent-handoff.md)，再读本地 agent-packet.json；包中有覆盖、方法、证据和解释边界，不需要读取 OAuth 凭证。

## 定期推送

默认交付本地 reports/*.md 和 JSON，并显示在网页上。要手机推送，配置自己的飞书应用机器人、接收者和独立分享授权：

~~~bash
healthos serve --delivery-settings data/private/feishu_delivery.json --allow-external-delivery
~~~

按[飞书说明](personalized-care.md#飞书设置)操作。飞书收到观察与行动摘要，背景原文留在本地；完整报告在本机查看。周期报告与行动提醒有不同投递账本。相同报告不重复发送；不确定回执保留状态，需人工核对。飞书通过模拟测试，尚未验证真实账号发送；手机端反馈暂未实现。

## 目前实际读取范围

| 入口 | 实际字段 | 边界 |
| --- | --- | --- |
| Fitbit 官方导出 | 睡眠时长、静息心率、显式 RMSSD、步数 | 支持已观察的文件子集，导出可能缺字段 |
| Google Health API / v4 JSON | Fitbit 日静息心率、日均 RMSSD、已处理主睡眠时长 | 实验实现；无自动步数、血氧、皮温；需账号资格与可确认来源 |
| Apple Health XML | 心率、静息心率、SDNN、血氧、睡眠腕温 | 当前不读睡眠时长和步数 |
| 保存的 WHOOP v2 JSON | 静息心率、RMSSD、血氧、皮温、睡眠时长、呼吸频率 | 需已有授权与保存响应；无 WHOOP 在线 OAuth |
| 规范 CSV / JSONL / 插件 | 标准字段词表 | 映射由适配器保证，不证明某设备已支持 |

目录 20 行是调研范围，并非 20 款设备均已验证。API 估算值不等于开放原始信号。换设备、算法或来源会建立新数据流；同名设备仍可能无法区分，需要人工确认。

## 验证与扩展

~~~bash
python -m unittest discover -s tests -v
healthos report
healthos watch --once
healthos plugins
~~~

测试使用合成数据与模拟 API；尚无真实设备完整验证、临床专家签字或效果研究。查看[方法与论文映射](report-methodology.md)、[插件协议](plugins.md)、[安全与存储](../SECURITY.md)。Google 在线模式要求健康记录和凭证位于加密存储；当前依赖系统磁盘加密，不提供应用层加密，不自动验证加密状态。
