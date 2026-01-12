#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Iterable


class DeepSeekError(RuntimeError):
    pass


@dataclass(frozen=True)
class DeepSeekConfig:
    api_key: str
    model: str
    base_url: str = "https://api.deepseek.com"
    api_path: str = "/chat/completions"
    timeout_s: int = 60


def load_config_from_env() -> DeepSeekConfig:
    api_key = (os.getenv("DEEPSEEK_API_KEY") or "").strip()
    if not api_key:
        raise DeepSeekError("Missing DEEPSEEK_API_KEY env var.")

    model = (os.getenv("DEEPSEEK_MODEL") or "DeepSeek-V3.2-Speciale").strip()
    allow_override = (os.getenv("DEEPSEEK_ALLOW_OVERRIDE") or "").strip() == "1"

    base_url = "https://api.deepseek.com"
    api_path = "/chat/completions"
    if allow_override:
        base_url = (os.getenv("DEEPSEEK_BASE_URL") or base_url).strip().rstrip("/")
        api_path = (os.getenv("DEEPSEEK_API_PATH") or api_path).strip()

    if "deepseek" not in base_url:
        raise DeepSeekError("DeepSeek API is required (base_url must be DeepSeek).")

    if not api_path.startswith("/"):
        api_path = "/" + api_path
    return DeepSeekConfig(api_key=api_key, model=model, base_url=base_url, api_path=api_path)


def _post_json(url: str, headers: dict[str, str], payload: dict[str, Any], timeout_s: int) -> dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={**headers, "Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        return json.loads(resp.read().decode("utf-8"))


def chat_completion(
    messages: Iterable[dict[str, Any]],
    *,
    config: DeepSeekConfig,
    temperature: float = 0.2,
    max_tokens: int = 1200,
    retries: int = 3,
) -> str:
    url = f"{config.base_url}{config.api_path}"
    headers = {"Authorization": f"Bearer {config.api_key}", "User-Agent": "thesis-research/0.1"}
    payload = {
        "model": config.model,
        "messages": list(messages),
        "temperature": float(temperature),
        "max_tokens": int(max_tokens),
        "stream": False,
    }

    last_err: Exception | None = None
    for attempt in range(retries + 1):
        try:
            data = _post_json(url, headers=headers, payload=payload, timeout_s=config.timeout_s)
            choices = data.get("choices") or []
            if not choices:
                raise DeepSeekError(f"Empty choices: {data!r}")
            msg = (choices[0].get("message") or {}).get("content")
            if not isinstance(msg, str) or not msg.strip():
                raise DeepSeekError(f"Empty content: {data!r}")
            return msg
        except urllib.error.HTTPError as e:
            last_err = e
            try:
                body = e.read().decode("utf-8", errors="replace")
            except Exception:
                body = ""
            # 429/5xx: retry; others: fail fast
            status = getattr(e, "code", None)
            if status in (429, 500, 502, 503, 504) and attempt < retries:
                time.sleep(0.8 * (2**attempt))
                continue
            raise DeepSeekError(f"HTTPError {status}: {body}".strip()) from e
        except (urllib.error.URLError, TimeoutError) as e:
            last_err = e
            if attempt < retries:
                time.sleep(0.8 * (2**attempt))
                continue
            raise DeepSeekError(str(e)) from e

    raise DeepSeekError(str(last_err) if last_err else "Unknown error")
