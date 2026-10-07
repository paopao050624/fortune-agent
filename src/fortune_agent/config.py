"""Configuration for an OpenAI-compatible API relay."""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlparse
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class ApiConfig:
    api_key: str
    base_url: str
    model: str

    @classmethod
    def from_env(cls) -> ApiConfig:
        api_key = os.environ.get("FORTUNE_API_KEY", "").strip()
        base_url = os.environ.get("FORTUNE_BASE_URL", "").strip().rstrip("/")
        model = os.environ.get("FORTUNE_MODEL", "").strip()
        missing = [
            name for name, value in (
                ("FORTUNE_API_KEY", api_key),
                ("FORTUNE_BASE_URL", base_url),
                ("FORTUNE_MODEL", model),
            ) if not value
        ]
        if missing:
            raise ValueError(f"请先设置：{', '.join(missing)}")

        parsed = urlparse(base_url)
        local_http = parsed.scheme == "http" and parsed.hostname in {
            "localhost", "127.0.0.1", "::1",
        }
        if (
            not parsed.hostname
            or (parsed.scheme != "https" and not local_http)
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("FORTUNE_BASE_URL 必须是 HTTPS API 根地址；本机 localhost 可使用 HTTP")
        return cls(api_key, base_url, model)


def api_status() -> dict[str, object]:
    """Return safe configuration metadata; never return the key itself."""
    try:
        config = ApiConfig.from_env()
    except ValueError as exc:
        missing = str(exc).removeprefix("请先设置：").strip()
        return {"configured": False, "missing": [item.strip() for item in missing.split(",") if item.strip()]}
    return {"configured": True, "key_set": bool(config.api_key), "base_url": config.base_url, "model": config.model}


def configure_api(*, api_key: str | None, base_url: str, model: str, test: bool = False) -> dict[str, object]:
    """Validate and apply process-local API settings, optionally probing /models."""
    key = (api_key or os.environ.get("FORTUNE_API_KEY", "")).strip()
    base = base_url.strip().rstrip("/")
    chosen_model = model.strip()
    if not key:
        raise ValueError("请输入 API Key，或保留当前已配置的 Key")
    if not base or not chosen_model:
        raise ValueError("Base URL 和模型不能为空")
    parsed = urlparse(base)
    local_http = parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    if not parsed.hostname or (parsed.scheme != "https" and not local_http) or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("Base URL 必须是 HTTPS API 根地址；本机 localhost 可使用 HTTP")
    os.environ.update(FORTUNE_API_KEY=key, FORTUNE_BASE_URL=base, FORTUNE_MODEL=chosen_model)
    result = api_status()
    if test:
        request = Request(base + "/models", headers={"Authorization": f"Bearer {key}", "Accept": "application/json"})
        try:
            with urlopen(request, timeout=8) as response:
                result["connection"] = {"ok": 200 <= response.status < 300, "status": response.status}
        except Exception as exc:
            result["connection"] = {"ok": False, "error": f"{type(exc).__name__}，请检查地址、密钥和中转站可用性"}
    return result
