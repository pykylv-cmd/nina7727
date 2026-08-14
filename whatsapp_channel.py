"""Meta WhatsApp Cloud API adapter for NinaOS channels.

Provider calls and webhook validation live here; Nina message routing does not.
"""

import hashlib
import hmac
import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from channel_connections import (
    decrypt_channel_credential,
    encrypt_channel_credential,
    finalize_whatsapp_onboarding,
    get_connection,
    get_secret_references,
    list_whatsapp_connections,
    mark_whatsapp_webhook_verified,
    update_whatsapp_verification,
)


GRAPH_API_VERSION = (os.environ.get("WHATSAPP_GRAPH_API_VERSION") or "v25.0").strip()
_SAFE_ID = re.compile(r"^[A-Za-z0-9_.:-]{3,128}$")
_RECIPIENT = re.compile(r"^[0-9]{6,20}$")


class WhatsAppProviderError(RuntimeError):
    def __init__(self, code, status=None):
        super().__init__(code)
        self.code = str(code or "provider_unavailable")
        self.status = status


def _secret(reference):
    stored = str(reference or "").strip()
    value = decrypt_channel_credential(stored) if stored.startswith("enc:v1:") else (os.environ.get(stored) or "").strip()
    if not value:
        raise WhatsAppProviderError("secret_not_configured")
    return value


def embedded_signup_public_config():
    """Return only non-secret identifiers required by Meta's browser SDK."""
    app_id = (os.environ.get("WHATSAPP_META_APP_ID") or "").strip()
    config_id = (os.environ.get("WHATSAPP_EMBEDDED_SIGNUP_CONFIG_ID") or "").strip()
    if not _SAFE_ID.fullmatch(app_id) or not _SAFE_ID.fullmatch(config_id):
        raise WhatsAppProviderError("onboarding_not_configured")
    return {"app_id": app_id, "config_id": config_id}


def _exchange_embedded_signup_code(code, requester=None):
    clean_code = str(code or "").strip()
    app_id = (os.environ.get("WHATSAPP_META_APP_ID") or "").strip()
    app_secret = (os.environ.get("WHATSAPP_META_APP_SECRET") or "").strip()
    if not clean_code or len(clean_code) > 2048 or not app_id or not app_secret:
        raise WhatsAppProviderError("onboarding_not_configured")
    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/oauth/access_token"
    payload = {"client_id": app_id, "client_secret": app_secret, "code": clean_code}
    result = requester("POST", url, "", payload) if requester else _request_oauth_json(url, payload)
    token = str(result.get("access_token") or "").strip()
    if not token:
        raise WhatsAppProviderError("authorization_failed")
    return token


def complete_embedded_signup(workspace_id, code, phone_number_id, business_account_id, business_portfolio_id="", requester=None):
    """Exchange Meta's code, verify returned assets, subscribe webhooks, and connect once."""
    phone_id = str(phone_number_id or "").strip()
    waba_id = str(business_account_id or "").strip()
    portfolio_id = str(business_portfolio_id or "").strip()
    if not _SAFE_ID.fullmatch(phone_id) or not _SAFE_ID.fullmatch(waba_id) or (portfolio_id and not _SAFE_ID.fullmatch(portfolio_id)):
        raise WhatsAppProviderError("invalid_provider_identity")
    token = _exchange_embedded_signup_code(code, requester=requester)
    call = requester or _request_json
    base = f"https://graph.facebook.com/{GRAPH_API_VERSION}"
    phone = call("GET", f"{base}/{quote(phone_id)}?{urlencode({'fields': 'id,display_phone_number,verified_name,quality_rating,name_status'})}", token, None)
    phone_list = call("GET", f"{base}/{quote(waba_id)}/phone_numbers?{urlencode({'fields': 'id'})}", token, None)
    ids = {str(item.get("id")) for item in phone_list.get("data", []) if isinstance(item, dict)}
    if str(phone.get("id") or "") != phone_id or phone_id not in ids:
        raise WhatsAppProviderError("provider_identity_mismatch")
    call("POST", f"{base}/{quote(waba_id)}/subscribed_apps", token, {})
    safe = {
        "display_phone_number": str(phone.get("display_phone_number") or "")[:64],
        "business_display_name": str(phone.get("verified_name") or "")[:160],
        "quality_rating": str(phone.get("quality_rating") or "")[:40],
        "name_status": str(phone.get("name_status") or "")[:40],
    }
    try:
        encrypted = encrypt_channel_credential(token)
        return finalize_whatsapp_onboarding(workspace_id, phone_id, waba_id, encrypted, safe)
    except ValueError as exc:
        raise WhatsAppProviderError(str(exc)) from None


def _request_json(method, url, access_token, payload=None, timeout=12):
    body = json.dumps(payload, separators=(",", ":")).encode() if payload is not None else None
    request = Request(url, data=body, method=method, headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read(1024 * 1024)
            data = json.loads(raw.decode("utf-8")) if raw else {}
            if not isinstance(data, dict):
                raise WhatsAppProviderError("invalid_provider_response", getattr(response, "status", None))
            return data
    except HTTPError as exc:
        raise WhatsAppProviderError("credentials_or_provider_request_rejected", getattr(exc, "code", None)) from None
    except (URLError, TimeoutError, OSError, json.JSONDecodeError):
        raise WhatsAppProviderError("provider_unavailable") from None


def _request_oauth_json(url, payload, timeout=12):
    body = urlencode(payload).encode()
    request = Request(url, data=body, method="POST", headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urlopen(request, timeout=timeout) as response:
            result = json.loads(response.read(1024 * 1024).decode("utf-8"))
            if not isinstance(result, dict):
                raise WhatsAppProviderError("invalid_provider_response", getattr(response, "status", None))
            return result
    except HTTPError as exc:
        raise WhatsAppProviderError("authorization_failed", getattr(exc, "code", None)) from None
    except (URLError, TimeoutError, OSError, json.JSONDecodeError):
        raise WhatsAppProviderError("provider_unavailable") from None


def verify_whatsapp_connection(workspace_id, requester=None):
    connection = get_connection(workspace_id, "whatsapp")
    metadata = connection.get("metadata") or {}
    phone_id = str(metadata.get("phone_number_id") or "")
    business_id = str(metadata.get("business_account_id") or "")
    if not _SAFE_ID.fullmatch(phone_id) or not _SAFE_ID.fullmatch(business_id):
        update_whatsapp_verification(workspace_id, False, error_code="configuration_incomplete")
        raise WhatsAppProviderError("configuration_incomplete")
    references = get_secret_references(workspace_id, "whatsapp")
    token = _secret(references.get("access_token"))
    call = requester or _request_json
    base = f"https://graph.facebook.com/{GRAPH_API_VERSION}"
    try:
        phone = call("GET", f"{base}/{quote(phone_id)}?{urlencode({'fields': 'id,display_phone_number,verified_name,quality_rating,name_status'})}", token)
        business = call("GET", f"{base}/{quote(business_id)}?{urlencode({'fields': 'id,name'})}", token)
        phone_list = call("GET", f"{base}/{quote(business_id)}/phone_numbers?{urlencode({'fields': 'id'})}", token)
        ids = {str(item.get("id")) for item in phone_list.get("data", []) if isinstance(item, dict)}
        if str(phone.get("id")) != phone_id or str(business.get("id")) != business_id or phone_id not in ids:
            raise WhatsAppProviderError("provider_identity_mismatch")
    except WhatsAppProviderError as exc:
        update_whatsapp_verification(workspace_id, False, error_code=exc.code)
        raise
    safe = {
        "display_phone_number": str(phone.get("display_phone_number") or "")[:64],
        "business_display_name": str(phone.get("verified_name") or business.get("name") or "")[:160],
        "quality_rating": str(phone.get("quality_rating") or "")[:40],
        "name_status": str(phone.get("name_status") or "")[:40],
        "provider_verified": True,
    }
    return update_whatsapp_verification(workspace_id, True, safe)


def resolve_webhook_verification(mode, verify_token):
    if mode != "subscribe" or not verify_token:
        return None
    matches = []
    for connection in list_whatsapp_connections({"pending", "connected", "error"}):
        refs = get_secret_references(connection["workspace_id"], "whatsapp")
        configured = (os.environ.get(refs.get("webhook_verify_token", "")) or "").strip()
        if configured and hmac.compare_digest(configured, str(verify_token)):
            matches.append(connection["workspace_id"])
    if len(matches) != 1:
        return None
    mark_whatsapp_webhook_verified(matches[0])
    return matches[0]


def verify_webhook_signature(workspace_id, raw_body, signature_header):
    refs = get_secret_references(workspace_id, "whatsapp")
    app_secret = _secret(refs.get("app_secret"))
    supplied = str(signature_header or "").strip()
    expected = "sha256=" + hmac.new(app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return bool(supplied) and hmac.compare_digest(supplied, expected)


def parse_inbound_text(payload):
    if not isinstance(payload, dict) or payload.get("object") != "whatsapp_business_account":
        raise ValueError("invalid_payload")
    entries = payload.get("entry")
    if not isinstance(entries, list) or not entries or len(entries) > 20:
        raise ValueError("invalid_payload")
    messages = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("invalid_payload")
        for change in entry.get("changes") or []:
            if not isinstance(change, dict) or change.get("field") != "messages":
                continue
            value = change.get("value")
            if not isinstance(value, dict) or value.get("messaging_product") != "whatsapp":
                raise ValueError("invalid_payload")
            metadata = value.get("metadata") or {}
            phone_id = str(metadata.get("phone_number_id") or "")
            if not _SAFE_ID.fullmatch(phone_id):
                raise ValueError("invalid_payload")
            for message in value.get("messages") or []:
                if not isinstance(message, dict) or message.get("type") != "text":
                    continue
                sender = str(message.get("from") or "")
                message_id = str(message.get("id") or "")
                text = str((message.get("text") or {}).get("body") or "").strip()
                if not _RECIPIENT.fullmatch(sender) or not message_id or not text or len(text) > 4000:
                    raise ValueError("invalid_payload")
                messages.append({"phone_number_id": phone_id, "sender": sender, "message_id": message_id[:256], "text": text})
    if not messages or len(messages) > 20:
        raise ValueError("no_supported_messages")
    return messages


def resolve_workspace_for_phone_number(phone_number_id):
    matches = [item for item in list_whatsapp_connections({"connected"}) if str((item.get("metadata") or {}).get("phone_number_id")) == str(phone_number_id)]
    return matches[0]["workspace_id"] if len(matches) == 1 else None


def send_whatsapp_message(workspace_id, recipient, text, requester=None):
    connection = get_connection(workspace_id, "whatsapp")
    if connection["status"] != "connected":
        raise WhatsAppProviderError("channel_not_connected")
    recipient = str(recipient or "").strip()
    clean = str(text or "").strip()
    if not _RECIPIENT.fullmatch(recipient) or not clean or len(clean) > 4096:
        raise WhatsAppProviderError("invalid_outbound_message")
    phone_id = str((connection.get("metadata") or {}).get("phone_number_id") or "")
    refs = get_secret_references(workspace_id, "whatsapp")
    token = _secret(refs.get("access_token"))
    return send_cloud_api_message(phone_id, token, recipient, clean, requester=requester)


def send_cloud_api_message(phone_number_id, access_token, recipient, text, requester=None):
    """Provider transport shared by isolated WhatsApp channel adapters."""
    phone_id = str(phone_number_id or "").strip()
    token = str(access_token or "").strip()
    recipient = str(recipient or "").strip()
    clean = str(text or "").strip()
    if not _SAFE_ID.fullmatch(phone_id) or not token:
        raise WhatsAppProviderError("channel_not_configured")
    if not _RECIPIENT.fullmatch(recipient) or not clean or len(clean) > 4096:
        raise WhatsAppProviderError("invalid_outbound_message")
    call = requester or _request_json
    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{quote(phone_id)}/messages"
    response = call("POST", url, token, {"messaging_product": "whatsapp", "recipient_type": "individual", "to": recipient, "type": "text", "text": {"preview_url": False, "body": clean}})
    message_items = response.get("messages") or []
    message_id = str(message_items[0].get("id") or "") if message_items and isinstance(message_items[0], dict) else ""
    if not message_id:
        raise WhatsAppProviderError("invalid_provider_response")
    return {"ok": True, "message_id": message_id[:256]}
