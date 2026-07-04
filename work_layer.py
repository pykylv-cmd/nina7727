"""
work_layer.py
Nina Work Layer V1.3.1 — Offer Context Cleanup

Mērķis:
- pārvērst klienta darba snapshotu praktiskās darba sagatavēs;
- dot 3 klienta ziņu variantus katram darba tipam;
- saglabāt Smart Message Mode un Smart Priority izvēli;
- ielikt ziņās darba tēmu, summu/cenu, termiņu un nākamo soli, ja tie ir atrodami tekstā;
- nemainīt datubāzi un neizdomāt klientus, ja tie nav tekstā vai darba atmiņā.
"""

import re

WORK_LAYER_VERSION = "Nina Work Layer V1.3.1 — Offer Context Cleanup"


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
        "andris": "Andris", "andri": "Andris", "andrim": "Andris", "andriu": "Andris",
        "jānis": "Jānis", "janis": "Jānis", "jāni": "Jānis", "jani": "Jānis", "jānim": "Jānis", "janim": "Jānis",
        "anna": "Anna", "annu": "Anna", "annai": "Anna",
    }
    return known.get(raw.lower(), raw[:1].upper() + raw[1:])


def _client_vocative(name):
    client = _normalize_client(name)
    return {"Andris": "Andri", "Jānis": "Jāni", "Anna": "Anna"}.get(client, client)


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
    result, seen = [], set()
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
    if any(x in lower for x in ["follow-up", "followup", "follow up", "pajautāt", "pajautat", "par atbildi", "atgādinājums", "atgadinajums"]):
        if any(x in lower for x in ["uzraksti", "sagatavo", "ko rakstīt", "ko rakstit", "ziņu", "zinu"]):
            return "followup_message"
    if any(x in lower for x in ["ko rakstīt", "ko rakstit", "uzraksti", "sagatavo ziņu", "sagatavo zinu", "ko sūtīt", "ko sutit", "ko nosūtīt", "ko nosutit", "ziņu klientam", "zinu klientam"]):
        return "client_message"
    if any(x in lower for x in ["uztaisi piedāvājumu", "uztaisi piedavajumu", "sagatavo piedāvājumu", "sagatavo piedavajumu", "sagatavo tāmi", "sagatavo tami", "piedāvājuma tekstu", "piedavajuma tekstu"]):
        return "offer_message"
    return ""


def is_work_layer_command(text):
    return bool(_detect_intent(text))


def work_layer_status_answer():
    return (
        "🧰 Nina Work Layer V1.3.1 — Offer Context Cleanup ir aktīvs. ✅\n\n"
        "Ko tas dara:\n"
        "• sagatavo piedāvājuma tekstu klientam;\n"
        "• sagatavo follow-up ziņu;\n"
        "• sagatavo zvana plānu;\n"
        "• Smart Message Mode pats izvēlas pareizo ziņas tipu pēc klienta darba snapshota;\n"
        "• katram ziņas tipam dod 3 variantus;\n"
        "• offer ziņās termiņu lieto tikai kā piedāvājuma nosūtīšanas kontekstu, nevis kā darbu sākšanas frāzi;\n"
        "• follow-up ziņās nevajadzīgi neievelk offer termiņu;\n"
        "• ziņās ieliek darba tēmu, summu/cenu un tikai atbilstošo kontekstu no taska;\n"
        "• neko nesaglabā datubāzē — tikai sagatavo tekstu darbam.\n\n"
        "Testi:\n"
        "• ko rakstīt Andrim\n"
        "• uztaisi piedāvājumu Andrim\n"
        "• uzraksti atgādinājums Andrim\n"
        "• sagatavo zvana plānu Andrim\n\n"
        f"Versija: {WORK_LAYER_VERSION}"
    )


def _extract_price(text):
    raw = _clean(text)
    patterns = [
        r"(?i)(?:summa|cena|budžets|budzets)\s*(?:ir|:)?\s*([0-9][0-9\s.,]*\s*(?:€|eur|eiro))",
        r"([0-9][0-9\s.,]*\s*(?:€|eur|eiro))",
    ]
    for pattern in patterns:
        m = re.search(pattern, raw)
        if m:
            return _clean(m.group(1)).replace("  ", " ")
    return ""


def _extract_start_or_deadline(text):
    lower = _lower(text)
    # order matters: specific phrases before generic day words
    phrase_map = [
        ("nākamnedēļ", "nākamnedēļ"), ("nakamnedel", "nākamnedēļ"),
        ("šonedēļ", "šonedēļ"), ("sonedel", "šonedēļ"),
        ("rīt", "rīt"), ("rit", "rīt"), ("parīt", "parīt"), ("parit", "parīt"),
        ("šodien", "šodien"), ("sodien", "šodien"),
        ("pirmdien", "pirmdien"), ("otrdien", "otrdien"), ("trešdien", "trešdien"), ("tresdien", "trešdien"),
        ("ceturtdien", "ceturtdien"), ("piektdien", "piektdien"), ("sestdien", "sestdien"),
        ("svētdien", "svētdien"), ("svetdien", "svētdien"),
    ]
    for needle, label in phrase_map:
        if re.search(rf"\b{re.escape(needle)}\b", lower):
            return label
    return ""


def _extract_subject(text, client=""):
    raw = _clean(text)
    lower = raw.lower()
    if not raw:
        return "pārrunāto darbu"

    # explicit topic markers
    explicit_patterns = [
        r"(?i)(?:par|darbs|darbi|tēma|tema)\s*[:\-]?\s*([A-Za-zĀČĒĢĪĶĻŅŠŪŽāčēģīķļņšūž0-9\s\-]+?)(?:\s+(?:summa|cena|budžets|budzets|rīt|rit|šodien|sodien|nākamnedēļ|nakamnedel|piektdien|pirmdien|otrdien|trešdien|tresdien|ceturtdien|sestdien|svētdien|svetdien)|[.,;]|$)",
    ]
    for pattern in explicit_patterns:
        m = re.search(pattern, raw)
        if m:
            subject = _clean(m.group(1))
            if subject and len(subject) > 2 and subject.lower() not in {"atbildi", "piedāvājumu", "piedavajumu"}:
                return subject[:80]

    # known work topic keywords
    topics = [
        ("fasādes krāso", "fasādes krāsošanas darbiem"),
        ("fasades kraso", "fasādes krāsošanas darbiem"),
        ("fasāde", "fasādes darbiem"),
        ("fasade", "fasādes darbiem"),
        ("jumt", "jumta darbiem"),
        ("remont", "remonta darbiem"),
        ("tāme", "tāmi"),
        ("tame", "tāmi"),
    ]
    for needle, subject in topics:
        if needle in lower:
            return subject

    return "pārrunāto darbu"


def _build_context(client, tasks=None, memory_snapshot=None):
    offer_task = _find_offer_task(client, tasks, memory_snapshot)
    followup_task = _find_followup_task(client, tasks, memory_snapshot)
    call_task = _find_call_task(client, tasks, memory_snapshot)
    combined = " | ".join([offer_task, followup_task, call_task])
    primary = offer_task or followup_task or call_task or combined
    return {
        "client": _normalize_client(client),
        "offer_task": offer_task,
        "followup_task": followup_task,
        "call_task": call_task,
        "subject": _extract_subject(primary, client),
        "price": _extract_price(combined),
        "offer_send_when": _extract_start_or_deadline(offer_task),
        "followup_when": _extract_start_or_deadline(followup_task),
        "call_when": _extract_start_or_deadline(call_task),
    }


def _context_sentence(ctx, mode="generic"):
    parts = []
    if ctx.get("subject") and ctx.get("subject") != "pārrunāto darbu":
        parts.append(f"darba tēma: {ctx['subject']}")
    if ctx.get("price"):
        parts.append(f"summa/cena: {ctx['price']}")
    when = ""
    if mode == "offer":
        when = ctx.get("offer_send_when", "")
        if when:
            parts.append(f"piedāvājums jānosūta: {when}")
    elif mode == "followup":
        when = ctx.get("followup_when", "")
        if when:
            parts.append(f"follow-up termiņš: {when}")
    elif mode == "call":
        when = ctx.get("call_when", "")
        if when:
            parts.append(f"zvana termiņš: {when}")
    return "; ".join(parts)


def _offer_body(ctx, style="normal"):
    voc = _client_vocative(ctx["client"])
    subject = ctx.get("subject") or "pārrunāto darbu"
    price = ctx.get("price")
    send_when = ctx.get("offer_send_when")
    price_line = f" Kopējā summa/cena: {price}." if price else ""
    when_line = f" Nosūtu to {send_when}, kā runājām." if send_when else ""

    if style == "short":
        return f"Sveiks, {voc}! Nosūtu piedāvājumu par {subject}.{price_line}{when_line} Apskati, lūdzu, un dod ziņu, ja viss der vai vajag ko precizēt."
    if style == "formal":
        return f"Labdien, {ctx['client']}!\n\nNosūtu Jums piedāvājumu par {subject}.{price_line}{when_line} Lūdzu apskatiet, un, ja viss ir pieņemami, vienosimies par nākamo soli un izpildes laiku. Ja nepieciešami precizējumi, sagatavošu labotu variantu."
    return f"Sveiks, {voc}!\n\nNosūtu piedāvājumu par {subject}.{price_line}{when_line}\n\nJa viss izskatās kārtībā, dod ziņu, un varam vienoties par nākamo soli vai darbu sākšanu.\n\nJa vajag ko precizēt, droši uzraksti — pielabošu."


def _followup_body(ctx, style="soft"):
    voc = _client_vocative(ctx["client"])
    subject = ctx.get("subject") or "piedāvājumu"
    price = ctx.get("price")
    context = f" par {subject}" if subject and subject != "pārrunāto darbu" else ""
    price_line = f" Summa/cena bija {price}." if price else ""
    if style == "direct":
        return f"Sveiks, {voc}! Vai sanāca apskatīt manu piedāvājumu{context}?{price_line} Ja vajag ko precizēt vai pielabot, varu to izdarīt šodien."
    if style == "received":
        return f"Sveiks, {voc}! Gribu pārliecināties, ka piedāvājums{context} ir saņemts un nonācis līdz Tev.{price_line} Vai sanāca to apskatīt, un vai ir kādi jautājumi pirms ejam tālāk?"
    return f"Sveiks, {voc}! Gribēju tikai pieklājīgi pajautāt, vai sanāca apskatīt piedāvājumu{context}.{price_line} Ja ir kādi jautājumi, droši dod ziņu."


def _render_variants(title, variants, notes, next_step, ctx=None, mode="generic"):
    lines = [title, "", "Gatavi varianti klientam:", ""]
    for idx, (label, text) in enumerate(variants, 1):
        lines.append(f"{idx}. {label}")
        lines.append(text)
        lines.append("")
    context_note = _context_sentence(ctx or {}, mode=mode)
    if context_note:
        notes = list(notes or []) + [f"konteksts ziņā: {context_note}"]
    lines.append("Ninas darba piezīmes:")
    for note in notes:
        if note:
            lines.append(f"• {note}")
    lines.extend(["", f"Nākamais solis: {next_step}", "", f"Versija: {WORK_LAYER_VERSION}"])
    return "\n".join(lines)


def build_offer_message(client, tasks=None, memory_snapshot=None):
    client = _normalize_client(client)
    ctx = _build_context(client, tasks, memory_snapshot)
    variants = [
        ("Īsais Telegram variants", _offer_body(ctx, "short")),
        ("Normālais klienta variants", _offer_body(ctx, "normal")),
        ("Formālākais variants", _offer_body(ctx, "formal")),
    ]
    notes = [f"klients: {client}", f"saistītais darbs: {ctx.get('offer_task') or 'jānosūta piedāvājums'}"]
    if ctx.get("followup_task"):
        notes.append(f"pēc tam jāseko līdzi: {ctx['followup_task']}")
    return _render_variants(f"📨 Piedāvājuma varianti — {client}", variants, notes, "izvēlies vienu variantu, pieliec summas / termiņus un nosūti klientam.", ctx, mode="offer")


def build_followup_message(client, tasks=None, memory_snapshot=None):
    client = _normalize_client(client)
    ctx = _build_context(client, tasks, memory_snapshot)
    variants = [
        ("Maigais follow-up", _followup_body(ctx, "soft")),
        ("Tiešāks follow-up", _followup_body(ctx, "direct")),
        ("Saņēmāt / apskatījāt variants", _followup_body(ctx, "received")),
    ]
    notes = [f"klients: {client}", f"follow-up darbs: {ctx.get('followup_task') or 'jāpajautā par atbildi'}"]
    if ctx.get("offer_task"):
        notes.append(f"piedāvājuma konteksts: {ctx['offer_task']}")
    return _render_variants(f"🔁 Follow-up varianti — {client}", variants, notes, "izvēlies vienu follow-up variantu, nosūti un pēc tam atzīmē klienta atbildi.", ctx, mode="followup")


def build_call_plan(client, tasks=None, memory_snapshot=None):
    client = _normalize_client(client)
    ctx = _build_context(client, tasks, memory_snapshot)
    subject = ctx.get("subject") or "piedāvājumu"
    price = f" Summa/cena: {ctx['price']}." if ctx.get("price") else ""
    when = f" Zvana termiņš: {ctx['call_when']}." if ctx.get("call_when") else ""
    variants = [
        ("Īsais zvana plāns", f"1. Pajautā, vai piedāvājums par {subject} ir apskatīts.\n2. Noskaidro, vai ir jautājumi par cenu, termiņu vai darba apjomu.{price}{when}\n3. Vienojies par nākamo soli."),
        ("Sarunas skripts", f"Sveiks, {_client_vocative(client)}! Zvanu, lai saprastu, vai sanāca apskatīt piedāvājumu par {subject} un vai ir kādi jautājumi.{price}{when} Ja kaut kas jāprecizē, varu to uzreiz piefiksēt un sagatavot nākamo versiju."),
        ("Iebildumu jautājumi", "• Kas šobrīd traucē pieņemt lēmumu?\n• Vai jautājums ir par cenu, termiņu vai darba apjomu?\n• Ko vajag precizēt, lai varam virzīties tālāk?"),
    ]
    notes = [f"klients: {client}", f"zvans: {ctx.get('call_task') or 'jāzvana klientam'}", f"piedāvājums: {ctx.get('offer_task') or 'nav konkrēta piedāvājuma ieraksta'}", f"follow-up: {ctx.get('followup_task') or 'nav konkrēta follow-up ieraksta'}"]
    return _render_variants(f"☎️ Zvana varianti — {client}", variants, notes, "izvēlies vienu zvana pieeju, piezvani un pēc sarunas ieraksti rezultātu.", ctx, mode="call")


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
    for key in ["top_task", "top_work", "priority", "next_step", "last_task", "task"]:
        if snap.get(key):
            return _clean(snap.get(key))
    return ""


def _deadline_score(text):
    lower = _lower(text)
    if any(x in lower for x in ["šodien", "sodien", "tagad", "today"]):
        return 40
    if any(x in lower for x in ["rīt", "rit", "tomorrow"]):
        return 35
    if any(x in lower for x in ["parīt", "parit"]):
        return 20
    if any(x in lower for x in ["pirmdien", "otrdien", "trešdien", "tresdien", "ceturtdien", "piektdien", "sestdien", "svētdien", "svetdien"]):
        return 15
    return 0


def _candidate_score(kind, text, top_text=""):
    base = {"offer": 130, "followup": 85, "call": 70, "general": 10}.get(kind, 10)
    score = base + _deadline_score(text)
    if top_text and _clean(text).lower() == _clean(top_text).lower():
        score += 25
    return score


def _choose_smart_message_type(client, tasks=None, memory_snapshot=None):
    top_text = _snapshot_top_text(memory_snapshot)
    candidates = []
    offer_task = _find_offer_task(client, tasks, memory_snapshot)
    followup_task = _find_followup_task(client, tasks, memory_snapshot)
    call_task = _find_call_task(client, tasks, memory_snapshot)
    if offer_task:
        candidates.append(("offer", offer_task))
    if followup_task:
        candidates.append(("followup", followup_task))
    if call_task:
        candidates.append(("call", call_task))
    top_kind = _task_kind(top_text)
    if top_text and top_kind in ["offer", "followup", "call"]:
        candidates.append((top_kind, top_text))
    for task in _client_tasks(client, tasks):
        text = _task_text(task)
        kind = _task_kind(text)
        if kind in ["offer", "followup", "call"]:
            candidates.append((kind, text))
    deduped, seen = [], set()
    for kind, text in candidates:
        key = (kind, _clean(text).lower())
        if text and key not in seen:
            seen.add(key)
            deduped.append((kind, text))
    if deduped:
        ranked = sorted([(_candidate_score(kind, text, top_text), kind, text) for kind, text in deduped], reverse=True, key=lambda x: x[0])
        _, best_kind, best_text = ranked[0]
        return best_kind, best_text
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
    note = ("\n\nSmart Message izvēle:\n" f"• izvēlētais tips: {selected}\n" f"• pamats: {reason_text or 'klienta darba snapshot'}")
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
            "• uzraksti atgādinājums Andrim\n"
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
    return ""
