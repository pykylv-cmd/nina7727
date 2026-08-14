"""NinaOS Initiative Engine V1.

Deterministic, read-only initiative candidates over existing ONE NINA data.
This module never changes Work Objects, sends messages, creates reminders, or
invokes an AI provider.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import re
from typing import Iterable, Optional

from work_objects import WorkObject, list_work_objects


INITIATIVE_ENGINE_VERSION = "Initiative Engine V1"
_CLOSED_STATUSES = frozenset({
    "archived", "cancelled", "closed", "completed", "done", "paid",
    "rejected",
})
_PRIORITY_POINTS = {"low": 2, "normal": 6, "high": 14, "urgent": 22}


@dataclass(frozen=True)
class InitiativeCandidate:
    initiative_id: str
    workspace_id: str
    work_object_id: str
    type: str
    reason: str
    score: int
    created_at: str

    def as_dict(self):
        return {
            "initiative_id": self.initiative_id,
            "workspace_id": self.workspace_id,
            "work_object_id": self.work_object_id,
            "type": self.type,
            "reason": self.reason,
            "score": self.score,
            "created_at": self.created_at,
        }


def _utc(value: Optional[datetime] = None) -> datetime:
    value = value or datetime.now(timezone.utc)
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _timestamp(value) -> Optional[datetime]:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = datetime.strptime(text[:10], "%Y-%m-%d")
        except ValueError:
            return None
    return _utc(parsed)


def _number(value, minimum=0, maximum=10) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return minimum
    return max(minimum, min(number, maximum))


def _metadata(item: WorkObject) -> dict:
    return item.metadata if isinstance(item.metadata, dict) else {}


def _relationship_value(item: WorkObject) -> int:
    metadata = _metadata(item)
    details = metadata.get("business_details")
    details = details if isinstance(details, dict) else {}
    explicit = metadata.get("relationship_value", details.get("relationship_value"))
    if explicit is not None:
        return _number(explicit)
    relationship = str(
        metadata.get("relationship")
        or metadata.get("relation")
        or details.get("relationship")
        or ""
    ).casefold()
    if relationship in {"client", "owner", "partner", "important"}:
        return 7
    return 4 if item.client_id else 0


def initiative_score(
    item: WorkObject,
    initiative_type: str,
    *,
    now: Optional[datetime] = None,
) -> int:
    """Return the deterministic V1 score for one detected candidate."""
    current = _utc(now)
    due_at = _timestamp(item.due_date)
    metadata = _metadata(item)
    score = 10  # confidence for a rule-backed detector
    score += _PRIORITY_POINTS.get(str(item.priority).casefold(), 6)
    score += _relationship_value(item)
    score += _number(metadata.get("initiative_priority"))

    if initiative_type == "overdue" and due_at:
        overdue_days = max(1, (current.date() - due_at.date()).days)
        score += 40 + min(overdue_days, 15)
    elif initiative_type == "today_priority":
        score += 28
    elif initiative_type == "deadline_upcoming" and due_at:
        hours = max(0, int((due_at - current).total_seconds() // 3600))
        score += 24 if hours <= 24 else 16
    elif initiative_type == "follow_up_waiting":
        score += 24
    elif initiative_type == "inactive_client":
        score += 20
    elif initiative_type == "relationship_signal":
        score += 12
    return score


def _candidate(
    item: WorkObject,
    initiative_type: str,
    reason: str,
    now: datetime,
) -> InitiativeCandidate:
    return InitiativeCandidate(
        initiative_id=f"initiative:{item.workspace_id}:{item.object_id}:{initiative_type}",
        workspace_id=item.workspace_id,
        work_object_id=item.object_id,
        type=initiative_type,
        reason=reason,
        score=initiative_score(item, initiative_type, now=now),
        created_at=now.isoformat(),
    )


def detect_initiatives(
    workspace_id: str,
    *,
    objects: Optional[Iterable[WorkObject]] = None,
    now: Optional[datetime] = None,
) -> tuple[InitiativeCandidate, ...]:
    """Detect candidates without mutating any source module or source object."""
    workspace = str(workspace_id or "").strip()
    if not workspace:
        raise ValueError("workspace_id is required")
    current = _utc(now)
    source = list(objects) if objects is not None else list_work_objects(
        workspace_id=workspace, limit=1000,
    )
    found = {}

    for item in source:
        if item.workspace_id != workspace:
            continue
        status = str(item.status or "").casefold()
        if status in _CLOSED_STATUSES:
            continue
        due_at = _timestamp(item.due_date)
        metadata = _metadata(item)

        proposals = []
        if due_at and due_at < current:
            proposals.append(("overdue", f"Overdue since {due_at.date().isoformat()}"))
        elif due_at and due_at.date() == current.date():
            proposals.append(("today_priority", "Due today"))
        elif due_at and due_at <= current + timedelta(days=7):
            proposals.append((
                "deadline_upcoming",
                f"Deadline approaching on {due_at.date().isoformat()}",
            ))

        waiting = (
            item.object_type in {"followup_task", "follow_up"}
            and status in {"open", "scheduled", "waiting"}
        ) or status == "waiting"
        if waiting:
            proposals.append(("follow_up_waiting", "Follow-up is waiting for attention"))

        if item.object_type == "client":
            last_activity = _timestamp(
                metadata.get("last_activity_at") or item.updated_at
            )
            if status == "inactive" or (
                last_activity and last_activity < current - timedelta(days=30)
            ):
                proposals.append(("inactive_client", "Client has been inactive for 30+ days"))

        if _relationship_value(item) >= 7 and metadata.get("relationship_signal"):
            proposals.append((
                "relationship_signal",
                str(metadata["relationship_signal"])[:240],
            ))

        for initiative_type, reason in proposals:
            candidate = _candidate(item, initiative_type, reason, current)
            found[candidate.initiative_id] = candidate

    return tuple(sorted(
        found.values(),
        key=lambda item: (-item.score, item.created_at, item.initiative_id),
    ))


def initiative_queue(
    workspace_id: str,
    *,
    limit: int = 20,
    objects: Optional[Iterable[WorkObject]] = None,
    now: Optional[datetime] = None,
) -> tuple[InitiativeCandidate, ...]:
    safe_limit = max(0, min(int(limit), 100))
    return detect_initiatives(
        workspace_id, objects=objects, now=now,
    )[:safe_limit]


# Legacy Nina conversation adapter. This preserves the established ONE NINA
# command surface while the V1 queue above becomes the canonical detector.
def _task_title(task):
    return str(
        (task or {}).get("title") or (task or {}).get("raw_text") or ""
    ).strip()


def _contains(text, words):
    lower = str(text or "").casefold()
    return any(word in lower for word in words)


def _extract_client_name(text):
    match = re.search(
        r"\b([A-ZĀČĒĢĪĶĻŅŠŪŽ][a-zāčēģīķļņšūž]+)\b",
        str(text or "").strip(),
    )
    return match.group(1) if match else ""


def _score_task(task):
    title = _task_title(task)
    score = 0
    reasons = []
    if _contains(
        title,
        ["piedāvāj", "tāme", "tame", "rēķin", "rekin", "invoice", "offer"],
    ):
        score += 60
        reasons.append("tas ir tuvu naudai / darījumam")
    if _contains(
        title,
        ["jāpajautā", "japajauta", "follow-up", "followup", "atbild",
         "jāzvana", "jazvana"],
    ):
        score += 40
        reasons.append("tas uztur klientu kustībā")
    if _contains(title, ["šodien", "sodien", "tagad"]):
        score += 80
        reasons.append("tam ir tūlītējs termiņš")
    elif _contains(title, ["rīt", "rit"]):
        score += 50
        reasons.append("tam ir tuvākais termiņš")
    elif _contains(
        title,
        ["pirmdien", "otrdien", "trešdien", "tresdien", "ceturtdien",
         "piektdien", "sestdien", "svētdien", "svetdien"],
    ):
        score += 35
        reasons.append("tam ir konkrēts termiņš")
    client = _extract_client_name(title)
    if client:
        score += 15
        reasons.append(f"tas ir saistīts ar klientu: {client}")
    if str((task or {}).get("status") or "open").casefold() in {
        "open", "active", "todo",
    }:
        score += 5
    return score, reasons, client


def _pick_top_tasks(tasks, limit=3):
    ranked = []
    for task in tasks or []:
        title = _task_title(task)
        if not title:
            continue
        score, reasons, client = _score_task(task)
        ranked.append({
            "task": task, "title": title, "score": score,
            "reasons": reasons, "client": client,
        })
    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked[:limit]


def build_initiative_answer(tasks):
    ranked = _pick_top_tasks(tasks, limit=3)
    if not ranked:
        return (
            "🔥 Šobrīd neredzu aktīvu darbu, ko celt kā prioritāti.\n\n"
            "Ja iedosi man uzdevumus vai klientu darbus, es pateikšu, ar ko sākt."
        )
    top = ranked[0]
    lines = ["🔥 Šobrīd svarīgākais", "", f"1. {top['title']}"]
    if top["reasons"]:
        lines.extend(["Kāpēc:"] + [
            f"- {reason}" for reason in top["reasons"][:2]
        ])
    if len(ranked) > 1:
        lines.extend(["", "Pēc tam:", f"2. {ranked[1]['title']}"])
    lines.extend([
        "", "Mans ieteikums:",
        "Sāc ar pirmo punktu, jo tas šobrīd saņem augstāko prioritāti.",
        "", f"Versija: {INITIATIVE_ENGINE_VERSION}",
    ])
    return "\n".join(lines)


def initiative_status_answer():
    return (
        "🔥 Initiative Engine V1 ir aktīvs.\n\n"
        "Tas deterministiski atrod un prioritizē kandidātus no esošajiem "
        "Work Objects. Tas neveic darbības automātiski.\n\n"
        f"Versija: {INITIATIVE_ENGINE_VERSION}"
    )


def is_initiative_command(text):
    return str(text or "").strip().casefold() in {
        "ko man tagad darīt", "kas svarīgākais", "kas svarigakais",
        "ar ko sākt", "ar ko sakt", "ko tu iesaki", "initiative",
        "initiative status", "initiative engine",
    }
