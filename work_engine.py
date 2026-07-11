"""
work_engine.py
NinaOS Work Engine V1.2.1 — ONE NINA Estimate Approval V1 Release-Safe

Task Engine captures work.
Work Engine turns canonical Work Objects into real work actions.

ONE NINA rules:
- consume the same persistent Work Object;
- consume metadata.business_details as canonical truth;
- never parse Telegram/Web text here;
- persist action output on the same Work Object;
- never create a second estimate object;
- approval changes the action state on that same Work Object.

Release safety:
- this module remains importable during staggered Railway/GitHub deploys;
- when work_objects.py is still V2.2.2, local compatibility helpers use the
  existing get_work_object/update_work_object API without creating new truth.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from reply_builder import build_client_estimate_draft, build_client_reply_draft
from work_objects import get_work_object, list_work_objects, update_work_object

try:
    from work_objects import canonical_action_result as _canonical_action_result
except ImportError:
    _canonical_action_result = None

try:
    from work_objects import canonical_business_details as _canonical_business_details
except ImportError:
    _canonical_business_details = None

try:
    from work_objects import save_canonical_action_result as _save_canonical_action_result
except ImportError:
    _save_canonical_action_result = None

WORK_ENGINE_VERSION = "Work Engine V1.4 — ONE NINA Forwarded Client Reply Action V1"
ESTIMATE_ACTION_KEY = "estimate_draft_v1"
ESTIMATE_ACTION_VERSION = "ONE_NINA_CANONICAL_ESTIMATE_ACTION_V1"
ESTIMATE_APPROVAL_VERSION = "ONE_NINA_ESTIMATE_APPROVAL_V1"
CLIENT_REPLY_ACTION_KEY = "client_reply_draft_v1"
CLIENT_REPLY_ACTION_VERSION = "ONE_NINA_FORWARDED_CLIENT_REPLY_ACTION_V1"
_ALLOWED_APPROVAL_DECISIONS = {"approve", "hold", "reject"}


def _clean(text: Any) -> str:
    return str(text or "").strip()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_business_details(obj) -> Dict[str, Any]:
    if _canonical_business_details is not None:
        return _canonical_business_details(obj)
    if not obj:
        return {}
    metadata = obj.metadata if isinstance(getattr(obj, "metadata", None), dict) else {}
    details = metadata.get("business_details")
    return dict(details) if isinstance(details, dict) else {}


def _read_action_result(obj, action_key: str) -> Dict[str, Any]:
    if _canonical_action_result is not None:
        return _canonical_action_result(obj, action_key)
    if not obj:
        return {}
    metadata = obj.metadata if isinstance(getattr(obj, "metadata", None), dict) else {}
    actions = metadata.get("canonical_actions")
    if not isinstance(actions, dict):
        return {}
    result = actions.get(_clean(action_key))
    return dict(result) if isinstance(result, dict) else {}


def _save_action_result(object_id: str, action_key: str, result: Dict[str, Any]):
    if _save_canonical_action_result is not None:
        return _save_canonical_action_result(object_id, action_key, result)

    obj = get_work_object(object_id)
    if not obj:
        return None
    key = _clean(action_key)
    if not key:
        raise ValueError("action_key is required.")

    metadata = dict(obj.metadata or {})
    actions = metadata.get("canonical_actions")
    actions = dict(actions) if isinstance(actions, dict) else {}
    actions[key] = dict(result or {})
    metadata["canonical_actions"] = actions
    metadata["canonical_action_version"] = "ONE_NINA_CANONICAL_ACTION_V1"
    return update_work_object(obj.object_id, metadata=metadata)


def priority_score(task):
    priority = (task or {}).get("priority", "normal")
    deadline = (task or {}).get("deadline", "")
    score = 0
    if priority == "high":
        score += 100
    elif priority == "normal":
        score += 50
    elif priority == "low":
        score += 10
    if deadline == "today":
        score += 80
    elif deadline == "tomorrow":
        score += 40
    elif deadline:
        score += 20
    return score


def task_type(task):
    text = ((task or {}).get("title") or (task or {}).get("raw_text") or "").lower()
    if any(x in text for x in ["zvan", "jāzvana", "jazvana"]):
        return "📞 Zvans"
    if any(x in text for x in ["e-past", "epast", "email", "atbildēt", "atbildet"]):
        return "✉️ E-pasts"
    if any(x in text for x in ["piedāvāj", "piedavaj"]):
        return "📄 Piedāvājums"
    if any(x in text for x in ["tāme", "tame", "tāmi", "tami"]):
        return "📑 Tāme"
    if any(x in text for x in ["rēķin", "rekin"]):
        return "💰 Rēķins"
    if any(x in text for x in ["dokuments", "līgums", "ligums"]):
        return "📝 Dokuments"
    if any(x in text for x in ["tikšanās", "tiksanas", "sapulce"]):
        return "📅 Tikšanās"
    return "✔️ Darbs"


def sort_tasks(tasks):
    return sorted(tasks or [], key=priority_score, reverse=True)


def work_plan(tasks, user_name=""):
    tasks = sort_tasks(tasks)
    if not tasks:
        return (
            "📋 Šobrīd neredzu aktīvus darbus.\n\n"
            "Uzraksti vienu darbu, piemēram:\n"
            "šodien steidzami jāzvana klientam Andrim\n\n"
            f"Versija: {WORK_ENGINE_VERSION}"
        )

    high = [t for t in tasks if t.get("priority") == "high" or t.get("deadline") == "today"]
    normal = [t for t in tasks if t not in high and t.get("priority", "normal") == "normal"]
    low = [t for t in tasks if t not in high and t.get("priority") == "low"]
    name = f"{user_name}, " if user_name else ""
    lines = [
        f"🧠 {name}es sakārtoju tavu darba dienu.", "",
        f"🔴 Steidzami/svarīgi: {len(high)}",
        f"🟡 Normāli: {len(normal)}",
        f"🟢 Var pagaidīt: {len(low)}", "",
    ]
    first = tasks[0]
    lines.extend(["Prioritāte Nr.1:", f"{task_type(first)} {first.get('title', 'Bez nosaukuma')}"])
    if first.get("client"):
        lines.append(f"Klients/tēma: {first.get('client')}")
    if first.get("deadline_label") or first.get("deadline"):
        lines.append(f"Termiņš: {first.get('deadline_label') or first.get('deadline')}")
    lines.extend([
        "",
        "Mans ieteikums: sāc ar šo vienu darbu. Kad pabeigts, uzraksti: izdarīts.",
        "Es palīdzēšu noturēt fokusu, nevis tikai glabāšu sarakstu.",
        "",
        f"Versija: {WORK_ENGINE_VERSION}",
    ])
    return "\n".join(lines)


def get_estimate_action_result(object_id: str) -> Dict[str, Any]:
    return _read_action_result(get_work_object(object_id), ESTIMATE_ACTION_KEY)


def prepare_canonical_estimate_draft(object_id: str, force: bool = False) -> Dict[str, Any]:
    """Prepare one client-ready draft from one canonical estimate Work Object."""
    obj = get_work_object(object_id)
    if not obj:
        return {"ok": False, "error": "work_object_not_found", "object_id": object_id}
    if _clean(obj.object_type).lower() != "estimate":
        return {
            "ok": False,
            "error": "work_object_is_not_estimate",
            "object_id": obj.object_id,
            "object_type": obj.object_type,
        }

    existing = _read_action_result(obj, ESTIMATE_ACTION_KEY)
    if existing.get("ok") and existing.get("draft_text") and not force:
        return {**existing, "reused": True}

    built = build_client_estimate_draft(_read_business_details(obj))
    if not built.get("ok"):
        return {
            "ok": False,
            "error": built.get("error") or "estimate_draft_build_failed",
            "missing": built.get("missing") or [],
            "object_id": obj.object_id,
            "action_version": ESTIMATE_ACTION_VERSION,
        }

    result = {
        "ok": True,
        "action": "prepare_estimate_draft",
        "action_version": ESTIMATE_ACTION_VERSION,
        "object_id": obj.object_id,
        "object_type": obj.object_type,
        "draft_text": built.get("text") or "",
        "builder": built.get("builder") or "",
        "status": "prepared",
        "approval_state": "pending",
        "prepared_at": _utc_now(),
        "source": "canonical_business_details",
    }
    saved = _save_action_result(obj.object_id, ESTIMATE_ACTION_KEY, result)
    if not saved:
        return {"ok": False, "error": "estimate_action_persistence_failed", "object_id": obj.object_id}
    return result


def decide_canonical_estimate_draft(object_id: str, decision: str) -> Dict[str, Any]:
    """Approve, hold or reject the prepared draft on the same canonical estimate."""
    decision = _clean(decision).lower()
    if decision not in _ALLOWED_APPROVAL_DECISIONS:
        return {
            "ok": False,
            "error": "invalid_approval_decision",
            "decision": decision,
            "allowed": sorted(_ALLOWED_APPROVAL_DECISIONS),
            "object_id": object_id,
        }

    obj = get_work_object(object_id)
    if not obj:
        return {"ok": False, "error": "work_object_not_found", "object_id": object_id}
    if _clean(obj.object_type).lower() != "estimate":
        return {
            "ok": False,
            "error": "work_object_is_not_estimate",
            "object_id": obj.object_id,
            "object_type": obj.object_type,
        }

    current = _read_action_result(obj, ESTIMATE_ACTION_KEY)
    if not current.get("ok") or not _clean(current.get("draft_text")):
        return {
            "ok": False,
            "error": "estimate_draft_not_prepared",
            "object_id": obj.object_id,
        }

    state_map = {
        "approve": ("approved", "approved"),
        "hold": ("hold", "hold"),
        "reject": ("rejected", "rejected"),
    }
    status, approval_state = state_map[decision]
    now = _utc_now()
    result = dict(current)
    result.update({
        "ok": True,
        "status": status,
        "approval_state": approval_state,
        "approval_decision": decision,
        "approval_version": ESTIMATE_APPROVAL_VERSION,
        "decided_at": now,
    })
    if decision == "approve":
        result["approved_at"] = now
    elif decision == "hold":
        result["held_at"] = now
    else:
        result["rejected_at"] = now

    saved = _save_action_result(obj.object_id, ESTIMATE_ACTION_KEY, result)
    if not saved:
        return {"ok": False, "error": "estimate_approval_persistence_failed", "object_id": obj.object_id}
    return result



# =========================================================
# ONE NINA Natural Channel Work Execution V1
# =========================================================

def _fold_text(value: Any) -> str:
    text = _clean(value).lower()
    table = str.maketrans({
        "ā": "a", "č": "c", "ē": "e", "ģ": "g", "ī": "i",
        "ķ": "k", "ļ": "l", "ņ": "n", "š": "s", "ū": "u", "ž": "z",
    })
    return " ".join(text.translate(table).split())


def _is_estimate_prepare_request(user_text: str) -> bool:
    text = _fold_text(user_text)
    if not text:
        return False
    action_terms = ("sagatavo", "uztaisi", "uzraksti", "sastadi", "izveido", "iedod")
    estimate_terms = ("piedavaj", "tame", "estimate", "quote")
    return any(term in text for term in action_terms) and any(term in text for term in estimate_terms)


def _client_matches_text(client_name: str, user_text: str) -> bool:
    client = _fold_text(client_name)
    text = _fold_text(user_text)
    if not client or not text:
        return False
    if client in text:
        return True
    first = client.split()[0]
    stem = first[:-1] if len(first) >= 5 else first
    return len(stem) >= 4 and stem in text


def _production_estimates(workspace_id: str = "demo_small_business") -> List[Any]:
    objects = list_work_objects(workspace_id=workspace_id, object_type="estimate", limit=500)
    result = []
    for obj in objects or []:
        metadata = obj.metadata if isinstance(getattr(obj, "metadata", None), dict) else {}
        source_key = _clean(getattr(obj, "source_key", ""))
        if metadata.get("demo") is True or _clean(metadata.get("source")) == "demo_seed" or source_key.startswith("demo:"):
            continue
        result.append(obj)
    return result


def resolve_canonical_estimate_for_request(
    user_text: str,
    workspace_id: str = "demo_small_business",
) -> Dict[str, Any]:
    """Resolve a natural work command against existing canonical estimates.

    This does not extract a new business truth from channel text. It only resolves
    an action request to an already-persistent canonical Work Object.
    """
    if not _is_estimate_prepare_request(user_text):
        return {"matched": False}

    estimates = _production_estimates(workspace_id=workspace_id)
    matches = []
    for obj in estimates:
        details = _read_business_details(obj)
        client_name = _clean(details.get("client_name") or getattr(obj, "client_id", ""))
        if _client_matches_text(client_name, user_text):
            matches.append(obj)

    if len(matches) == 1:
        return {"matched": True, "ok": True, "object": matches[0]}

    if len(matches) > 1:
        matches.sort(key=lambda obj: _clean(getattr(obj, "updated_at", "")), reverse=True)
        return {"matched": True, "ok": True, "object": matches[0], "resolved_by": "latest_client_estimate"}

    clients = []
    for obj in estimates:
        details = _read_business_details(obj)
        name = _clean(details.get("client_name") or getattr(obj, "client_id", ""))
        if name and name not in clients:
            clients.append(name)

    return {
        "matched": True,
        "ok": False,
        "error": "estimate_not_resolved",
        "clients": clients[:8],
    }


def resolve_canonical_client_name(
    candidate_name: str,
    workspace_id: str = "demo_small_business",
) -> str:
    """Map a channel-visible person name to an existing canonical client name."""
    candidate = _clean(candidate_name)
    if not candidate:
        return ""
    for obj in list_work_objects(workspace_id=workspace_id, limit=500) or []:
        details = _read_business_details(obj)
        client_name = _clean(details.get("client_name") or getattr(obj, "client_id", ""))
        if client_name and (_client_matches_text(client_name, candidate) or _client_matches_text(candidate, client_name)):
            return client_name
    return candidate


def execute_natural_work_request(
    user_text: str,
    workspace_id: str = "demo_small_business",
    channel: str = "telegram",
) -> Optional[Dict[str, Any]]:
    """Execute a natural work command through the same ONE NINA Work Engine.

    Channel is context only. Telegram, WhatsApp and future surfaces must call the
    same function instead of building channel-specific business brains.
    """
    resolved = resolve_canonical_estimate_for_request(user_text, workspace_id=workspace_id)
    if not resolved.get("matched"):
        return None

    if not resolved.get("ok"):
        clients = resolved.get("clients") or []
        if clients:
            message = "Atradu vairākus piedāvājumu darbus, bet nesapratu, kuru klientu domā. Pasaki klienta vārdu: " + ", ".join(clients) + "."
        else:
            message = "Neatradu esošu canonical piedāvājumu, ko sagatavot. Pasaki klientu un piedāvājuma darbu."
        return {"ok": False, "handled": True, "text": message, "error": resolved.get("error", "not_resolved")}

    obj = resolved["object"]
    result = prepare_canonical_estimate_draft(obj.object_id, force=False)
    if not result.get("ok"):
        return {
            "ok": False,
            "handled": True,
            "text": "Atradu piedāvājumu, bet man pietrūkst canonical biznesa detaļu, lai droši sagatavotu tekstu.",
            "object_id": obj.object_id,
            "error": result.get("error", "prepare_failed"),
        }

    details = _read_business_details(obj)
    client_name = _clean(details.get("client_name") or getattr(obj, "client_id", "")) or "klientam"
    draft_text = _clean(result.get("draft_text") or result.get("text"))
    return {
        "ok": True,
        "handled": True,
        "action": ESTIMATE_ACTION_KEY,
        "object_id": obj.object_id,
        "client_name": client_name,
        "channel": _clean(channel) or "unknown",
        "text": draft_text,
        "action_result": result,
    }

def work_engine_status():
    return (
        "🧠 Work Engine V1.2.1 ir aktīvs. ✅\n\n"
        "Canonical estimate Work Object var sagatavot klienta draftu un iziet "
        "Approve / Hold / Reject vārtus tajā pašā Work Object.\n\n"
        f"Versija: {WORK_ENGINE_VERSION}"
    )


def _related_client_work_context(obj, workspace_id: str = "demo_small_business") -> str:
    client_name = _clean(getattr(obj, "client_id", ""))
    if not client_name:
        return ""
    lines = []
    for item in list_work_objects(workspace_id=workspace_id, limit=500) or []:
        if getattr(item, "object_id", "") == getattr(obj, "object_id", ""):
            continue
        details = _read_business_details(item)
        item_client = _clean(details.get("client_name") or getattr(item, "client_id", ""))
        if _fold_text(item_client) != _fold_text(client_name):
            continue
        subject = _clean(details.get("subject"))
        amount = _clean(details.get("amount"))
        currency = _clean(details.get("currency"))
        start_context = _clean(details.get("start_context"))
        parts = [_clean(getattr(item, "object_type", "work"))]
        if subject:
            parts.append(subject)
        if amount:
            parts.append(f"{amount} {currency or 'EUR'}")
        if start_context:
            parts.append(f"darbu sākums: {start_context}")
        lines.append(" · ".join(parts))
    return "\n".join(lines[:8])


def prepare_canonical_client_reply(object_id: str, generator, workspace_id: str = "demo_small_business", force: bool = False) -> Dict[str, Any]:
    """Prepare a send-ready owner reply from one canonical forwarded client_request."""
    obj = get_work_object(object_id)
    if not obj:
        return {"ok": False, "error": "work_object_not_found", "object_id": object_id}
    if _clean(getattr(obj, "object_type", "")).lower() != "client_request":
        return {"ok": False, "error": "work_object_is_not_client_request", "object_id": object_id}
    existing = _read_action_result(obj, CLIENT_REPLY_ACTION_KEY)
    if existing.get("ok") and existing.get("draft_text") and not force:
        return {**existing, "reused": True}
    metadata = obj.metadata if isinstance(getattr(obj, "metadata", None), dict) else {}
    incoming_text = _clean(metadata.get("raw_text") or getattr(obj, "title", ""))
    client_name = _clean(getattr(obj, "client_id", "") or metadata.get("forward_sender_name"))
    related_context = _related_client_work_context(obj, workspace_id=workspace_id)
    built = build_client_reply_draft(client_name, incoming_text, related_context, generator)
    if not built.get("ok"):
        return {"ok": False, "error": built.get("error", "client_reply_build_failed"), "object_id": object_id}
    result = {
        "ok": True,
        "action": "prepare_client_reply_draft",
        "action_version": CLIENT_REPLY_ACTION_VERSION,
        "object_id": obj.object_id,
        "draft_text": built.get("text", ""),
        "status": "prepared",
        "prepared_at": _utc_now(),
        "source": "canonical_client_request",
        "client_name": client_name,
    }
    saved = _save_action_result(obj.object_id, CLIENT_REPLY_ACTION_KEY, result)
    if not saved:
        return {"ok": False, "error": "client_reply_action_persistence_failed", "object_id": object_id}
    return result
