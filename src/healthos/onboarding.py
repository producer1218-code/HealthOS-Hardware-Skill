"""Local guided onboarding; explicit answers create consent, never defaults."""
from datetime import datetime, timezone

from healthos.permissions import PATHS, connection_plan
from healthos.planning import GOAL_METRICS


GOALS_ZH = {"sleep": "睡眠", "recovery": "恢复", "activity": "活动", "wellbeing": "自述精力", "vitals": "身体指标", "social_connection": "社会连接（自愿自述）"}


def selected_indices(answer: str, items: list) -> list:
    selected = []
    for entry in answer.split(","):
        if not entry.strip():
            continue
        number = int(entry.strip())
        if not 1 <= number <= len(items):
            raise ValueError("选择编号超出范围，未保存授权。")
        if items[number - 1] not in selected:
            selected.append(items[number - 1])
    return selected


def wizard(ask=input, tell=print) -> dict:
    now = datetime.now(timezone.utc)
    tell("HealthOS：先说目标，再选择数据。每项都可拒绝，之后可撤回。")
    user = ask("本地用户代号（不必用真名）：").strip()
    concern = ask("你最想改善什么？这段话仅保存在本地：").strip()
    goals = list(GOALS_ZH)
    tell(" / ".join(f"{i + 1} {GOALS_ZH[g]}" for i, g in enumerate(goals)))
    selected = ask("选择目标编号，按优先级排序，用逗号分隔：")
    chosen = selected_indices(selected, goals)
    profile = {"user_id": user, "main_concern": concern[:500], "timezone": "Asia/Shanghai",
               "goals": chosen, "sources": [], "consents": [],
               "preferences": {"max_notices_per_7_days": 2}, "advice_plugin": "guideline"}
    adapters = list(PATHS)
    while ask("添加一个已有数据入口？输入 yes 添加，其他输入跳过：").strip().lower() == "yes":
        tell(" / ".join(f"{i + 1} {a}" for i, a in enumerate(adapters)))
        adapter = selected_indices(ask("入口编号："), adapters)[0]
        for step in PATHS[adapter][1]:
            tell(step)
        path = ask("合法本地导出文件路径（尚未取得可以留空）：").strip()
        sid = f"source-{len(profile['sources']) + 1}"
        profile["sources"].append({"id": sid, "adapter": adapter, "path": path})
        relevant = sorted(PATHS[adapter][0] & set().union(*(GOAL_METRICS[g] for g in chosen)))
        tell(" / ".join(f"{i + 1} {m}" for i, m in enumerate(relevant)))
        answer = ask("允许分析哪些指标？填写编号，逗号分隔；留空表示不开放：")
        metrics = selected_indices(answer, relevant)
        for purpose, prompt in [("local_analysis", "允许本地处理这些指标？"),
                                ("notifications", "允许基于这些指标生成主动提醒？"),
                                ("external_delivery", "允许把提醒摘要发到你指定的飞书账号？飞书将收到摘要。")]:
            granted = bool(metrics) and ask(prompt + " 输入 yes 才授权：").strip().lower() == "yes"
            profile["consents"].append({"source_id": sid, "purpose": purpose, "metrics": metrics,
                                        "granted": granted, "granted_at": now.isoformat() if granted else None})
    connection_plan(profile, now)  # Validate before saving any profile.
    tell("已生成本地授权档案。文件尚未读取；运行 connection-plan 查看步骤，care 核对实际数据。")
    return profile
