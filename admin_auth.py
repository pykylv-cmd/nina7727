"""Minimal deny-by-default platform-admin session boundary for NinaOS Web."""

from __future__ import annotations

import hashlib
import hmac
import os
import time

ADMIN_ROLE = "platform_admin"
CLIENT_ROLE = "client"
ADMIN_COOKIE = "nina_platform_admin"
ADMIN_SESSION_SECONDS = 8 * 60 * 60
ADMIN_BOOTSTRAP_MIN_LENGTH = 12


def bootstrap_configured() -> bool:
    return len((os.environ.get("NINA_PLATFORM_ADMIN_BOOTSTRAP_TOKEN") or "").strip()) >= ADMIN_BOOTSTRAP_MIN_LENGTH


def verify_bootstrap_token(supplied: str) -> bool:
    expected = (os.environ.get("NINA_PLATFORM_ADMIN_BOOTSTRAP_TOKEN") or "").strip()
    return len(expected) >= ADMIN_BOOTSTRAP_MIN_LENGTH and hmac.compare_digest(str(supplied or ""), expected)


def _signature(secret: bytes, payload: str) -> str:
    return hmac.new(secret, payload.encode(), hashlib.sha256).hexdigest()


def create_admin_session(secret: bytes, now: int | None = None) -> str:
    expires = int(now or time.time()) + ADMIN_SESSION_SECONDS
    payload = f"{ADMIN_ROLE}:{expires}"
    return f"{payload}.{_signature(secret, payload)}"


def verify_admin_session(value: str, secret: bytes, now: int | None = None) -> bool:
    raw = str(value or "")
    try:
        payload, supplied = raw.rsplit(".", 1)
        role, expires_raw = payload.split(":", 1)
        expires = int(expires_raw)
    except (TypeError, ValueError):
        return False
    payload = f"{role}:{expires}"
    return (
        role == ADMIN_ROLE
        and expires > int(now or time.time())
        and hmac.compare_digest(supplied, _signature(secret, payload))
    )
