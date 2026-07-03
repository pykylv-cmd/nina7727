"""
daily_brief.py
NinaOS Daily Brief / Work Inbox — V1.0

Mērķis:
- vienā darba skatā parādīt, kas šobrīd jādara;
- apvienot uzdevumus, klientus, piedāvājumus, atgādinājumus un Ninas ieteikumu;
- kļūt par pamatu Telegram galvenajai komandai, web dashboard un mobile app home screen.

Šis modulis nemaina datubāzi.
Tas tikai analizē jau esošos taskus.
"""

DAILY_BRIEF_VERSION = "Daily Brief / Work Inbox V1.0"


def _clean(text):
    return (text or "").strip()


def _lower(text):
    return _clean(text).lower()


def _contains_any(text, phrases):
    lower = _lower(text)
    return any(p in lower for p in phrases)


def is_daily_brief_command(text):
    lower = _lower(text)
    return lower in [
        "mana diena",
        "ko man šodien darīt",
        "ko man sodien darit",
        "ko man šodien darit",
        "ko man sodien darīt",
        "darba inbox",
        "work inbox",
        "daily brief",
        "šodienas plāns",
        "sodienas plans",
        "dienas plāns",
        "dienas plans",
        "mans darba galds",
        "darba galds",
    ]


def daily_brief_status_answer():
    return (
        "📅 Daily Brief / Work Inbox V1.0 ir aktīvs. ✅\n\n"
        "Uzdevums:\n"
        "- vienā skatā parādīt svarīgākos darbus;\n"
        "- izcelt klientus kustībā;\n"
        "- parādīt piedāvājumus, atgādinājumus un riskus;\n"
        "- dot Ninas ieteikumu, ar ko sākt.\n\n"
        "Komandas:\n"
        "- mana diena\n"
        "- ko man šodien darīt\n"
        "- darba inbox\n"
        "- šodienas plāns\n\n"
        f"Versija: {DAILY_BRIEF_VERSION}"
    )


def task_text(task):
    if isinstance(task, dict):
        return _clean(task.get("title") or task.get("text") or task.get("task") or task.get("raw_text") or "")
    return _clean(str(task or ""))


def task_client(task):
    if isinstance(task, dict):
        return _clean(task.get("client", ""))
    return ""


def task_deadline(task):
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
    deadline = task_deadline(task)
    score = 0

    if is_offer_task(text):
        score += 120
    if deadline:
        score += deadline_score(deadline)
    if is_reminder_task(text):
        score += 60
    if task_client(task):
        score += 20

    return score


def unique_tasks(tasks):
    result = []
    seen = set()
    for task in tasks or []:
        text = task_text(task)
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(task)
    return result


def top_priority_tasks(tasks, limit=3):
    items = unique_tasks(tasks)
    items.sort(key=priority_score, reverse=True)
    return items[:int(limit or 3)]


def offer_tasks(tasks):
    return [t for t in unique_tasks(tasks) if is_offer_task(task_text(t))]


def reminder_tasks(tasks):
    return [t for t in unique_tasks(tasks) if is_reminder_task(task_text(t))]


def client_summary(tasks):
    clients = {}
    for task in unique_tasks(tasks):
        client = task_client(task)
        text = task_text(task)

        if not client:
            lower = text.lower()
            if any(x in lower for x in ["andris", "andri", "andrim"]):
                client = "Andris"
            elif any(x in lower for x in ["jānis", "janis", "jāni", "jani", "jānim", "janim"]):
                client = "Jānis"
            elif any(x in lower for x in ["anna", "annu", "annai"]):
                client = "Anna"

        if not client:
            continue

        info = clients.setdefault(client, {
            "client": client,
            "task_count": 0,
            "has_offer": False,
            "has_reminder": False,
            "next_step": "",
        })

        info["task_count"] += 1
        if is_offer_task(text):
            info["has_offer"] = True
            if not info["next_step"]:
                info["next_step"] = text
        if is_reminder_task(text):
            info["has_reminder"] = True
            if not info["next_step"]:
                info["next_step"] = text
        if not info["next_step"]:
            info["next_step"] = text

    return list(clients.values())


def client_status_text(client):
    if client.get("has_offer"):
        return "jānosūta piedāvājums"
    if client.get("has_reminder"):
        return "jāatgādina"
    return "aktīvs darbs"


def build_daily_brief_answer(tasks):
    tasks = unique_tasks(tasks)

    if not tasks:
        return (
            "📅 Tava darba diena\n\n"
            "Šobrīd Nina neredz aktīvus darbus vai klientu uzdevumus.\n\n"
            "Lai sāktu, uzraksti vienu īstu darbu, piemēram:\n"
            "rīt jānosūta piedāvājums Andrim\n\n"
            f"Versija: {DAILY_BRIEF_VERSION}"
        )

    top = top_priority_tasks(tasks, limit=3)
    offers = offer_tasks(tasks)
    reminders = reminder_tasks(tasks)
    clients = client_summary(tasks)

    lines = []
    lines.append("📅 Tava darba diena")
    lines.append("")

    lines.append("🔥 Šodien svarīgākais:")
    if top:
        for i, task in enumerate(top, 1):
            lines.append(f"{i}. {task_text(task)}")
    else:
        lines.append("Šobrīd nav skaidras prioritātes.")
    lines.append("")

    lines.append("👥 Klienti kustībā:")
    if clients:
        for client in clients[:5]:
            lines.append(f"- {client['client']} — {client_status_text(client)}")
    else:
        lines.append("- šobrīd nav redzamu klientu darbu")
    lines.append("")

    lines.append("📨 Piedāvājumi:")
    if offers:
        for task in offers[:5]:
            lines.append(f"- {task_text(task)}")
    else:
        lines.append("- šobrīd nav klientu, kam jānosūta piedāvājums")
    lines.append("")

    lines.append("🔁 Atgādinājumi:")
    if reminders:
        for task in reminders[:5]:
            lines.append(f"- {task_text(task)}")
    else:
        lines.append("- šobrīd nav atgādinājumu darbu")
    lines.append("")

    lines.append("⚠️ Riski:")
    # V1.0 bez datumu matemātikas: ja aktīvajiem klientiem nav nākamā soļa, tas būtu risks.
    # Tā kā šeit taski jau ir next step, šobrīd rādām mierīgu stāvokli.
    lines.append("- šobrīd nav redzamu iestrēgumu")
    lines.append("")

    lines.append("🔥 Ninas ieteikums:")
    if top:
        first = task_text(top[0])
        if is_offer_task(first):
            lines.append("Sāc ar piedāvājumu — tas šobrīd visvairāk virza klientu uz rezultātu.")
        elif is_reminder_task(first):
            lines.append("Sāc ar atgādinājumu klientam, lai darbs neiestrēgst.")
        else:
            lines.append("Sāc ar pirmo punktu, jo tas šobrīd izskatās svarīgākais.")
    else:
        lines.append("Iedod vienu konkrētu darbu, un es palīdzēšu sakārtot dienu.")
    lines.append("")

    lines.append("Ātrās komandas:")
    lines.append("- klienti")
    lines.append("- kas notiek ar Andri")
    lines.append("- ko man tagad darīt")
    lines.append("")
    lines.append(f"Versija: {DAILY_BRIEF_VERSION}")

    return "\n".join(lines)
