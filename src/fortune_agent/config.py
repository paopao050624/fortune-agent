"""Configuration for an OpenAI-compatible API relay."""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlparse


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
