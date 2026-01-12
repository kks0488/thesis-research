#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
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


MODEL_ALIASES = {
    "deepseek-v3.2-speciale": "deepseek-reasoner",
    "deepseek-v3-2-speciale": "deepseek-reasoner",
}


def normalize_model(model: str) -> str:
    raw = model.strip()
    if not raw:
        return raw
    return MODEL_ALIASES.get(raw.lower(), raw)


def _load_env_file(path: Path) -> None:
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        if raw.startswith("export "):
            raw = raw[len("export ") :].strip()
        key, value = raw.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key or key in os.environ:
            continue
        if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]
        os.environ[key] = value


def load_dotenv() -> Path | None:
    cwd = Path.cwd()
    loaded: Path | None = None
    for root in [cwd, *cwd.parents]:
        for name in (".env.local", ".env"):
            candidate = root / name
            if candidate.is_file():
                _load_env_file(candidate)
                if loaded is None:
                    loaded = candidate
    return loaded


def load_config_from_env() -> DeepSeekConfig:
    load_dotenv()
    api_key = (os.getenv("DEEPSEEK_API_KEY") or "").strip()
    if not api_key:
        raise DeepSeekError("Missing DEEPSEEK_API_KEY env var.")

    model = normalize_model((os.getenv("DEEPSEEK_MODEL") or "deepseek-reasoner").strip())
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
    payload_base = {
        "model": config.model,
        "messages": list(messages),
        "temperature": float(temperature),
        "stream": False,
    }

    last_err: Exception | None = None
    current_max_tokens = max(1, int(max_tokens))
    for attempt in range(retries + 1):
        try:
            payload = {**payload_base, "max_tokens": current_max_tokens}
            data = _post_json(url, headers=headers, payload=payload, timeout_s=config.timeout_s)
            choices = data.get("choices") or []
            if not choices:
                raise DeepSeekError(f"Empty choices: {data!r}")
            choice = choices[0] or {}
            message = choice.get("message") or {}
            content = message.get("content")
            reasoning = message.get("reasoning_content")
            finish_reason = choice.get("finish_reason")
            if isinstance(content, str) and content.strip():
                return content
            if reasoning and finish_reason == "length" and attempt < retries:
                current_max_tokens = min(max(256, current_max_tokens * 2), 4096)
                continue
            if reasoning:
                raise DeepSeekError("Empty content from deepseek-reasoner; increase max_tokens or use deepseek-chat.")
            raise DeepSeekError(f"Empty content: {data!r}")
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
