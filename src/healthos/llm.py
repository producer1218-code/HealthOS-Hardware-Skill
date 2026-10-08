"""Optional BYO-model narration; the model never chooses whether to alert."""
from __future__ import annotations

import json
import os
from importlib import import_module
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise ValueError("LLM endpoint redirects are refused to protect the API key")


def narrate(notice: dict, settings: dict, allow_cloud: bool = False) -> str:
    provider = settings.get("provider", "none")
    if provider == "none":
        return notice["message"]
    if not allow_cloud:
        raise ValueError("external narration disabled; pass --allow-cloud-health-data to send aggregate trend data")
    if ":" in provider:
        module_name, class_name = provider.split(":", 1)
        renderer = getattr(import_module(module_name), class_name)()
        if not callable(getattr(renderer, "render", None)):
            raise TypeError("narrator must implement render(notice, settings)")
        return str(renderer.render(notice, settings))[:2000]
    if provider != "openai_compatible":
        raise ValueError("unknown LLM provider")
    endpoint = settings.get("endpoint", "")
    parsed = urlparse(endpoint)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError("LLM endpoint must be an HTTPS URL without embedded credentials")
    env_name = settings.get("api_key_env", "HEALTHOS_LLM_API_KEY")
    key = os.environ.get(env_name)
    if not key:
        raise ValueError(f"missing API key environment variable: {env_name}")
    model = settings.get("model")
    if not model:
        raise ValueError("LLM model is required")
    # Only aggregated values leave the machine; no user_id, device_id, raw records or state.
    payload = {field: notice[field] for field in
               ("metric", "unit", "baseline_median", "recent_median", "baseline_n_days",
                "recent_n_days", "rule_version")}
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Explain an observed personal wellness trend in plain language. "
             "Do not diagnose, predict a disease, recommend treatment, imply certainty, or invent data. "
             "Mention that the rule is an unvalidated research prototype. Keep under 100 words."},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ],
    }
    request = Request(endpoint, data=json.dumps(body).encode("utf-8"),
                      headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                      method="POST")
    with build_opener(_NoRedirect()).open(request, timeout=20) as response:
        raw = response.read(65537)
    if len(raw) > 65536:
        raise ValueError("LLM response exceeds 64 KiB")
    answer = json.loads(raw)
    content = answer["choices"][0]["message"]["content"]
    if not isinstance(content, str) or not content.strip():
        raise ValueError("LLM returned no text")
    return content.strip()[:2000]
