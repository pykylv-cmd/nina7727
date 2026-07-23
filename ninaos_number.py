"""Official NinaOS WhatsApp numbers over Meta Cloud API.

Phone numbers and provider identifiers are configuration. Sender identities are
converted to opaque, number-scoped workspace and conversation identifiers before
they reach Nina's shared message service.
"""

import hashlib
import hmac
import json
import os
import re
from urllib.parse import quote

from whatsapp_channel import WhatsAppProviderError, send_cloud_api_message


CHANNEL = "ninaos_number"
CONFIG_ENV = "NINAOS_NUMBERS_JSON"
IDENTITY_KEY_ENV = "NINAOS_NUMBER_IDENTITY_KEY"
_SAFE_ID = re.compile(r"^[A-Za-z0-9_.:-]{3,128}$")
_WORKSPACE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,80}$")
_E164 = re.compile(r"^\+[1-9][0-9]{6,14}$")
_ENV_REF = re.compile(r"^[A-Z][A-Z0-9_]{2,127}$")


def _identity_secret():
    value = (os.environ.get(IDENTITY_KEY_ENV) or os.environ.get("NINA_CHANNEL_CREDENTIAL_KEY") or "").strip()
    if not value:
        raise RuntimeError("ninaos_number_identity_key_missing")
    return value.encode()


def configured_numbers():
    raw = (os.environ.get(CONFIG_ENV) or "").strip()
    if not raw:
        return []
    try:
        values = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("invalid_ninaos_numbers_config") from exc
    if not isinstance(values, list) or len(values) > 20:
        raise ValueError("invalid_ninaos_numbers_config")
    result = []
    seen_ids = set()
    for value in values:
        if not isinstance(value, dict):
            raise ValueError("invalid_ninaos_numbers_config")
        item = {
            "key": str(value.get("key") or "").strip(),
            "display_number": str(value.get("display_number") or "").replace(" ", ""),
            "phone_number_id": str(value.get("phone_number_id") or "").strip(),
            "workspace_id": str(value.get("workspace_id") or "").strip(),
            "region": str(value.get("region") or "").strip().upper(),
            "name": str(value.get("name") or "Nina").strip()[:80],
            "access_token_env": str(value.get("access_token_env") or "").strip(),
            "app_secret_env": str(value.get("app_secret_env") or "").strip(),
            "verify_token_env": str(value.get("verify_token_env") or "").strip(),
            "primary": bool(value.get("primary")),
        }
        if (
            not _SAFE_ID.fullmatch(item["key"])
            or not _E164.fullmatch(item["display_number"])
            or not _SAFE_ID.fullmatch(item["phone_number_id"])
            or not _WORKSPACE.fullmatch(item["workspace_id"])
            or not re.fullmatch(r"[A-Z]{2,8}", item["region"])
            or not all(_ENV_REF.fullmatch(item[key]) for key in ("access_token_env", "app_secret_env", "verify_token_env"))
            or item["phone_number_id"] in seen_ids
        ):
            raise ValueError("invalid_ninaos_numbers_config")
        seen_ids.add(item["phone_number_id"])
        result.append(item)
    return result


def primary_number(region=""):
    numbers = configured_numbers()
    requested = str(region or "").strip().upper()
    if requested:
        regional = [item for item in numbers if item["region"] == requested]
        if regional:
            return next((item for item in regional if item["primary"]), regional[0])
    return next((item for item in numbers if item["primary"]), numbers[0] if numbers else None)


def number_for_phone_id(phone_number_id):
    matches = [item for item in configured_numbers() if item["phone_number_id"] == str(phone_number_id or "")]
    return matches[0] if len(matches) == 1 else None


def whatsapp_url(number):
    digits = re.sub(r"\D", "", str((number or {}).get("display_number") or ""))
    return f"https://wa.me/{quote(digits)}" if digits else ""


def public_contact(number):
    if not number:
        return None
    return {
        "key": number["key"],
        "name": number["name"],
        "region": number["region"],
        "display_number": number["display_number"],
        "whatsapp_url": whatsapp_url(number),
    }


def _sender_digest(number, sender):
    clean_sender = str(sender or "").strip()
    if not re.fullmatch(r"[0-9]{6,20}", clean_sender):
        raise ValueError("invalid_sender")
    material = f"{number['key']}:{number['phone_number_id']}:{clean_sender}".encode()
    return hmac.new(_identity_secret(), material, hashlib.sha256).hexdigest()[:32]


def resolve_sender_identity(number, sender):
    digest = _sender_digest(number, sender)
    return {
        "workspace_id": f"{number['workspace_id']}.contact.{digest}",
        "conversation_id": f"{CHANNEL}:{number['key']}:{digest}",
        "contact_id": f"contact_{digest}",
    }


def verify_token(mode, supplied):
    if mode != "subscribe" or not supplied:
        return False
    matches = []
    for number in configured_numbers():
        expected = (os.environ.get(number["verify_token_env"]) or "").strip()
        if expected and hmac.compare_digest(expected, str(supplied)):
            matches.append(number["key"])
    return len(matches) == 1


def verify_signature(number, raw_body, supplied):
    secret = (os.environ.get(number["app_secret_env"]) or "").strip()
    if not secret:
        raise WhatsAppProviderError("secret_not_configured")
    expected = "sha256=" + hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return bool(supplied) and hmac.compare_digest(str(supplied), expected)


def send_reply(number, recipient, text, requester=None):
    token = (os.environ.get(number["access_token_env"]) or "").strip()
    if not token:
        raise WhatsAppProviderError("secret_not_configured")
    return send_cloud_api_message(number["phone_number_id"], token, recipient, text, requester=requester)
