"""
work_engine.py
NinaOS Work Engine V1.1 — ONE NINA Canonical Estimate Action V1

Task Engine captures work.
Work Engine turns canonical Work Objects into real work actions.

ONE NINA rules:
- consume the same persistent Work Object;
- consume metadata.business_details as canonical truth;
- never parse Telegram/Web text here;
- persist action output on the same Work Object;
- never create a second estimate object.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from reply_builder import build_client_estimate_draft
from work_objects import (
    canonical_action_result,
    canonical_business_details,
    get_work_object,
    save_canonical_action_result,
)

WORK_ENGINE_VERSION = "Work Engine V1.1 — ONE NINA Canonical Estimate Action V1"
ESTIMATE_ACTION_KEY = "estimate_draft_v1"
ESTIMATE_ACTION_VERSION = "ONE_NINA_CANONICAL_ESTIMATE_ACTION_V1"


def _clean(text):
    return (text or "").strip()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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
    high = [t for t in tasks if (t.get("priority") == "high" or t.get("deadline") == "today")]
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
    lines.extend(["", "Mans ieteikums: sāc ar šo vienu darbu. Kad pabeigts, uzraksti: izdarīts.",
                  "Es palīdzēšu noturēt fokusu, nevis tikai glabāšu sarakstu.", "",
                  f"Versija: {WORK_ENGINE_VERSION}"])
    return "\n".join(lines)


def get_estimate_action_result(object_id: str) -> Dict[str, Any]:
    obj = get_work_object(object_id)
    return canonical_action_result(obj, ESTIMATE_ACTION_KEY)


def prepare_canonical_estimate_draft(object_id: str, force: bool = False) -> Dict[str, Any]:
    """Perform estimate work on one canonical estimate Work Object."""
    obj = get_work_object(object_id)
    if not obj:
        return {"ok": False, "error": "work_object_not_found", "object_id": object_id}
    if str(obj.object_type or "").strip().lower() != "estimate":
        return {
            "ok": False,
            "error": "work_object_is_not_estimate",
            "object_id": obj.object_id,
            "object_type": obj.object_type,
        }

    existing = canonical_action_result(obj, ESTIMATE_ACTION_KEY)
    if existing.get("ok") and existing.get("draft_text") and not force:
        return {**existing, "reused": True}

    details = canonical_business_details(obj)
    built = build_client_estimate_draft(details)
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
        "prepared_at": _utc_now(),
        "source": "canonical_business_details",
    }
    saved = save_canonical_action_result(obj.object_id, ESTIMATE_ACTION_KEY, result)
    if not saved:
        return {"ok": False, "error": "estimate_action_persistence_failed", "object_id": obj.object_id}
    return result


def work_engine_status():
    return (
        "🧠 Work Engine V1.1 ir aktīvs. ✅\n\n"
        "Canonical estimate Work Object var pārvērst klientam gatavā piedāvājuma draftā, "
        "izmantojot to pašu metadata.business_details un saglabājot rezultātu tajā pašā Work Object.\n\n"
        f"Versija: {WORK_ENGINE_VERSION}"
    )
