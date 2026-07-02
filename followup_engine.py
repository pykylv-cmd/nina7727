"""
followup_engine.py
NinaOS Follow-up Engine — V1.0

Mērķis:
atpazīt follow-up darbus un palīdzēt NinaOS saprast,
kuri uzdevumi ir atkārtoti kontakti, atgādinājumi vai pārbaudes pēc klienta darba.

Piemēri:
- piektdien jāpajautā Andrim par atbildi
- rīt jāatgādina klientam par rēķinu
- nākamnedēļ jāsazvana Andris vēlreiz
"""

FOLLOWUP_ENGINE_VERSION = "Follow-up Engine V1.0"


def _clean(text):
    return (text or "").strip()


def _lower(text):
    return _clean(text).lower()


def is_followup_task(task):
    title = _lower((task or {}).get("title", ""))
    raw_text = _lower((task or {}).get("raw_text", ""))

    text = f"{title} {raw_text}".strip()

    if not text:
        return False

    markers = [
        "vēlreiz", "velreiz",
        "atgādin", "atgadin",
        "pajautā", "pajauta",
        "pārjautā", "parjauta",
        "sazvana", "zvana vēlreiz", "zvana velreiz",
        "follow up", "follow-up",
        "par atbildi", "par piedāvājumu", "par piedavajumu",
        "par rēķinu", "par rekinu",
    ]

    return any(marker in text for marker in markers)


def enrich_task_with_followup(task):
    task = dict(task or {})

    if is_followup_task(task):
        task["followup"] = True
        task["work_type"] = "followup"
    else:
        task["followup"] = False
        task["work_type"] = task.get("work_type") or "general"

    task["version_followup"] = FOLLOWUP_ENGINE_VERSION
    return task


def build_followup_status_answer():
    return (
        "🔁 Follow-up Engine V1.0 ir aktīvs. ✅\n\n"
        "Mērķis: saprast, kuri uzdevumi ir follow-up darbi, nevis vienkārši jauni darbi.\n\n"
        "Tests:\n"
        "piektdien jāpajautā Andrim par atbildi\n\n"
        "Sagaidāmais rezultāts:\n"
        "Nina saprot, ka tas ir follow-up klientam.\n\n"
        f"Versija: {FOLLOWUP_ENGINE_VERSION}"
    )


def build_followup_context_answer(task):
    enriched = enrich_task_with_followup(task)
    title = _clean(enriched.get("title", ""))
    client = _clean(enriched.get("client", ""))

    if not enriched.get("followup"):
        return (
            "🔁 Šis uzdevums šobrīd neizskatās pēc follow-up darba.\n\n"
            f"Uzdevums: {title or '—'}\n"
            f"Klients: {client or '—'}\n\n"
            f"Versija: {FOLLOWUP_ENGINE_VERSION}"
        )

    return (
        "🔁 Nina atrada follow-up darbu. ✅\n\n"
        f"Uzdevums: {title or '—'}\n"
        f"Klients: {client or '—'}\n"
        "Tips: follow-up / atkārtots kontakts\n\n"
        "Tas nozīmē, ka šo darbu vēlāk varēs atsevišķi rādīt kā sekošanu klientam, nevis kā pilnīgi jaunu uzdevumu.\n\n"
        f"Versija: {FOLLOWUP_ENGINE_VERSION}"
    )
