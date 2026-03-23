from __future__ import annotations

import httpx

from app.core.config import Settings


def build_http_client(settings: Settings) -> httpx.Client:
    return httpx.Client(trust_env=settings.trust_env_proxy, timeout=60.0)
