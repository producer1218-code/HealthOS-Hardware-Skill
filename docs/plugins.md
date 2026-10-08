# 可插拔接口

四个边界分别替换，均为可信 Python 插件；不是隔离沙箱。高级配置应放 `data/private/`。内置 UI 提供已声明入口，高级档案支持自定义模块与多来源。

## 需求理解

`provider: local` 默认关键词匹配，明确标记非 AI。可用 `examples/intent_settings.json` 指定 HTTPS 兼容接口、model、api_key_env；设置环境变量后：

```bash
healthos serve --intent-settings data/private/intent_settings.json
```

页面逐次勾选 AI 才发送用户输入的需求；终端需 `start --intent-settings ... --allow-cloud-intent`。需求本身可能敏感，勾选时应知悉配置的提供方。没有发送设备记录或自动读取私有档案。

自定义 `provider: your_package.intent:Planner` 实现 `propose(request: str, settings: dict) -> dict`，返回 goals / summary / questions。白名单校验只接受已知目标，最多 4 个目标、3 个问题。输出 `requires_confirmation: true`，忽略模型试图提供的授权、阈值和医疗建议字段。问题正文和摘要仍是模型文本，需用户判断；结构校验不是模型质量评估。模型故障会报错，不假装 AI 成功。

当前问答用于保存用户背景、确认目标与下一轮补问；自由文本答案不会自动转换成医学规则。轮班可行性由明确勾选开关调整。后续更细的节奏/偏好规划须增加可审计字段与测试。

## 数据入口

```python
class Adapter:
    def configure(self, settings: dict): ...  # optional
    def read(self, path, user_id): ...        # yields Observation
```

高级 profile 的 sources 每项包含 id / adapter / path / device_id。已知入口能力从 permissions.PATHS 提供；自定义 `module:Class` 在来源配置中声明 metrics 和 setup_steps，不能声明未知 canonical 指标。configure 收到 timezone / device_id / allowed_metrics；联网插件必须在请求时限制 scope，通用旧版读取器可能先读全部选定文件再过滤。Fitbit 文件选择在读取前按授权筛选。

来源权限在实例化读取器前核验，分析还要求用户、目标和指标匹配。每个来源、设备、方法单独基线。扩展实时采集不能把 OAuth 授权等同于本地分析和外发授权。参见[适配器](adapters.md)、[数据契约](data-contract.md)。

## 行动建议

profile.advice_plugin 默认 guideline；自定义 `module:Class.propose(result, profile, feedback)`。结果包含 action_id / action / question / evidence / success_check / scope / content_version / review_status。当前 scope 仅接受 general_wellness；必须有 HTTPS 证据链接和版本。插件可能收到完整本地背景和反馈；外部传输需另建明确 opt-in，不能在自定义代码里悄悄外发。

内置内容来自公开原始来源，标记尚未临床专家审核。插件格式合格不证明医学正确；生产审查应真实记录审查者、资质、日期、人群、排除条件、证据与复审版本。

## 推送和反馈

```python
class Delivery:
    external = False
    def send(self, notice, settings):
        return "confirmed-delivery-id"
```

`local-json` 内置，飞书用 `healthos.feishu:FeishuDelivery`。外部插件 external=True，需用户对来源/指标授权 external_delivery、命令 allow 标记、recipient_user_id 匹配。模糊送达抛 DeliveryUncertain，停止自动重试；明确失败重试前再次检查授权和预算。

反馈只接受已送达且归属本人 notice。execution 与 self_reported_outcome 分层；拒绝或感觉更差暂停 action_id。不会据此更新生理门槛或宣称因果改善。接口参见 outbox.Outbox.record_feedback。公网/飞书回调还需认证、验签、身份绑定、去重与回放防护，当前没有手机回调服务。
