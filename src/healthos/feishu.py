"""Optional Feishu app-bot text delivery. Never invoked by default or the demo.

https://open.feishu.cn/document/server-docs/im-v1/message/create
API acknowledgement is delivery success, not proof of reading or executing.
"""
from __future__ import annotations

import json
import os
from urllib.request import Request, build_opener, HTTPRedirectHandler
from healthos.outbox import DeliveryUncertain


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def post(path: str, body: dict, token: str | None = None) -> dict:
    headers = {"Content-Type": "application/json; charset=utf-8"}
    if token:
        headers["Authorization"] = "Bearer " + token
    request = Request("https://open.feishu.cn/open-apis/" + path,
                      data=json.dumps(body, ensure_ascii=False).encode(), headers=headers, method="POST")
    with build_opener(NoRedirect()).open(request, timeout=15) as response:
        payload = json.loads(response.read(1_000_000))
    if payload.get("code") != 0:
        raise RuntimeError("Feishu rejected request")
    return payload


class FeishuDelivery:
    external = True

    def send_report(self, report: dict, settings: dict) -> str:
        if settings.get("recipient_user_id") != report["user_id"]:
            raise ValueError("recipient binding mismatch")
        receive_type = settings.get("receive_id_type", "open_id")
        if receive_type not in {"open_id", "user_id"} or not settings.get("receive_id"):
            raise ValueError("Feishu requires a specific consenting user")
        auth = post("auth/v3/tenant_access_token/internal", {
            "app_id": os.environ[settings.get("app_id_env", "HEALTHOS_FEISHU_APP_ID")],
            "app_secret": os.environ[settings.get("app_secret_env", "HEALTHOS_FEISHU_APP_SECRET")]})
        # Free-text history stays local; send only the bounded report observation/actions.
        text = report["markdown"].split("## 我目前了解的你", 1)[0] + "\n完整证据、个人记忆与反馈入口见你本机 HealthOS 报告。"
        try:
            result = post("im/v1/messages?receive_id_type=" + receive_type,
                          {"receive_id": settings["receive_id"], "msg_type": "text", "uuid": report["id"][:32],
                           "content": json.dumps({"text": text[:12000]}, ensure_ascii=False)}, auth["tenant_access_token"])
        except RuntimeError:
            raise
        except Exception:
            raise DeliveryUncertain("report may have been accepted; reconcile before retry") from None
        receipt = result.get("data", {}).get("message_id")
        if not receipt:
            raise DeliveryUncertain("report acknowledgement missing")
        return receipt

    def send(self, notice: dict, settings: dict) -> str:
        if settings.get("recipient_user_id") != notice["user_id"]:
            raise ValueError("recipient binding mismatch")
        receive_type = settings.get("receive_id_type", "open_id")
        if receive_type not in {"open_id", "user_id"} or not settings.get("receive_id"):
            raise ValueError("Feishu delivery requires a specific consenting user")
        app_id = os.environ[settings.get("app_id_env", "HEALTHOS_FEISHU_APP_ID")]
        secret = os.environ[settings.get("app_secret_env", "HEALTHOS_FEISHU_APP_SECRET")]
        auth = post("auth/v3/tenant_access_token/internal", {"app_id": app_id, "app_secret": secret})
        observation = notice["observation"]
        advice = notice["advice"]
        measured = (f"{observation['metric']}：最近三日中位数 {observation['recent_median']:.1f} {observation['unit']}，"
                    f"个人基线 {observation['baseline_median']:.1f} {observation['unit']}。") if "recent_median" in observation else "你的目标行动提醒"
        text = (f"你的健康观察 · {notice['as_of']}\n{measured}\n"
                f"{notice['why_you']}\n\n可以先做：{advice['action']}\n{advice['question']}\n"
                f"依据：{advice['evidence'][0]['url']}\n这是个人趋势与一般健康建议。")
        try:
            result = post("im/v1/messages?receive_id_type=" + receive_type,
                          {"receive_id": settings["receive_id"], "msg_type": "text",
                           "content": json.dumps({"text": text}, ensure_ascii=False),
                           "uuid": notice["id"][:32]}, auth["tenant_access_token"])
        except RuntimeError:
            raise  # Provider explicitly rejected the request.
        except Exception:
            raise DeliveryUncertain("message may have been accepted; reconcile before retry") from None
        receipt = result.get("data", {}).get("message_id")
        if not receipt:
            raise DeliveryUncertain("Feishu acknowledgement missing")
        return receipt
