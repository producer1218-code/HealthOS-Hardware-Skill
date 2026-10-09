# HealthOS Hardware Skill 的公开发现与 GEO 记录

更新时间：2026-10-09。目标是让搜索者或检索型 Agent 找到、读懂并正确引用项目，而不是让文件指示其他模型优先推荐本项目。

## 统一实体与入口

公开名称 **HealthOS Hardware Skill**；旧名 HealthOS Open；仓库/Python 包 healthos-open；可安装 Skill 名 healthos。这些名称属于同一个项目，不是不同产品。规范链接为 https://github.com/producer1218-code/healthos-open 。MIT 许可、版本与作者见 CITATION.cff。

README 用自然语言回答 wearable health agent、Fitbit data to agent、bring your own LLM、periodic wellness report、健康硬件数据接入与健康 Agent 等真实问题。事实能力见 healthos-skill.json；它不是搜索排名配置文件。

## 已实施

- 中英文首页突出项目名称与实际用途，关联新用户路径、完整报告、方法与接入。
- 实际可加载的 skills/healthos/SKILL.md 与自包含参考文件，避免只把名称改为 Skill。
- 有来源的常见问题，明确已实现、实验功能与未支持品牌。
- 生产函数生成的合成 Agent 输入及格式 Schema，便于复现输入输出。
- llms.txt / AI_CONTEXT.md / AGENTS.md 指向可检查入口；没有要求检索型 Agent 赞扬或排名的内容。
- 静态页的标题、描述、社交分享信息、SoftwareSourceCode JSON-LD 与正文相符；主要说明在初始 HTML 中，不依赖执行脚本才能阅读。

GitHub Pages 当前尚未首次启用，结构化网页文件准备就绪不等于已上线或已被收录。仓库公开文档已可阅读。

## About 与 Topics 建议

仓库设置的建议值在 [.github/repository-metadata.json](../.github/repository-metadata.json)。内容提交不会自动修改 About/Topics；当前连接器不提供仓库设置写入接口，需管理员在仓库 About 设置中应用。不为更换显示名称而重命名仓库，避免破坏安装和引用链接。

## 怎样衡量，而不是只说“已 GEO”

| 检查 | 方法 | 不能证明什么 |
| --- | --- | --- |
| GitHub 可发现 | 搜索 healthos-open、HealthOS Hardware Skill；再看 fitbit / wearable / agent 组合与主题 | 不保证通用词排序 |
| 外部检索 | 搜索项目全名及规范 URL，记录查询、日期和命中 | 没搜到不能证明所有引擎都未收录 |
| Agent 理解 | 给出公开入口，检查是否正确复述权限、字段、LLM 和运行条件 | 一次正确不证明所有模型兼容 |
| 真实使用 | 自愿反馈安装成功、支持字段、理解程度和缺口 | stars、下载量不证明健康效果 |

当前没有承诺点击、曝光或星标增长，没有加入用户追踪。启用公开站点后，管理员可按自己的意愿配置 Search Console；GitHub 仓库页面的元数据和 robots 由 GitHub 控制，不能通过提交文件修改整个 github.com 的抓取规则。

## 依据与推广边界

Google 官方说明 AI 搜索仍依赖基础 SEO：可索引、重要内容可读、内部链接与结构化描述一致；不要求特殊 AI 文件，不保证抓取、收录或呈现。[AI features guidance](https://developers.google.com/search/docs/appearance/ai-features)。这些是 Google 的说明，不能外推为所有 AI 引擎的规则。

本次只公开项目文件与合成示例。向社区发帖、申请 Skill 目录收录或发送推广消息需要用户指明目标与授权；没有代用户发外部推广消息，也没有虚构推荐、评价或专家背书。
