"""
initiative_engine.py
NinaOS Initiative Engine — V1.0

Mērķis:
- Nina pati pasaka, kas šobrīd svarīgākais;
- no aktīvajiem uzdevumiem izceļ 1–3 prioritātes;
- dod īsu cilvēkam saprotamu ieteikumu.

Šis modulis nemaina datubāzi.
Tas tikai analizē jau esošos taskus.
"""

INITIATIVE_ENGINE_VERSION = "Initiative Engine V1.0"


def _clean(text):
    return (text or "").strip()


def _lower(text):
    return _clean(text).lower()


def _contains_any(text, phrases):
    lower = _lower(text)
    return any(p in lower for p in phrases)


def initiative_status_answer():
    return (
        "🔥 Initiative Engine V1.0 ir aktīvs. ✅\n\n"
        "Uzdevums:\n"
        "- paskatīties uz aktīvajiem darbiem;\n"
        "- izcelt 1–3 svarīgākos soļus;\n"
        "- dot īsu ieteikumu, ar ko sākt.\n\n"
        "Komandas:\n"
        "- ko man tagad darīt\n"
        "- kas svarīgākais\n"
        "- ko iesaki\n"
        "- ninas ieteikums\n\n"
        f"Versija: {INITIATIVE_ENGINE_VERSION}"
    )


def is_initiative_command(text):
    lower = _lower(text)
    return lower in [
        "ko man tagad darīt",
        "ko man tagad darit",
        "kas svarīgākais",
        "kas svarigakais",
        "kas tagad svarīgākais",
        "kas tagad svarigakais",
        "ko iesaki",
        "ko tu iesaki",
        "ninas ieteikums",
        "nina ieteikums",
        "initiative",
        "initiative engine",
    ]


def task_text(task):
    if isinstance(task, dict):
        return _clean(task.get("title") or task.get("text") or task.get("task") or task.get("raw_text") or "")
    return _clean(str(task or ""))


def task_client(task):
    if isinstance(task, dict):
        return _clean(task.get("client", ""))
    return ""


def task_deadline_label(task):
    if isinstance(task, dict):
        return _clean(task.get("deadline_label", "")) or _clean(task.get("deadline", ""))
    return ""


def is_offer_task(text):
    return _contains_any(text, [
        "piedāvājums", "piedavajums",
        "jānosūta", "janosuta",
        "nosūtīt", "nosutit",
        "sagatavot piedāvājumu", "sagatavot piedavajumu",
    ])


def is_reminder_task(text):
    return _contains_any(text, [
        "jāpajautā", "japajauta",
        "pajautāt", "pajautat",
        "par atbildi",
        "atgādināt", "atgadinat",
        "follow-up", "follow up", "followup",
    ])


def deadline_score(deadline):
    d = _lower(deadline)
    if d in ["šodien", "sodien", "today"]:
        return 90
    if d in ["rīt", "rit", "tomorrow"]:
        return 75
    if d in ["parīt", "parit", "day_after_tomorrow"]:
        return 55
    if d:
        return 35
    return 0


def priority_score(task):
    text = task_text(task)
    deadline = task_deadline_label(task)

    score = 0
    reasons = []

    if is_offer_task(text):
        score += 120
        reasons.append("tas virza klientu tuvāk darījumam")

    if deadline:
        ds = deadline_score(deadline)
        score += ds
        if deadline in ["šodien", "sodien", "today"]:
            reasons.append("termiņš ir šodien")
        elif deadline in ["rīt", "rit", "tomorrow"]:
            reasons.append("termiņš ir rīt")
        else:
            reasons.append(f"ir termiņš: {deadline}")

    if is_reminder_task(text):
        score += 60
        reasons.append("tas ir klienta atgādinājuma darbs")

    client = task_client(task)
    if client:
        score += 20
        reasons.append(f"tas ir saistīts ar klientu {client}")

    if not reasons:
        reasons.append("tas ir aktīvs darbs")

    return score, reasons


def ranked_tasks(tasks, limit=3):
    scored = []
    seen = set()

    for task in tasks or []:
        text = task_text(task)
        if not text:
            continue

        key = text.lower()
        if key in seen:
            continue
        seen.add(key)

        score, reasons = priority_score(task)
        scored.append({
            "task": task,
            "text": text,
            "score": score,
            "reasons": reasons,
            "client": task_client(task),
            "deadline": task_deadline_label(task),
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:int(limit or 3)]


def build_initiative_answer(tasks):
    top = ranked_tasks(tasks, limit=3)

    if not top:
        return (
            "🔥 Šobrīd neredzu aktīvus darbus, no kuriem izvēlēties prioritāti.\n\n"
            "Iedod vienu īstu darbu, piemēram:\n"
            "rīt jānosūta piedāvājums Andrim\n\n"
            f"Versija: {INITIATIVE_ENGINE_VERSION}"
        )

    lines = []
    lines.append("🔥 Šobrīd svarīgākais")
    lines.append("")

    for idx, item in enumerate(top, start=1):
        lines.append(f"{idx}. {item['text']}")
        if item["reasons"]:
            lines.append(f"Kāpēc: {item['reasons'][0]}.")
        lines.append("")

    first = top[0]["text"]

    lines.append("Mans ieteikums:")
    if is_offer_task(first):
        lines.append("Sāc ar piedāvājumu, jo tas ir vistuvāk naudas un klienta virzībai.")
    elif is_reminder_task(first):
        lines.append("Sāc ar atgādinājumu klientam, lai darbs neiestrēgst.")
    else:
        lines.append("Sāc ar pirmo punktu — tas šobrīd izskatās svarīgākais.")

    lines.append("")
    lines.append("Pēc tam vari rakstīt:")
    lines.append("- klienti")
    lines.append("- mani uzdevumi")
    lines.append("- kam jānosūta piedāvājums")
    lines.append("")
    lines.append(f"Versija: {INITIATIVE_ENGINE_VERSION}")

    return "\n".join(lines)
