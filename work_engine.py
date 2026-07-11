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
from typing import Any, Dict

from reply_builder import build_client_estimate_draft
from work_objects import get_work_object, update_work_object

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

WORK_ENGINE_VERSION = "Work Engine V1.2.1 — ONE NINA Estimate Approval V1 Release-Safe"
ESTIMATE_ACTION_KEY = "estimate_draft_v1"
ESTIMATE_ACTION_VERSION = "ONE_NINA_CANONICAL_ESTIMATE_ACTION_V1"
ESTIMATE_APPROVAL_VERSION = "ONE_NINA_ESTIMATE_APPROVAL_V1"
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


def work_engine_status():
    return (
        "🧠 Work Engine V1.2.1 ir aktīvs. ✅\n\n"
        "Canonical estimate Work Object var sagatavot klienta draftu un iziet "
        "Approve / Hold / Reject vārtus tajā pašā Work Object.\n\n"
        f"Versija: {WORK_ENGINE_VERSION}"
    )
