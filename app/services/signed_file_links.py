from __future__ import annotations

import hashlib
import hmac
import os
import time


DEFAULT_LINK_TTL_SECONDS = 24 * 60 * 60


def _signing_secret() -> bytes:
    secret = (
        os.getenv("DOMNAI_FILE_LINK_SECRET")
        or os.getenv("SESSION_SECRET")
        or os.getenv("CLERK_SECRET_KEY")
        or ""
    ).strip()
    if not secret:
        raise RuntimeError("Segredo para links de arquivo não configurado.")
    return secret.encode("utf-8")


def _signature(asset_id: str, expires_at: int) -> str:
    payload = f"{asset_id}:{expires_at}".encode("utf-8")
    return hmac.new(_signing_secret(), payload, hashlib.sha256).hexdigest()


def create_signed_file_path(asset_id: str, ttl_seconds: int = DEFAULT_LINK_TTL_SECONDS) -> str:
    expires_at = int(time.time()) + max(60, int(ttl_seconds))
    signature = _signature(asset_id, expires_at)
    return f"/api/library/shared/{asset_id}?expires={expires_at}&signature={signature}"


def validate_signed_file_link(asset_id: str, expires_at: int, signature: str) -> bool:
    if expires_at < int(time.time()):
        return False
    expected = _signature(asset_id, expires_at)
    return hmac.compare_digest(expected, str(signature or ""))
