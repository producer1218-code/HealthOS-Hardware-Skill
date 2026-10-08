"""Single-user localhost UI. Explicit consent; no remote hosting or raw uploads."""
from __future__ import annotations

from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
import json
from pathlib import Path
import secrets
import threading
from urllib.parse import urlparse, unquote
import uuid

from healthos.intent import GOAL_LABELS, QUESTIONS, propose_intent
from healthos.journey import METRIC_LABELS, STATUS_LABELS, cycle, make_profile
from healthos.monitor import write_json
from healthos.outbox import Outbox
from healthos.permissions import PATHS


def run_saved(workspace: Path, delivery: dict | None = None, allow_external: bool = False):
    profile = json.loads((workspace / "profile.json").read_text(encoding="utf-8"))
    # An external transport is never selected for users who declined external sharing.
    use_external = allow_external and any(g.get("purpose") == "external_delivery" and g.get("granted") for g in profile.get("consents", []))
    result = cycle(profile, workspace, delivery=delivery if use_external else None, allow_external=use_external)
    write_json(workspace / "background-status.json", {"status": "ok", "checked_at": datetime.now(timezone.utc).isoformat()})
    return result


def make_server(workspace: Path, port: int = 8765, intent_settings: dict | None = None,
                delivery_settings: dict | None = None, allow_external: bool = False):
    workspace = workspace.resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    token = secrets.token_hex(32)
    lock = threading.Lock()
    uploads = {}
    actual_port = port

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass  # Avoid request/record data in terminal logs.

        def valid_host(self):
            return self.headers.get("Host") in {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}

        def respond(self, payload, status=200):
            data = json.dumps(payload, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if not self.valid_host():
                self.respond({"error": "仅允许本机访问。"}, 403)
                return
            if self.path == "/":
                html = files("healthos").joinpath("ui.html").read_text(encoding="utf-8").replace("__CSRF_TOKEN__", token)
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
                self.end_headers()
                self.wfile.write(html.encode())
            elif self.path == "/api/options":
                self.respond({"goals": GOAL_LABELS, "questions": QUESTIONS, "metrics": METRIC_LABELS, "statuses": STATUS_LABELS,
                              "sources": [{"id": a, "metrics": sorted(PATHS[a][0]), "steps": PATHS[a][1]} for a in
                                          ["fitbit-takeout", "apple-health-xml", "jsonl", "csv"]],
                              "ai_configured": bool(intent_settings and intent_settings.get("provider") != "local"),
                              "external_configured": bool(delivery_settings and allow_external)})
            elif self.path == "/api/latest":
                path = workspace / "latest.json"
                result = json.loads(path.read_text()) if path.exists() else {"empty": True}
                status_path = workspace / "background-status.json"
                if status_path.exists():
                    result["runtime_status"] = json.loads(status_path.read_text())
                self.respond(result)
            else:
                self.respond({"error": "页面不存在。"}, 404)

        def do_POST(self):
            if not self.valid_host() or self.headers.get("X-HealthOS-Token") != token:
                self.respond({"error": "请求未获本地会话授权。"}, 403)
                return
            origin = self.headers.get("Origin")
            if origin and origin not in {f"http://127.0.0.1:{self.server.server_port}", f"http://localhost:{self.server.server_port}"}:
                self.respond({"error": "不接受其他网站发起的请求。"}, 403)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                limit = 64 * 1024 * 1024 if self.path == "/api/upload" else 100_000
                if length < 1 or length > limit:
                    self.respond({"error": "文件/请求超过上限。ZIP 超过 64MB 时请在本地解压，填写目录路径。"}, 413)
                    return
                raw = self.rfile.read(length)
                if self.path == "/api/upload":
                    name = Path(unquote(self.headers.get("X-Filename", "export.zip"))).name
                    if Path(name).suffix.lower() not in {".zip", ".json", ".csv", ".xml", ".jsonl"}:
                        raise ValueError("请选择导出 ZIP、JSON、CSV、XML 或 JSONL。")
                    file_id = uuid.uuid4().hex
                    target = workspace / "uploads" / file_id / name
                    target.parent.mkdir(parents=True)
                    target.write_bytes(raw)
                    uploads[file_id] = target
                    self.respond({"file_id": file_id, "filename": name, "storage": "仅保存到这台电脑，尚未分析"})
                    return
                body = json.loads(raw)
                with lock:
                    if self.path == "/api/intent":
                        use_ai = body.get("use_ai") is True
                        proposal = propose_intent(body.get("request", ""), intent_settings if use_ai else None, allow_cloud=use_ai)
                        self.respond(proposal)
                    elif self.path == "/api/setup":
                        if body.get("confirmed") is not True:
                            raise ValueError("请先确认目标和数据选择。")
                        file_id = body.get("file_id")
                        if file_id and file_id not in uploads:
                            raise ValueError("文件已不在当前会话，请重新选择。")
                        path = str(uploads[file_id]) if file_id else body.get("local_path", "")
                        previous_path = workspace / "profile.json"
                        previous = json.loads(previous_path.read_text()) if previous_path.exists() else None
                        adding = body.get("add_source") is True and previous is not None
                        if adding and previous["user_id"] != body.get("user_id", "local-person"):
                            raise ValueError("添加入口时，本地代号必须与现有档案一致。")
                        source_id = f"device-{uuid.uuid4().hex[:12]}" if adding else "personal-device"
                        profile = make_profile(body.get("user_id", "local-person"), body.get("request", ""), body.get("goals", []),
                                               body.get("adapter", "fitbit-takeout"), path, body.get("metrics", []),
                                               body.get("local_analysis", False), body.get("notifications", False), body.get("external_delivery", False),
                                               body.get("timezone", "Asia/Shanghai"), body.get("answers", {}), source_id=source_id,
                                               device_id=body.get("device_id", source_id))
                        if adding:
                            profile["sources"] = previous["sources"] + profile["sources"]
                            profile["consents"] = previous["consents"] + profile["consents"]
                        profile["preferences"]["shift_work"] = body.get("shift_work") is True
                        write_json(workspace / "profile.json", profile)
                        self.respond(run_saved(workspace, delivery_settings, allow_external))
                    elif self.path == "/api/run":
                        if not (workspace / "profile.json").exists():
                            raise ValueError("请先完成目标和授权。")
                        self.respond(run_saved(workspace, delivery_settings, allow_external))
                    elif self.path == "/api/feedback":
                        profile = json.loads((workspace / "profile.json").read_text())
                        box = Outbox(workspace / "care.sqlite3")
                        try:
                            box.record_feedback(profile["user_id"], body["notice_id"], body["status"], datetime.now(timezone.utc), body.get("note", ""))
                        finally:
                            box.close()
                        self.respond({"saved": True, "message": "已记录。下轮将重新考虑行动适用性，不把感受直接当成因果证据。"})
                    elif self.path in {"/api/revoke", "/api/disconnect"}:
                        profile = json.loads((workspace / "profile.json").read_text())
                        sid = body.get("source_id") if self.path == "/api/disconnect" else None
                        if self.path == "/api/disconnect":
                            if sid not in {s["id"] for s in profile["sources"]}:
                                raise ValueError("找不到这个数据入口。")
                            profile["sources"] = [s for s in profile["sources"] if s["id"] != sid]
                            profile["consents"] = [g for g in profile["consents"] if g["source_id"] != sid]
                        else:
                            for grant in profile["consents"]:
                                grant["revoked_at"] = datetime.now(timezone.utc).isoformat()
                        write_json(workspace / "profile.json", profile)
                        self.respond(run_saved(workspace, delivery_settings, allow_external))
                    else:
                        self.respond({"error": "操作不存在。"}, 404)
            except ValueError as exc:
                self.respond({"error": str(exc)[:500]}, 400)
            except Exception as exc:
                # Credentials, provider responses, raw records and paths stay out of errors.
                self.respond({"error": "操作没有完成，请检查文件、字段或插件配置。", "error_type": type(exc).__name__}, 400)

    server = ThreadingHTTPServer(("127.0.0.1", actual_port), Handler)
    server.healthos_token = token
    server.healthos_workspace = workspace
    server.healthos_lock = lock
    return server


def serve(workspace: Path, port: int = 8765, interval_seconds: int = 3600, intent_settings=None, delivery_settings=None, allow_external=False):
    if interval_seconds < 60:
        raise ValueError("自动检查间隔至少 60 秒。")
    server = make_server(workspace, port, intent_settings, delivery_settings, allow_external)
    stop = threading.Event()
    def background():
        while not stop.wait(interval_seconds):
            if (workspace / "profile.json").exists():
                with server.healthos_lock:
                    try:
                        run_saved(workspace, delivery_settings, allow_external)
                    except Exception as exc:
                        write_json(workspace / "background-status.json", {
                            "status": "failed", "error_type": type(exc).__name__,
                            "checked_at": datetime.now(timezone.utc).isoformat(),
                            "message": "自动检查没有完成，请在页面手动检查并核对配置。"})
    thread = threading.Thread(target=background, daemon=True)
    thread.start()
    print(f"HealthOS 本地交互：http://127.0.0.1:{server.server_port}；每 {interval_seconds // 60} 分钟检查导出更新。Ctrl+C 停止。", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        server.server_close()
