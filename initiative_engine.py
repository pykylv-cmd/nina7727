"""
initiative_engine.py
NinaOS Core 2.6 — Initiative Hardening V1.0

Mērķis:
- izvēlēties nākamo labāko darbu no reālajiem taskiem;
- dot vienu skaidru TOP prioritāti un 1–2 nākamos soļus;
- prioritizēt pēc termiņa, klienta/piedāvājuma tuvuma un follow-up riska.
"""

import re

INITIATIVE_ENGINE_VERSION = "Core 2.6 — Initiative Hardening V1.0"


def _task_title(task):
    return str((task or {}).get("title") or (task or {}).get("raw_text") or "").strip()


def _contains(text, words):
    lower = (text or "").lower()
    return any(w in lower for w in words)


def _extract_client_name(text):
    text = str(text or "").strip()
    m = re.search(r"\b([A-ZĀČĒĢĪĶĻŅŠŪŽ][a-zāčēģīķļņšūž]+)\b", text)
    return m.group(1) if m else ""


def _score_task(task):
    title = _task_title(task)
    lower = title.lower()

    score = 0
    reasons = []

    if _contains(lower, ["piedāvāj", "tāme", "tame", "rēķin", "rekin", "invoice", "offer"]):
        score += 60
        reasons.append("tas ir tuvu naudai / darījumam")

    if _contains(lower, ["jāpajautā", "japajauta", "follow-up", "followup", "atbild", "jāzvana", "jazvana"]):
        score += 40
        reasons.append("tas uztur klientu kustībā")

    if _contains(lower, ["šodien", "sodien", "tagad"]):
        score += 80
        reasons.append("tam ir tūlītējs termiņš")
    elif _contains(lower, ["rīt", "rit"]):
        score += 50
        reasons.append("tam ir tuvākais termiņš")
    elif _contains(lower, ["pirmdien", "otrdien", "trešdien", "tresdien", "ceturtdien", "piektdien", "sestdien", "svētdien", "svetdien"]):
        score += 35
        reasons.append("tam ir konkrēts termiņš")

    client = _extract_client_name(title)
    if client:
        score += 15
        reasons.append(f"tas ir saistīts ar klientu: {client}")

    status = str((task or {}).get("status") or "open").lower()
    if status in ["open", "active", "todo"]:
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
            "task": task,
            "title": title,
            "score": score,
            "reasons": reasons,
            "client": client,
        })

    ranked.sort(key=lambda x: x["score"], reverse=True)
    return ranked[:limit]


def build_initiative_answer(tasks):
    ranked = _pick_top_tasks(tasks, limit=3)

    if not ranked:
        return (
            "🔥 Šobrīd neredzu aktīvu darbu, ko celt kā prioritāti.\n\n"
            "Ja iedosi man uzdevumus vai klientu darbus, es pateikšu, ar ko sākt."
        )

    top = ranked[0]
    second = ranked[1] if len(ranked) > 1 else None

    lines = []
    lines.append("🔥 Šobrīd svarīgākais")
    lines.append("")
    lines.append(f"1. {top['title']}")

    if top["reasons"]:
        lines.append("Kāpēc:")
        for reason in top["reasons"][:2]:
            lines.append(f"- {reason}")

    if second:
        lines.append("")
        lines.append("Pēc tam:")
        lines.append(f"2. {second['title']}")

    lines.append("")
    lines.append("Mans ieteikums:")
    if _contains(top["title"].lower(), ["piedāvāj", "offer", "tāme", "tame"]):
        lines.append("Sāc ar piedāvājumu/tāmi — tas šobrīd ir vistuvāk rezultātam un naudai.")
    elif _contains(top["title"].lower(), ["jāpajautā", "japajauta", "follow-up", "followup", "atbild"]):
        lines.append("Sāc ar follow-up — tas notur klientu kustībā un neļauj sarunai atdzist.")
    else:
        lines.append("Sāc ar pirmo punktu, jo tas šobrīd saņem augstāko prioritāti pēc termiņa un klienta svara.")

    lines.append("")
    lines.append("Pēc tam vari rakstīt:")
    lines.append("- klienti")
    lines.append("- mani uzdevumi")
    lines.append("- mana diena")
    lines.append("")
    lines.append(f"Versija: {INITIATIVE_ENGINE_VERSION}")
    return "\n".join(lines)


def initiative_status_answer():
    return (
        "🔥 Core 2.6 — Initiative Hardening V1.0 ir aktīvs.\n\n"
        "Ko tas dara:\n"
        "• izvēlas TOP prioritāti no reālajiem taskiem;\n"
        "• ņem vērā termiņu, piedāvājumu un follow-up svaru;\n"
        "• dod vienu skaidru nākamo soli, nevis tikai vispārīgu sarakstu.\n\n"
        "Testi:\n"
        "• ko man tagad darīt\n"
        "• kas svarīgākais\n"
        "• ar ko sākt\n\n"
        f"Versija: {INITIATIVE_ENGINE_VERSION}"
    )


def is_initiative_command(text):
    lower = (text or "").strip().lower()
    return lower in {
        "ko man tagad darīt",
        "kas svarīgākais",
        "kas svarigakais",
        "ar ko sākt",
        "ar ko sakt",
        "ko tu iesaki",
        "initiative",
        "initiative status",
        "initiative engine",
    }
