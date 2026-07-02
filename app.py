"""
followup_engine.py
NinaOS Follow-up Engine — V1.1

V1.1:
- ne tikai pārbauda esošu task;
- pats atpazīst follow-up tekstu;
- izveido task objektu, lai tas neaiziet vecajā memory/reminder plūsmā.

Piemērs:
piektdien jāpajautā Andrim par atbildi
"""

FOLLOWUP_ENGINE_VERSION = "Follow-up Engine V1.1"


def _clean(text):
    return (text or "").strip()


def _lower(text):
    return _clean(text).lower()


def is_followup_text(text):
    lower = _lower(text)

    if not lower:
        return False

    markers = [
        "jāpajautā", "japajauta",
        "pajautā", "pajauta",
        "pārjautā", "parjauta",
        "jāatgādina", "jaatgadina",
        "atgādināt", "atgadinat",
        "jāsazvana", "jasazvana",
        "sazvanīt", "sazvanit",
        "vēlreiz", "velreiz",
        "par atbildi",
        "par piedāvājumu", "par piedavajumu",
        "par rēķinu", "par rekinu",
        "follow-up", "follow up", "followup",
    ]

    return any(m in lower for m in markers)


def detect_deadline(text):
    lower = _lower(text)

    if "šodien" in lower or "sodien" in lower:
        return "today"
    if "rīt" in lower or "rit" in lower:
        return "tomorrow"
    if "parīt" in lower or "parit" in lower:
        return "day_after_tomorrow"

    weekdays = {
        "pirmdien": "monday",
        "otrdien": "tuesday",
        "trešdien": "wednesday",
        "tresdien": "wednesday",
        "ceturtdien": "thursday",
        "piektdien": "friday",
        "sestdien": "saturday",
        "svētdien": "sunday",
        "svetdien": "sunday",
    }

    for lv, code in weekdays.items():
        if lv in lower:
            return code

    return ""


def deadline_label(code):
    labels = {
        "today": "šodien",
        "tomorrow": "rīt",
        "day_after_tomorrow": "parīt",
        "monday": "pirmdien",
        "tuesday": "otrdien",
        "wednesday": "trešdien",
        "thursday": "ceturtdien",
        "friday": "piektdien",
        "saturday": "sestdien",
        "sunday": "svētdien",
    }
    return labels.get(code or "", "")


def normalize_person_name(name):
    raw = _clean(name).strip(" .,!?:;")
    if not raw:
        return ""

    known = {
        "andrim": "Andris",
        "andri": "Andris",
        "andris": "Andris",
        "annai": "Anna",
        "anna": "Anna",
        "jānim": "Jānis",
        "janim": "Jānis",
        "jānis": "Jānis",
        "janis": "Jānis",
    }

    lower = raw.lower()
    if lower in known:
        return known[lower]

    if lower.endswith("im") and len(raw) > 4:
        return raw[:-2].capitalize() + "is"
    if lower.endswith("am") and len(raw) > 4:
        return raw[:-2].capitalize() + "s"
    if lower.endswith("ai") and len(raw) > 4:
        return raw[:-2].capitalize() + "a"

    return raw[:1].upper() + raw[1:]


def detect_client(text):
    raw = _clean(text)
    lower = raw.lower()

    words = raw.split()
    for word in words:
        w = word.strip(" .,!?:;")
        lw = w.lower()
        if lw in ["andrim", "andris", "annai", "anna", "jānim", "janim", "janis", "jānis"]:
            return normalize_person_name(w)

    for marker in ["klientam ", "klientei ", "klientu ", "klients "]:
        if marker in lower:
            idx = lower.find(marker) + len(marker)
            tail = raw[idx:].strip(" .,!?:;")
            if tail:
                return normalize_person_name(tail.split()[0])

    return ""


def detect_followup_task(text):
    raw = _clean(text)

    if not is_followup_text(raw):
        return None

    deadline = detect_deadline(raw)

    return {
        "type": "task",
        "title": raw[:120],
        "raw_text": raw,
        "client": detect_client(raw),
        "deadline": deadline,
        "deadline_label": deadline_label(deadline),
        "priority": "normal",
        "priority_label": "normāla",
        "status": "open",
        "status_label": "atvērts",
        "followup": True,
        "work_type": "followup",
        "source": "telegram",
        "version": FOLLOWUP_ENGINE_VERSION,
    }


def is_followup_task(task):
    if (task or {}).get("followup") is True:
        return True

    title = _lower((task or {}).get("title", ""))
    raw_text = _lower((task or {}).get("raw_text", ""))
    return is_followup_text(f"{title} {raw_text}")


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


def build_followup_saved_answer(task):
    if not task:
        return ""

    lines = [
        "🔁 Piefiksēju follow-up darbu. ✅",
        "",
        f"Uzdevums: {task.get('title', '')}",
    ]

    if task.get("client"):
        lines.append(f"Klients: {task.get('client')}")

    if task.get("deadline_label"):
        lines.append(f"Termiņš: {task.get('deadline_label')}")

    lines.append("Tips: follow-up / atkārtots kontakts")
    lines.append("")
    lines.append("Tas nozīmē, ka Nina šo uztvers kā sekošanu klientam, nevis parastu piezīmi.")
    lines.append("")
    lines.append(f"Versija: {FOLLOWUP_ENGINE_VERSION}")

    return "\n".join(lines)


def build_followup_status_answer():
    return (
        "🔁 Follow-up Engine V1.1 ir aktīvs. ✅\n\n"
        "Mērķis: follow-up tekstu pārvērst par īstu uzdevumu.\n\n"
        "Tests:\n"
        "piektdien jāpajautā Andrim par atbildi\n\n"
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
        f"Versija: {FOLLOWUP_ENGINE_VERSION}"
    )
