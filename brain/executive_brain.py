"""Deterministic V1 message classification for the ONE NINA Brain."""

from __future__ import annotations

import re

from .decision import Decision

_ACKNOWLEDGEMENTS = {
    "ok", "okay", "labi", "skaidrs", "paldies", "thanks", "thank you",
    "saprotu", "darīts", "done",
}
_REMINDER_MARKERS = (
    "atgādini", "atgadin", "remind me", "reminder", "atgādināj",
)
_TIME_MARKERS = (
    "šodien", "sodien", "rīt", "rit", "parīt", "parit", "tomorrow", "today", "pēc ", "pec ",
    "pirmdien", "otrdien", "trešdien", "tresdien", "ceturtdien", "piektdien",
    "sestdien", "svētdien", "svetdien", "nākam", "nakam", "at ",
)
_MEMORY_MARKERS = (
    "atceries", "iegaumē", "iegaume", "man jāatceras", "man jaatceras",
    "remember that", "remember my", "paturi prātā", "paturi prata",
)
_WORK_MARKERS = (
    "jāizdara", "jaizdara", "jānosūta", "janosuta", "jāpiezvana", "japiezvana",
    "piezvanīt", "piezvanit", "nosūtīt", "nosutit", "sagatavot", "izdarīt",
    "izdarit", "jāsagatavo", "jasagatavo", "task", "todo", "follow up", "follow-up",
)
_HIGH_PRIORITY_MARKERS = (
    "steidzami", "urgent", "svarīgi", "svarigi", "critical", "kritisk",
    "dzimšanas dien", "dzimsanas dien", "jubilej",
)
_FOLLOW_UP_MARKERS = (
    "seko līdzi", "seko lidzi", "follow up", "follow-up", "pajautā statusu",
    "pajauta statusu", "gaidu atbildi",
)

_CANCEL_ALL_REMINDERS = (
    "novāc visus atgādinājumus", "novac visus atgadinajumus",
    "izdzēs visus reminderus", "izdzes visus reminderus",
    "izdzēs visus atgādinājumus", "izdzes visus atgadinajumus",
    "cancel all reminders",
)

def _normalized(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip()).casefold()


def _plain_acknowledgement(value: str) -> bool:
    return re.sub(r"[^\wāčēģīķļņšūž]+", "", value, flags=re.UNICODE) in {
        re.sub(r"[^\wāčēģīķļņšūž]+", "", item, flags=re.UNICODE)
        for item in _ACKNOWLEDGEMENTS
    }


def _has_clock_or_date(value: str) -> bool:
    return bool(
        re.search(r"\b(?:[01]?\d|2[0-3])[:.]\d{2}\b", value)
        or re.search(r"\b\d{4}-\d{2}-\d{2}(?:[ t]\d{1,2}[:.]\d{2})?\b", value)
        or re.search(r"\b\d{1,2}[./-]\d{1,2}(?:[./-]\d{2,4})?\b", value)
        or re.search(
            r"\b\d{1,2}\.?(?:\s+)(?:janvār|janvar|februār|februar|mart|aprīl|april|"
            r"maij|jūnij|junij|jūlij|julij|august|septembr|oktobr|novembr|decembr)",
            value,
        )
        or any(marker in value for marker in _TIME_MARKERS)
    )


def _has_reminder_time(value: str) -> bool:
    """A day alone is not a delivery time; relative durations are complete."""
    return bool(
        re.search(r"\b(?:[01]?\d|2[0-3])[:.]\d{2}\b", value)
        or re.search(r"\b\d{4}-\d{2}-\d{2}[ t](?:[01]?\d|2[0-3])[:.]\d{2}\b", value)
        or re.search(r"\bp(?:ē|e)c\s+(?:(?:\d+|vienas?|div(?:ā|a)m?|tr(?:ī|i)m?)\s+)?(?:stund|min)", value)
    )


def _starts_with_time(value: str) -> bool:
    return bool(
        re.match(
            r"^(?:p(?:ē|e)c\s+|šodien\b|sodien\b|rīt\b|rit\b|parīt\b|parit\b|"
            r"(?:nākam\w*|nakam\w*)\s+|pirmdien\b|otrdien\b|trešdien\b|tresdien\b|"
            r"ceturtdien\b|piektdien\b|sestdien\b|svētdien\b|svetdien\b|\d{4}-\d{2}-\d{2}\b)",
            value,
        )
    )


def _reminder_query_operation(value: str) -> str:
    """Classify reminder questions by grammar before create detection."""
    reminder_reference = bool(re.search(r"\b(?:atgādinājum|atgadinajum|reminder)", value))
    reminder_verb = bool(re.search(r"\b(?:jāatgādina|jaatgadina|atgādināsi|atgadinasi)\b", value))
    list_request = bool(re.search(
        r"\b(?:kādi|kadi|parādi|paradi|nosauc|uzskaiti|list|show)\b",
        value,
    ))
    if reminder_reference and list_request:
        return "LIST"
    period_reference = bool(re.search(
        r"\b(?:pa\s+dienu|pusdien|dienā|vakara|vakarā|rītā|no\s+rīta|midday|afternoon|evening|morning)\b",
        value,
    ))
    question_request = "?" in value or bool(re.search(r"\b(?:kas|ko|what)\b", value))
    if (reminder_reference or reminder_verb) and period_reference and question_request:
        return "ASK"
    return ""


def classify_message(message: str) -> Decision:
    value = _normalized(message)
    if not value:
        return Decision(
            reply_required=False, needs_clarification=True,
            confidence=1.0, reason="empty_message",
        )
    if _plain_acknowledgement(value):
        return Decision(
            reply_required=False, no_action=True, priority="low",
            confidence=0.99, reason="acknowledgement_no_action",
        )

    if value in _CANCEL_ALL_REMINDERS:
        return Decision(
            reply_required=True, confidence=1.0,
            reason="cancel_all_reminders", reminder_operation="CANCEL",
        )

    reminder_query = _reminder_query_operation(value)
    if reminder_query == "LIST":
        return Decision(
            reply_required=True, confidence=0.99,
            reason="reminder_list", reminder_operation="LIST",
        )

    if reminder_query == "ASK":
        return Decision(
            reply_required=True, confidence=0.98,
            reason="reminder_ask", reminder_operation="ASK",
        )

    has_time = _has_clock_or_date(value)
    remember = any(marker in value for marker in _MEMORY_MARKERS)
    reminder = (
        any(marker in value for marker in _REMINDER_MARKERS)
        or (remember and has_time)
        or (has_time and _starts_with_time(value) and "?" not in value)
    )
    birthday_or_event = any(marker in value for marker in (
        "dzimšanas dien", "dzimsanas dien", "jubilej", "appointment", "vizīte", "vizite",
        "zobārst", "zobarst", "dentist", "ārst", "arst", "doctor",
    ))
    work = reminder or birthday_or_event or any(marker in value for marker in _WORK_MARKERS)
    follow_up = any(marker in value for marker in _FOLLOW_UP_MARKERS)
    high = any(marker in value for marker in _HIGH_PRIORITY_MARKERS)

    if reminder and not _has_reminder_time(value):
        return Decision(
            reply_required=True, remember=remember,
            create_work_object=True, create_reminder=True,
            needs_clarification=True, priority="high" if high else "normal",
            confidence=0.98, reason="reminder_time_missing",
            reminder_operation="CREATE",
        )
    if reminder:
        return Decision(
            reply_required=True, remember=True,
            create_work_object=True, create_reminder=True,
            priority="high" if high else "normal",
            confidence=0.98, reason="scheduled_reminder",
            reminder_operation="CREATE",
        )
    if birthday_or_event:
        return Decision(
            reply_required=True, remember=remember or "dzim" in value or "jubilej" in value,
            create_work_object=True, create_reminder=has_time,
            priority="high" if high else "normal",
            confidence=0.96, reason="remembered_personal_event",
        )
    if follow_up:
        return Decision(
            reply_required=True, create_work_object=True, follow_up=True,
            priority="high" if high else "normal", confidence=0.94,
            reason="follow_up_request",
        )
    if work:
        return Decision(
            reply_required=True, create_work_object=True,
            priority="high" if high else "normal", confidence=0.92,
            reason="work_request",
        )
    if remember:
        return Decision(
            reply_required=True, remember=True,
            priority="high" if high else "normal", confidence=0.94,
            reason="memory_request",
        )
    return Decision(confidence=0.75, reason="general_reply")
