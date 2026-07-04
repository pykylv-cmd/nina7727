"""
work_layer.py
Nina Work Layer V1 — Offer & Follow-up Skills

Mērķis:
- pārvērst klienta darba snapshotu praktiskās darba sagatavēs;
- sagatavot piedāvājuma tekstu, follow-up ziņu un zvana plānu;
- strādāt virs esošajiem Task / Follow-up / Client Work / Initiative slāņiem;
- nemainīt datubāzi un neizdomāt klientus, ja tie nav tekstā vai darba atmiņā.
"""

import re

WORK_LAYER_VERSION = "Nina Work Layer V1 — Offer & Follow-up Skills"


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
    if any(x in lower for x in ["ko rakstīt", "ko rakstit", "uzraksti", "sagatavo ziņu", "sagatavo zinu"]):
        return "client_message"
    if any(x in lower for x in ["uztaisi piedāvājumu", "uztaisi piedavajumu", "sagatavo piedāvājumu", "sagatavo piedavajumu", "sagatavo tāmi", "sagatavo tami", "piedāvājuma tekstu", "piedavajuma tekstu"]):
        return "offer_message"
    return ""


def is_work_layer_command(text):
    return bool(_detect_intent(text))


def work_layer_status_answer():
    return (
        "🧰 Nina Work Layer V1 — Offer & Follow-up Skills ir aktīvs. ✅\n\n"
        "Ko tas dara:\n"
        "• sagatavo piedāvājuma tekstu klientam;\n"
        "• sagatavo follow-up ziņu;\n"
        "• sagatavo zvana plānu;\n"
        "• izmanto klienta darbu snapshotu, bet neko nesaglabā datubāzē.\n\n"
        "Testi:\n"
        "• uztaisi piedāvājumu Andrim\n"
        "• uzraksti follow-up Andrim\n"
        "• ko rakstīt Andrim\n"
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


def build_client_message(client, tasks=None, memory_snapshot=None):
    client = _normalize_client(client)
    offer_task = _find_offer_task(client, tasks, memory_snapshot)
    followup_task = _find_followup_task(client, tasks, memory_snapshot)

    # Ja redzam follow-up, drošāk piedāvāt follow-up. Ja piedāvājums ir top darbs, piedāvāt piedāvājumu.
    if followup_task and "piedāv" not in _lower(offer_task):
        return build_followup_message(client, tasks, memory_snapshot)
    if offer_task:
        return build_offer_message(client, tasks, memory_snapshot)
    return build_followup_message(client, tasks, memory_snapshot)


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
