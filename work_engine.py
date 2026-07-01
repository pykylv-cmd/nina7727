"""
work_engine.py
NinaOS Work Engine — V1.0

Mērķis:
Pārvērst uzdevumu sarakstu par darba plānu.

Task Engine = uztver darbus.
Work Engine = sakārto darbus un pasaka, ar ko sākt.

Šis modulis pats nesūta Telegram ziņas.
"""

WORK_ENGINE_VERSION = "Work Engine V1.0"


def _clean(text):
    return (text or "").strip()


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
    tasks = tasks or []
    return sorted(tasks, key=priority_score, reverse=True)


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
        f"🧠 {name}es sakārtoju tavu darba dienu.",
        "",
        f"🔴 Steidzami/svarīgi: {len(high)}",
        f"🟡 Normāli: {len(normal)}",
        f"🟢 Var pagaidīt: {len(low)}",
        "",
    ]

    first = tasks[0]
    lines.append("Prioritāte Nr.1:")
    lines.append(f"{task_type(first)} {first.get('title', 'Bez nosaukuma')}")

    if first.get("client"):
        lines.append(f"Klients/tēma: {first.get('client')}")

    if first.get("deadline_label") or first.get("deadline"):
        lines.append(f"Termiņš: {first.get('deadline_label') or first.get('deadline')}")

    lines.append("")
    lines.append("Mans ieteikums: sāc ar šo vienu darbu. Kad pabeigts, uzraksti: izdarīts.")
    lines.append("Es palīdzēšu noturēt fokusu, nevis tikai glabāšu sarakstu.")
    lines.append("")
    lines.append(f"Versija: {WORK_ENGINE_VERSION}")

    return "\n".join(lines)


def work_engine_status():
    return (
        "🧠 Work Engine V1.0 ir gatavs pieslēgšanai. ✅\n\n"
        "Mērķis: sakārtot uzdevumus pēc svarīguma un pateikt, ar ko sākt.\n\n"
        "Tests pēc pieslēgšanas:\n"
        "sakārto manu dienu\n\n"
        f"Versija: {WORK_ENGINE_VERSION}"
    )
