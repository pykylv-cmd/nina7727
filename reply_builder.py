"""
reply_builder.py
NinaOS Reply Builder V1.2 — ONE NINA Client Deliverable Privacy

Central communication layer for NinaOS.
Business actions pass structured canonical context into this module.
The Reply Builder does not extract Telegram/Web text and does not persist work truth.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, Iterable

from initiative_engine import InitiativeCandidate
from rolepack_system import RolePackError, action_for_workspace
from work_objects import WorkObject, list_work_objects

REPLY_BUILDER_VERSION = "Reply Builder V1.2 — ONE NINA Client Deliverable Privacy"
APP_VERSION = "V116.6 + ONE NINA Forwarded Work Intake V1.1"

SUGGESTED_ACTIONS = frozenset({
    "FOLLOW_UP", "REMIND", "CHECK_IN", "ASK_FOR_UPDATE", "NO_ACTION",
})

_VERSION_PATTERNS = [
    r"\n{0,2}Versija:\s*V[0-9.]+\s*$",
    r"\n{0,2}Versija:\s*V[0-9.]+\s*\+\s*Core\s*2\.5\.1\s*$",
    r"\n{0,2}Versija:\s*V[0-9.]+\s*\+\s*.*$",
]


@dataclass(frozen=True)
class ReplyDraft:
    reply_id: str
    initiative_id: str
    workspace_id: str
    work_object_id: str
    title: str
    draft_message: str
    suggested_action: str
    reason: str
    confidence: float
    created_at: str

    def as_dict(self):
        return {
            "reply_id": self.reply_id,
            "initiative_id": self.initiative_id,
            "workspace_id": self.workspace_id,
            "work_object_id": self.work_object_id,
            "title": self.title,
            "draft_message": self.draft_message,
            "suggested_action": self.suggested_action,
            "reason": self.reason,
            "confidence": self.confidence,
            "created_at": self.created_at,
        }


def _initiative_value(initiative, name):
    if isinstance(initiative, dict):
        return initiative.get(name)
    return getattr(initiative, name, None)


def _initiative_work_object(initiative) -> WorkObject | None:
    workspace_id = str(_initiative_value(initiative, "workspace_id") or "").strip()
    work_object_id = str(
        _initiative_value(initiative, "work_object_id") or ""
    ).strip()
    if not workspace_id or not work_object_id:
        return None
    return next((
        item for item in list_work_objects(workspace_id=workspace_id, limit=1000)
        if item.object_id == work_object_id
    ), None)


def _suggested_action(initiative_type: str, item: WorkObject) -> str:
    initiative_type = str(initiative_type or "").casefold()
    if initiative_type == "follow_up_waiting":
        return "FOLLOW_UP"
    if initiative_type == "inactive_client":
        return "CHECK_IN"
    if initiative_type == "relationship_signal":
        return "CHECK_IN"
    if initiative_type == "overdue":
        return "ASK_FOR_UPDATE" if item.client_id else "REMIND"
    if initiative_type in {"today_priority", "deadline_upcoming"}:
        return "REMIND"
    return "NO_ACTION"


def _client_name(item: WorkObject) -> str:
    metadata = item.metadata if isinstance(item.metadata, dict) else {}
    details = metadata.get("business_details")
    details = details if isinstance(details, dict) else {}
    return str(
        details.get("client_name") or metadata.get("client_name")
        or item.client_id or ""
    ).strip()


def _draft_message(action: str, item: WorkObject) -> str:
    client_name = _client_name(item)
    greeting = f"Labdien, {client_name}!" if client_name else "Labdien!"
    title = str(item.title or "šo jautājumu").strip()
    if action == "FOLLOW_UP":
        return f"{greeting} Vēlos sekot līdzi jautājumam “{title}”. Vai ir jaunumi?"
    if action == "ASK_FOR_UPDATE":
        return f"{greeting} Vēlos precizēt aktuālo statusu jautājumam “{title}”."
    if action == "CHECK_IN":
        return f"{greeting} Vēlos apjautāties, kā Jums šobrīd klājas un vai varu palīdzēt."
    if action == "REMIND":
        return f"Atgādinājums: {title}."
    return ""


def _reply_confidence(initiative, item: WorkObject, action: str) -> float:
    try:
        initiative_score = int(_initiative_value(initiative, "score") or 0)
    except (TypeError, ValueError):
        initiative_score = 0
    confidence = 0.55 + min(max(initiative_score, 0), 100) / 500
    if _client_name(item):
        confidence += 0.08
    if item.due_date:
        confidence += 0.05
    if action == "NO_ACTION":
        confidence -= 0.15
    return round(max(0.0, min(confidence, 0.95)), 2)


class ReplyBuilder:
    """Deterministic read-only drafts for Initiative Engine candidates."""

    @staticmethod
    def build(initiative) -> ReplyDraft:
        initiative_id = str(
            _initiative_value(initiative, "initiative_id") or ""
        ).strip()
        workspace_id = str(
            _initiative_value(initiative, "workspace_id") or ""
        ).strip()
        work_object_id = str(
            _initiative_value(initiative, "work_object_id") or ""
        ).strip()
        if not initiative_id or not workspace_id or not work_object_id:
            raise ValueError("initiative identity is required")
        item = _initiative_work_object(initiative)
        if item is None:
            raise ValueError("initiative work object not found in workspace")
        initiative_type = str(
            _initiative_value(initiative, "type") or ""
        ).strip()
        action = _suggested_action(initiative_type, item)
        if action not in SUGGESTED_ACTIONS:
            action = "NO_ACTION"
        try:
            _definition, rolepack = action_for_workspace(
                workspace_id, action,
            )
            if rolepack is None:
                fallback, fallback_rolepack = action_for_workspace(
                    workspace_id, "NO_ACTION",
                )
                if fallback is None or fallback_rolepack is None:
                    raise ValueError("rolepack_action_not_allowed")
                action = "NO_ACTION"
        except RolePackError:
            raise
        except Exception:
            # During additive rolling deploys, an older schema can still be
            # serving. Readiness blocks the new runtime until migration, while
            # legacy unit fixtures retain the canonical pre-RolePack action.
            pass
        return ReplyDraft(
            reply_id=f"reply:{initiative_id}",
            initiative_id=initiative_id,
            workspace_id=workspace_id,
            work_object_id=work_object_id,
            title=item.title,
            draft_message=_draft_message(action, item),
            suggested_action=action,
            reason=str(_initiative_value(initiative, "reason") or "").strip(),
            confidence=_reply_confidence(initiative, item, action),
            created_at=str(
                _initiative_value(initiative, "created_at") or ""
            ).strip(),
        )


def build_reply_queue(
    initiatives: Iterable[InitiativeCandidate],
) -> tuple[ReplyDraft, ...]:
    """Build one stable draft per initiative and suppress duplicate candidates."""
    replies = {}
    for initiative in initiatives or ():
        reply = ReplyBuilder.build(initiative)
        replies[reply.reply_id] = reply
    return tuple(replies[key] for key in sorted(replies))


def rb_clean_text(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    for pattern in _VERSION_PATTERNS:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def rb_detect_intent(text: str) -> str:
    lower = (text or "").strip().lower()
    if not lower:
        return "empty"
    if any(x in lower for x in ["premium", "abonements", "pirkt", "cena", "tarifs"]):
        return "business"
    if any(x in lower for x in [
        "klienti", "andri", "andris", "piedāvājums", "piedavajums",
        "follow-up", "followup", "jāpajautā", "japajauta"
    ]):
        return "client_work"
    if any(x in lower for x in ["mana diena", "darba inbox", "ko man šodien", "ko man sodien"]):
        return "daily_brief"
    if any(x in lower for x in ["ko man tagad", "kas svarīgākais", "ko iesaki"]):
        return "initiative"
    if any(x in lower for x in ["core", "ninaos", "initiative", "think engine", "learning", "quality", "reply builder"]):
        return "ninaos_core"
    if any(x in lower for x in ["čau", "cau", "sveika", "sveiks", "hello", "hi", "kā tev iet", "ka tev iet"]):
        return "conversation"
    return "general"


def rb_detect_tone(text: str) -> str:
    lower = (text or "").strip().lower()
    if any(x in lower for x in ["smagi", "grūti", "gruti", "slikti", "noguris", "nogurusi", "bēdīgi", "bedigi"]):
        return "supportive"
    if any(x in lower for x in ["premium", "cena", "tarifs", "pirkt", "abonements"]):
        return "commercial_warm"
    if any(x in lower for x in ["core", "ninaos", "architecture", "arhitekt", "engine"]):
        return "architectural"
    return "warm"


def build_reply_object(main_message="", user_text="", source="legacy_router", intent="", tone="", channel="telegram", metadata=None):
    return {
        "intent": intent or rb_detect_intent(user_text or main_message),
        "tone": tone or rb_detect_tone(user_text or main_message),
        "priority": "normal",
        "identity": "Nina — AI darbiniece NinaOS platformā",
        "main_message": main_message or "",
        "channel": channel or "telegram",
        "metadata": metadata or {"source": source},
    }


def reply_builder_build(reply_object):
    if isinstance(reply_object, str):
        reply_object = build_reply_object(main_message=reply_object)
    if not isinstance(reply_object, dict):
        reply_object = build_reply_object(main_message=str(reply_object or ""))

    text = rb_clean_text(reply_object.get("main_message", ""))
    if not text:
        text = "Esmu te. 😊\n\nPasaki, ko vajag sakārtot, un es palīdzēšu soli pa solim."

    channel = (reply_object.get("channel") or "telegram").lower()
    if channel == "telegram" and len(text) > 3800:
        text = text[:3700].rstrip() + "\n\n…"

    if not reply_object.get("client_deliverable"):
        text = rb_clean_text(text).rstrip() + f"\n\nVersija: {APP_VERSION}"

    return {
        "text": text,
        "buttons": [],
        "attachments": [],
        "actions": [],
        "metadata": {
            "builder": REPLY_BUILDER_VERSION,
            "intent": reply_object.get("intent", ""),
            "tone": reply_object.get("tone", ""),
            **(reply_object.get("metadata") or {}),
        },
    }


def reply_builder_text(text, user_text="", source="legacy_router", channel="telegram"):
    obj = build_reply_object(
        main_message=text,
        user_text=user_text,
        source=source,
        channel=channel,
    )
    return reply_builder_build(obj).get("text", "")


def _display_amount(value: Any) -> str:
    if value in (None, ""):
        return ""
    try:
        number = float(value)
        if number.is_integer():
            return f"{int(number):,}".replace(",", " ")
        return f"{number:,.2f}".replace(",", " ")
    except (TypeError, ValueError):
        return str(value).strip()


def build_client_estimate_draft(business_details: Dict[str, Any]) -> Dict[str, Any]:
    """Build a client-ready estimate draft from canonical structured fields only."""
    details = dict(business_details or {})
    client_name = str(details.get("client_name") or "").strip()
    subject = str(details.get("subject") or "").strip()
    currency = str(details.get("currency") or "EUR").strip().upper()
    start_context = str(details.get("start_context") or "").strip()
    amount = _display_amount(details.get("amount"))

    missing = []
    if not client_name:
        missing.append("client_name")
    if not subject:
        missing.append("subject")
    if not amount:
        missing.append("amount")

    if missing:
        return {
            "ok": False,
            "error": "missing_canonical_business_details",
            "missing": missing,
            "text": "",
            "builder": REPLY_BUILDER_VERSION,
        }

    lines = [
        f"Labdien, {client_name}!",
        "",
        f"Sagatavojām piedāvājumu par {subject}.",
        f"Kopējā piedāvājuma summa ir {amount} {currency}.",
    ]
    if start_context:
        lines.extend(["", f"Darbus varam uzsākt {start_context}."])
    lines.extend([
        "",
        "Ja piedāvājums Jums ir pieņemams, dodiet ziņu, un vienosimies par nākamajiem soļiem.",
        "",
        "Ar cieņu",
    ])

    reply_object = build_reply_object(
        main_message="\n".join(lines),
        source="canonical_estimate_action_v1",
        intent="client_estimate_draft",
        tone="professional_warm",
        channel="client_deliverable",
        metadata={"source": "canonical_estimate_action_v1"},
    )
    reply_object["client_deliverable"] = True
    built = reply_builder_build(reply_object)
    return {
        "ok": True,
        "text": built["text"],
        "builder": REPLY_BUILDER_VERSION,
        "missing": [],
    }


def reply_builder_status_answer():
    return reply_builder_text(
        "🧩 Reply Builder ir aktīvs kā ONE NINA centrālais komunikācijas slānis. ✅\n\n"
        "Canonical estimate actions var nodot strukturētus business_details un saņemt klientam gatavu draftu.",
        source="reply_builder_status",
    )


def clean_client_deliverable_text(value: Any) -> str:
    """Return text safe to hand directly to a client: no NinaOS/AI/version markers."""
    text = rb_clean_text(value)
    blocked_prefixes = ("versija:", "one nina", "ninaos", "reply builder", "work engine")
    lines = []
    for line in text.splitlines():
        if line.strip().lower().startswith(blocked_prefixes):
            continue
        lines.append(line)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def build_client_reply_prompt(client_name: str, incoming_text: str, related_work_context: str = "") -> str:
    """Central ONE NINA communication prompt for a client-ready reply draft."""
    return f"""
Tu esi Nina, neredzams darba palīgs uzņēmuma īpašniekam.
Sagatavo TIKAI gatavu ziņu, ko īpašnieks var pārsūtīt klientam kā savu atbildi.
Klients nedrīkst redzēt vai nojaust Ninu, AI, NinaOS, versiju vai tehnisko sistēmu.
Neraksti ievadu, paskaidrojumu, analīzi vai frāzi 'te ir atbilde'.
Neizdomā datumus, cenas, solījumus vai faktus, kuru nav dotajā kontekstā.
Raksti dabiski, īsi un profesionāli latviski.

Klients: {client_name or 'nav droši zināms'}
Klienta ziņa:
{incoming_text}

Saistītais canonical darba konteksts:
{related_work_context or 'nav'}

Atdod tikai klientam sūtāmo ziņu.
""".strip()


def build_client_reply_draft(client_name: str, incoming_text: str, related_work_context: str, generator) -> Dict[str, Any]:
    """Build a client-ready reply using the central communication layer and a supplied ONE NINA generator."""
    incoming = rb_clean_text(incoming_text)
    if not incoming:
        return {"ok": False, "error": "missing_incoming_text", "text": ""}
    prompt = build_client_reply_prompt(client_name, incoming, related_work_context)
    try:
        raw = generator(prompt)
    except Exception as exc:
        return {"ok": False, "error": "client_reply_generation_failed", "detail": repr(exc), "text": ""}
    text = clean_client_deliverable_text(raw)
    if not text:
        return {"ok": False, "error": "empty_client_reply", "text": ""}
    return {"ok": True, "text": text, "builder": REPLY_BUILDER_VERSION}
