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
        or re.search(r"\b\d{1,2}[./-]\d{1,2}(?:[./-]\d{2,4})?\b", value)
        or re.search(
            r"\b\d{1,2}\.?(?:\s+)(?:janvār|janvar|februār|februar|mart|aprīl|april|"
            r"maij|jūnij|junij|jūlij|julij|august|septembr|oktobr|novembr|decembr)",
            value,
        )
        or any(marker in value for marker in _TIME_MARKERS)
    )


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

    reminder = any(marker in value for marker in _REMINDER_MARKERS)
    has_time = _has_clock_or_date(value)
    remember = any(marker in value for marker in _MEMORY_MARKERS)
    birthday_or_event = any(marker in value for marker in (
        "dzimšanas dien", "dzimsanas dien", "jubilej", "appointment", "vizīte", "vizite",
        "zobārst", "zobarst", "dentist", "ārst", "arst", "doctor",
    ))
    work = reminder or birthday_or_event or any(marker in value for marker in _WORK_MARKERS)
    follow_up = any(marker in value for marker in _FOLLOW_UP_MARKERS)
    high = any(marker in value for marker in _HIGH_PRIORITY_MARKERS)

    if reminder and not has_time:
        return Decision(
            reply_required=True, remember=remember,
            needs_clarification=True, priority="high" if high else "normal",
            confidence=0.98, reason="reminder_time_missing",
        )
    if reminder:
        return Decision(
            reply_required=True, remember=True,
            create_work_object=True, create_reminder=True,
            priority="high" if high else "normal",
            confidence=0.98, reason="scheduled_reminder",
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
