"""
work_layer.py
Nina Work Layer V1.1 — Smart Message Mode

Mērķis:
- pārvērst klienta darba snapshotu praktiskās darba sagatavēs;
- sagatavot piedāvājuma tekstu, follow-up ziņu un zvana plānu;
- strādāt virs esošajiem Task / Follow-up / Client Work / Initiative slāņiem;
- nemainīt datubāzi un neizdomāt klientus, ja tie nav tekstā vai darba atmiņā.
"""

import re

WORK_LAYER_VERSION = "Nina Work Layer V1.1 — Smart Message Mode"


def _clean(value):
    return str(value or "").strip()


def _lower(value):
    return _clean(value).lower()


def _task_text(task):
    if isinstance(task, dict):
        return _clean(task.get("title") or task.get("text") or task.get("task") or task.get("raw_text") or "")
    return _clean(task)


def _task_client(task):
    if isinstance(task, dict):
        return _normalize_client(task.get("client", ""))
    return ""


def _normalize_client(name):
    raw = _clean(name).strip(" .,!?:;\"'")
    if not raw:
        return ""
    known = {
        "andris": "Andris",
        "andri": "Andris",
        "andrim": "Andris",
        "andriu": "Andris",
        "jānis": "Jānis",
        "janis": "Jānis",
        "jāni": "Jānis",
        "jani": "Jānis",
        "jānim": "Jānis",
        "janim": "Jānis",
        "anna": "Anna",
        "annu": "Anna",
        "annai": "Anna",
    }
    return known.get(raw.lower(), raw[:1].upper() + raw[1:])


def _client_accusative(name):
    client = _normalize_client(name)
    mapping = {"Andris": "Andri", "Jānis": "Jāni", "Anna": "Annu"}
    if client in mapping:
        return mapping[client]
    if client.endswith("s"):
        return client[:-1] + "u"
    return client


def _client_dative(name):
    client = _normalize_client(name)
    mapping = {"Andris": "Andrim", "Jānis": "Jānim", "Anna": "Annai"}
    if client in mapping:
        return mapping[client]
    if client.endswith("s"):
        return client[:-1] + "am"
    return client


def _client_vocative(name):
    # Telegram darba tekstiem drošāk izmantojam akuzatīvu/vārdu bez agresīva locījuma.
    client = _normalize_client(name)
    mapping = {"Andris": "Andri", "Jānis": "Jāni", "Anna": "Anna"}
    return mapping.get(client, client)


def extract_client(text, tasks=None, memory_snapshot=None):
    raw = _clean(text)
    lower = raw.lower()

    for token in ["andrim", "andri", "andris", "andriu", "jānim", "janim", "jāni", "jani", "jānis", "janis", "annai", "annu", "anna"]:
        if re.search(rf"\b{re.escape(token)}\b", lower):
            return _normalize_client(token)

    m = re.search(r"\b([A-ZĀČĒĢĪĶĻŅŠŪŽ][a-zāčēģīķļņšūž]+)\b", raw)
    if m:
        candidate = _normalize_client(m.group(1))
        if candidate.lower() not in {"nina", "telegram", "core", "work", "layer"}:
            return candidate

    snap = memory_snapshot or {}
    for key in ["client", "last_client", "active_client"]:
        if snap.get(key):
            return _normalize_client(snap.get(key))

    for task in tasks or []:
        client = _task_client(task)
        if client:
            return client
        blob = _task_text(task).lower()
        if any(x in blob for x in ["andris", "andri", "andrim"]):
            return "Andris"

    return ""


def _client_tasks(client, tasks=None):
    client = _normalize_client(client)
    if not client:
        return []

    variants = {
        "Andris": ["andris", "andri", "andrim"],
        "Jānis": ["jānis", "janis", "jāni", "jani", "jānim", "janim"],
        "Anna": ["anna", "annu", "annai"],
    }.get(client, [client.lower()])

    result = []
    seen = set()
    for task in tasks or []:
        text = _task_text(task)
        if not text:
            continue
        task_client = _task_client(task)
        blob = text.lower()
        if task_client == client or any(v in blob for v in variants):
            key = text.lower()
            if key not in seen:
                seen.add(key)
                result.append(task)
    return result


def _find_offer_task(client, tasks=None, memory_snapshot=None):
    snap = memory_snapshot or {}
    for key in ["offer", "last_offer", "proposal", "piedāvājums"]:
        if snap.get(key):
            return _clean(snap.get(key))

    for task in _client_tasks(client, tasks):
        text = _task_text(task)
        if any(x in text.lower() for x in ["piedāvāj", "piedavaj", "tāme", "tame", "jānosūta", "janosuta"]):
            return text
    return ""


def _find_followup_task(client, tasks=None, memory_snapshot=None):
    snap = memory_snapshot or {}
    for key in ["followup", "follow_up", "last_followup"]:
        if snap.get(key):
            return _clean(snap.get(key))

    for task in _client_tasks(client, tasks):
        text = _task_text(task)
        if any(x in text.lower() for x in ["jāpajautā", "japajauta", "follow", "par atbildi", "atgādin", "atgadin"]):
            return text
    return ""


def _find_call_task(client, tasks=None, memory_snapshot=None):
    snap = memory_snapshot or {}
    for key in ["call", "zvans", "last_call"]:
        if snap.get(key):
            return _clean(snap.get(key))

    for task in _client_tasks(client, tasks):
        text = _task_text(task)
        if any(x in text.lower() for x in ["jāzvana", "jazvana", "jāpiezvana", "japiezvana", "zvans"]):
            return text
    return ""


def _detect_intent(text):
    lower = _lower(text)
    if lower in ["work layer", "work layer status", "nina work layer", "work skills", "darba prasmes"]:
        return "status"
    if any(x in lower for x in ["zvana plānu", "zvana planu", "sarunas plānu", "sarunas planu", "sagatavo zvanu", "pirms zvana"]):
        return "call_prep"
    if any(x in lower for x in ["follow-up", "followup", "follow up", "pajautāt", "pajautat", "par atbildi"]):
        if any(x in lower for x in ["uzraksti", "sagatavo", "ko rakstīt", "ko rakstit", "ziņu", "zinu"]):
            return "followup_message"
    if any(x in lower for x in [
        "ko rakstīt", "ko rakstit", "uzraksti", "sagatavo ziņu", "sagatavo zinu",
        "ko sūtīt", "ko sutit", "ko nosūtīt", "ko nosutit", "ziņu klientam", "zinu klientam"
    ]):
        return "client_message"
    if any(x in lower for x in ["uztaisi piedāvājumu", "uztaisi piedavajumu", "sagatavo piedāvājumu", "sagatavo piedavajumu", "sagatavo tāmi", "sagatavo tami", "piedāvājuma tekstu", "piedavajuma tekstu"]):
        return "offer_message"
    return ""


def is_work_layer_command(text):
    return bool(_detect_intent(text))


def work_layer_status_answer():
    return (
        "🧰 Nina Work Layer V1.1 — Smart Message Mode ir aktīvs. ✅\n\n"
        "Ko tas dara:\n"
        "• sagatavo piedāvājuma tekstu klientam;\n"
        "• sagatavo follow-up ziņu;\n"
        "• sagatavo zvana plānu;\n"
        "• Smart Message Mode pats izvēlas pareizo ziņas tipu pēc klienta darba snapshota;\n"
        "• neko nesaglabā datubāzē — tikai sagatavo tekstu darbam.\n\n"
        "Smart komandas:\n"
        "• ko rakstīt Andrim\n"
        "• uzraksti Andrim\n"
        "• sagatavo ziņu Andrim\n"
        "• ko sūtīt Andrim\n\n"
        "Tiešās komandas:\n"
        "• uztaisi piedāvājumu Andrim\n"
        "• uzraksti follow-up Andrim\n"
        "• sagatavo zvana plānu Andrim\n\n"
        f"Versija: {WORK_LAYER_VERSION}"
    )


def build_offer_message(client, tasks=None, memory_snapshot=None):
    client = _normalize_client(client)
    voc = _client_vocative(client)
    dat = _client_dative(client)
    offer_task = _find_offer_task(client, tasks, memory_snapshot)
    followup_task = _find_followup_task(client, tasks, memory_snapshot)

    lines = [
        f"📨 Piedāvājuma sagatave — {client}",
        "",
        "Gatavs teksts klientam:",
        "",
        f"Sveiks, {voc}!",
        "",
        "Nosūtu piedāvājumu par pārrunāto darbu.",
        "Ja viss izskatās kārtībā, dod ziņu, un varam vienoties par nākamo soli / darbu sākšanu.",
        "",
        "Ja vajag kaut ko precizēt, droši uzraksti — pielabošu.",
        "",
        "Ar cieņu,",
        "",
        "Ninas darba piezīmes:",
        f"• klients: {client}",
        f"• saistītais darbs: {offer_task or f'piedāvājums {dat}'}",
    ]
    if followup_task:
        lines.append(f"• pēc tam jāseko līdzi: {followup_task}")
    lines.extend([
        "",
        "Nākamais solis: pārbaudi summas / termiņus un nosūti klientam.",
        "",
        f"Versija: {WORK_LAYER_VERSION}",
    ])
    return "\n".join(lines)


def build_followup_message(client, tasks=None, memory_snapshot=None):
    client = _normalize_client(client)
    voc = _client_vocative(client)
    offer_task = _find_offer_task(client, tasks, memory_snapshot)
    followup_task = _find_followup_task(client, tasks, memory_snapshot)

    lines = [
        f"🔁 Follow-up ziņas sagatave — {client}",
        "",
        "Gatavs teksts klientam:",
        "",
        f"Sveiks, {voc}!",
        "",
        "Gribēju pieklājīgi pajautāt, vai sanāca apskatīt piedāvājumu.",
        "Ja ir kādi jautājumi vai vajag ko precizēt, droši dod ziņu — varu pielabot vai paskaidrot.",
        "",
        "Paldies!",
        "",
        "Ninas darba piezīmes:",
        f"• klients: {client}",
        f"• follow-up darbs: {followup_task or 'jāpajautā par atbildi'}",
    ]
    if offer_task:
        lines.append(f"• piedāvājuma konteksts: {offer_task}")
    lines.extend([
        "",
        "Nākamais solis: nosūti šo ziņu un pēc tam atzīmē, kad klients atbild.",
        "",
        f"Versija: {WORK_LAYER_VERSION}",
    ])
    return "\n".join(lines)


def build_call_plan(client, tasks=None, memory_snapshot=None):
    client = _normalize_client(client)
    offer_task = _find_offer_task(client, tasks, memory_snapshot)
    followup_task = _find_followup_task(client, tasks, memory_snapshot)
    call_task = _find_call_task(client, tasks, memory_snapshot)

    lines = [
        f"☎️ Zvana plāns — {client}",
        "",
        "Mērķis:",
        "• saprast, vai klients virzās uz lēmumu;",
        "• noskaidrot, kas traucē pieņemt piedāvājumu;",
        "• vienoties par nākamo konkrēto soli.",
        "",
        "Sarunas punkti:",
        "1. Vai sanāca apskatīt piedāvājumu?",
        "2. Vai ir kāds neskaidrs punkts, cena vai termiņš?",
        "3. Kādu nākamo soli varam vienoties tagad?",
        "",
        "Darba konteksts:",
        f"• zvans: {call_task or 'jāzvana klientam'}",
        f"• piedāvājums: {offer_task or 'nav konkrēta piedāvājuma ieraksta'}",
        f"• follow-up: {followup_task or 'nav konkrēta follow-up ieraksta'}",
        "",
        "Nākamais solis: piezvani un pēc sarunas ieraksti īsu rezultātu, piemēram: `Andris piekrita, jānosūta precizēta tāme`.",
        "",
        f"Versija: {WORK_LAYER_VERSION}",
    ]
    return "\n".join(lines)


def _task_kind(text):
    lower = _lower(text)
    if any(x in lower for x in ["piedāvāj", "piedavaj", "tāme", "tame", "jānosūta", "janosuta", "offer"]):
        return "offer"
    if any(x in lower for x in ["jāpajautā", "japajauta", "follow", "par atbildi", "atgādin", "atgadin"]):
        return "followup"
    if any(x in lower for x in ["jāzvana", "jazvana", "jāpiezvana", "japiezvana", "zvans", "zvanīt", "zvanit"]):
        return "call"
    return "general"


def _snapshot_top_text(memory_snapshot=None):
    snap = memory_snapshot or {}
    for key in ["top_task", "top_work", "priority", "last_task", "task"]:
        if snap.get(key):
            return _clean(snap.get(key))
    return ""


def _choose_smart_message_type(client, tasks=None, memory_snapshot=None):
    top_text = _snapshot_top_text(memory_snapshot)
    top_kind = _task_kind(top_text)
    if top_kind in ["offer", "followup", "call"]:
        return top_kind, top_text

    client_items = _client_tasks(client, tasks)
    if client_items:
        ranked = []
        for task in client_items:
            text = _task_text(task)
            kind = _task_kind(text)
            score = 0
            if kind == "offer":
                score = 90
            elif kind == "followup":
                score = 70
            elif kind == "call":
                score = 60
            else:
                score = 10
            lower = _lower(text)
            if "rīt" in lower or "rit" in lower:
                score += 15
            if "šodien" in lower or "sodien" in lower:
                score += 20
            ranked.append((score, kind, text))
        ranked.sort(reverse=True, key=lambda x: x[0])
        if ranked and ranked[0][1] in ["offer", "followup", "call"]:
            return ranked[0][1], ranked[0][2]

    if _find_offer_task(client, tasks, memory_snapshot):
        return "offer", _find_offer_task(client, tasks, memory_snapshot)
    if _find_followup_task(client, tasks, memory_snapshot):
        return "followup", _find_followup_task(client, tasks, memory_snapshot)
    if _find_call_task(client, tasks, memory_snapshot):
        return "call", _find_call_task(client, tasks, memory_snapshot)
    return "followup", ""


def build_client_message(client, tasks=None, memory_snapshot=None):
    client = _normalize_client(client)
    selected, reason_text = _choose_smart_message_type(client, tasks, memory_snapshot)

    if selected == "offer":
        answer = build_offer_message(client, tasks, memory_snapshot)
    elif selected == "call":
        answer = build_call_plan(client, tasks, memory_snapshot)
    else:
        answer = build_followup_message(client, tasks, memory_snapshot)

    note = (
        "\n\nSmart Message izvēle:\n"
        f"• izvēlētais tips: {selected}\n"
        f"• pamats: {reason_text or 'klienta darba snapshot'}"
    )
    if "Versija:" in answer:
        before, version = answer.rsplit("Versija:", 1)
        return before.rstrip() + note + "\n\nVersija:" + version
    return answer.rstrip() + note + f"\n\nVersija: {WORK_LAYER_VERSION}"


def build_work_layer_answer(user_text, tasks=None, memory_snapshot=None):
    intent = _detect_intent(user_text)
    if intent == "status":
        return work_layer_status_answer()

    client = extract_client(user_text, tasks=tasks, memory_snapshot=memory_snapshot)
    if not client:
        return (
            "🧰 Work Layer\n\n"
            "Pasaki klientu, kuram jāsagatavo teksts.\n\n"
            "Piemēri:\n"
            "• uztaisi piedāvājumu Andrim\n"
            "• uzraksti follow-up Andrim\n"
            "• sagatavo zvana plānu Andrim\n\n"
            f"Versija: {WORK_LAYER_VERSION}"
        )

    if intent == "offer_message":
        return build_offer_message(client, tasks, memory_snapshot)
    if intent == "followup_message":
        return build_followup_message(client, tasks, memory_snapshot)
    if intent == "call_prep":
        return build_call_plan(client, tasks, memory_snapshot)
    if intent == "client_message":
        return build_client_message(client, tasks, memory_snapshot)

    return work_layer_status_answer()
