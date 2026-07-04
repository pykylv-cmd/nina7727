"""
work_layer.py
Nina Work Layer V1.6 — Call Intelligence

Mērķis:
- pārvērst klienta darba snapshotu praktiskās darba sagatavēs;
- dot 3 klienta ziņu variantus katram darba tipam;
- saglabāt Smart Message Mode un Smart Priority izvēli;
- ielikt ziņās darba tēmu, summu/cenu, termiņu un nākamo soli, ja tie ir atrodami tekstā;
- nemainīt datubāzi un neizdomāt klientus, ja tie nav tekstā vai darba atmiņā.
"""

import re

WORK_LAYER_VERSION = "Nina Work Layer V1.6 — Call Intelligence"


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
        "🧰 Nina Work Layer V1.6 — Call Intelligence ir aktīvs. ✅\n\n"
        "Ko tas dara:\n"
        "• sagatavo piedāvājuma tekstu klientam;\n"
        "• sagatavo follow-up ziņu;\n"
        "• sagatavo zvana plānu;\n"
        "• Smart Message Mode pats izvēlas pareizo ziņas tipu pēc klienta darba snapshota;\n"
        "• katram ziņas tipam dod 3 variantus;\n"
        "• offer ziņās termiņu lieto tikai kā piedāvājuma nosūtīšanas kontekstu, nevis kā darbu sākšanas frāzi;\n"
        "• follow-up ziņās nevajadzīgi neievelk offer termiņu;\n"
        "• ziņās ieliek darba tēmu, summu/cenu un tikai atbilstošo kontekstu no taska;\n"
        "• offer_send_when tagad ņem rīt no rīt jānosūta piedāvājums, nevis nākamnedēļ no darbu sākšanas;\n"
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


def _deadline_words_pattern():
    return r"(šodien|sodien|rīt|rit|parīt|parit|nākamnedēļ|nakamnedel|šonedēļ|sonedel|pirmdien|otrdien|trešdien|tresdien|ceturtdien|piektdien|sestdien|svētdien|svetdien)"


def _normalize_deadline_word(word):
    return _extract_start_or_deadline(word or "")


def _extract_offer_send_deadline(text):
    """Atrod tieši piedāvājuma nosūtīšanas termiņu, nevis darbu sākšanas laiku."""
    raw = _clean(text)
    lower = raw.lower()
    if not lower:
        return ""

    word = _deadline_words_pattern()

    # Termiņš pirms darbības: "rīt jānosūta piedāvājums"
    m = re.search(rf"\b{word}\b[^.,;|]{{0,90}}(?:jānosūta|janosuta|nosūtīt|nosutit|nosūtu|nosutu|sagatavot|uztaisi|sagatavo)\s+(?:piedāvājumu|piedavajumu|piedāvājums|piedavajums|tāmi|tami)", lower)
    if m:
        return _normalize_deadline_word(m.group(1))

    # Darbība pirms termiņa: "piedāvājums jānosūta rīt"
    m = re.search(rf"(?:piedāvājums|piedavajums|piedāvājumu|piedavajumu|tāme|tame|tāmi|tami)[^.,;|]{{0,90}}(?:jānosūta|janosuta|nosūtīt|nosutit|nosūtu|nosutu|sagatavot|sagatavo)[^.,;|]{{0,60}}\b{word}\b", lower)
    if m:
        return _normalize_deadline_word(m.group(1))

    # Īss offer uzdevums bez darba sākšanas frāzes: drīkst paņemt pirmo termiņu.
    has_offer = any(x in lower for x in ["piedāvāj", "piedavaj", "tāme", "tame", "jānosūta", "janosuta", "nosūtīt", "nosutit"])
    has_job_start = re.search(r"(?:darbus|darbu|sākt|sakt|uzsākt|uzsakt)", lower)
    if has_offer and not has_job_start:
        return _extract_start_or_deadline(lower)

    return ""


def _extract_job_start_time(text):
    lower = _lower(text)
    for pattern,label in [
        (r"(?:darbus|darbu|sākt|sakt|uzsākt|uzsakt).*?(nākamnedēļ|nakamnedel|šonedēļ|sonedel|rīt|rit|parīt|parit|pirmdien|otrdien|trešdien|tresdien|ceturtdien|piektdien|sestdien|svētdien|svetdien)", None),
        (r"(nākamnedēļ|nakamnedel|šonedēļ|sonedel)\s+(?:varam\s+)?(?:sākt|sakt|uzsākt|uzsakt|darbus)", None),
    ]:
        m=re.search(pattern, lower)
        if m:
            return _extract_start_or_deadline(m.group(1))
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
        "offer_send_when": _extract_offer_send_deadline(offer_task),
        "job_start_when": _extract_job_start_time(combined),
        "followup_when": _extract_start_or_deadline(followup_task),
        "call_when": _extract_start_or_deadline(call_task),
    }


def _context_sentence(ctx, mode="generic"):
    """Build a clean one-line context note without repeating subject/price twice."""
    parts = []

    def add_subject():
        if ctx.get("subject") and ctx.get("subject") != "pārrunāto darbu":
            parts.append(f"darba tēma: {ctx['subject']}")

    def add_price():
        if ctx.get("price"):
            parts.append(f"summa/cena: {ctx['price']}")

    if mode == "offer":
        add_subject()
        add_price()
        when = ctx.get("offer_send_when", "")
        if when:
            parts.append(f"piedāvājums jānosūta: {when}")
        if ctx.get("job_start_when"):
            parts.append(f"darbu sākšana: {ctx['job_start_when']}")
    elif mode == "followup":
        # V1.5.1: follow-up piezīmēs tēma un summa parādās tikai vienreiz.
        when = ctx.get("followup_when", "")
        if when:
            parts.append(f"follow-up termiņš: {when}")
        add_subject()
        add_price()
        if ctx.get("job_start_when"):
            parts.append(f"darbu sākšana: {ctx['job_start_when']}")
    elif mode == "call":
        add_subject()
        add_price()
        when = ctx.get("call_when", "")
        if when:
            parts.append(f"zvana termiņš: {when}")
        if ctx.get("job_start_when"):
            parts.append(f"darbu sākšana: {ctx['job_start_when']}")
    else:
        add_subject()
        add_price()

    return "; ".join(parts)


def _offer_body(ctx, style="normal"):
    voc = _client_vocative(ctx["client"])
    subject = ctx.get("subject") or "pārrunāto darbu"
    price = ctx.get("price")
    send_when = ctx.get("offer_send_when")
    price_line = f" Kopējā summa ir {price}." if price else ""
    when_line = f" Nosūtu to {send_when}, kā runājām." if send_when else ""
    start_when = ctx.get("job_start_when")
    start_line = f" Darbus varam sākt {start_when}." if start_when else ""

    if style == "short":
        return f"Sveiks, {voc}! Nosūtu piedāvājumu par {subject}.{price_line}{start_line}{when_line} Apskati, lūdzu, un dod ziņu, ja viss der vai vajag ko precizēt."
    if style == "formal":
        return f"Labdien, {ctx['client']}!\n\nNosūtu Jums piedāvājumu par {subject}.{price_line}{start_line}{when_line} Lūdzu apskatiet, un, ja viss ir pieņemami, vienosimies par nākamo soli un izpildes laiku. Ja nepieciešami precizējumi, sagatavošu labotu variantu."
    return f"Sveiks, {voc}!\n\nNosūtu piedāvājumu par {subject}.{price_line}{start_line}{when_line}\n\nJa viss izskatās kārtībā, dod ziņu, un varam vienoties par nākamo soli vai darbu sākšanu.\n\nJa vajag ko precizēt, droši uzraksti — pielabošu."


def _followup_context_parts(ctx):
    """Follow-up izmanto piedāvājuma darba detaļas, bet nevelk iekšā offer send deadline."""
    subject = ctx.get("subject") or ""
    price = ctx.get("price") or ""
    job_start = ctx.get("job_start_when") or ""

    context = f" par {subject}" if subject and subject != "pārrunāto darbu" else ""
    price_line = f" Piedāvājuma summa ir {price}." if price else ""
    start_line = f" Ja viss der, darbus varam sākt {job_start}." if job_start else ""
    return context, price_line, start_line


def _followup_body(ctx, style="soft"):
    voc = _client_vocative(ctx["client"])
    context, price_line, start_line = _followup_context_parts(ctx)

    if style == "direct":
        return f"Sveiks, {voc}! Vai sanāca apskatīt manu piedāvājumu{context}?{price_line}{start_line} Ja vajag ko precizēt vai pielabot, varu to izdarīt šodien."
    if style == "received":
        return f"Sveiks, {voc}! Gribu pārliecināties, ka piedāvājums{context} ir saņemts un nonācis līdz Tev.{price_line}{start_line} Vai sanāca to apskatīt, un vai ir kādi jautājumi pirms ejam tālāk?"
    return f"Sveiks, {voc}! Gribēju pieklājīgi pajautāt, vai sanāca apskatīt piedāvājumu{context}.{price_line}{start_line} Ja ir kādi jautājumi, droši dod ziņu."


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


def _call_context_intro(ctx):
    subject = ctx.get("subject") or "pārrunāto darbu"
    price = ctx.get("price") or ""
    job_start = ctx.get("job_start_when") or ""

    parts = [f"piedāvājums par {subject}"]
    if price:
        parts.append(f"summa {price}")
    if job_start:
        parts.append(f"darbus var sākt {job_start}")
    return "; ".join(parts)


def _call_goal(ctx):
    subject = ctx.get("subject") or "pārrunāto darbu"
    price = ctx.get("price") or ""
    job_start = ctx.get("job_start_when") or ""

    lines = [
        f"Zvana mērķis: saprast, vai Andris ir gatavs virzīties tālāk ar piedāvājumu par {subject}.",
    ]
    if price:
        lines.append(f"Sarunā noteikti pieskaries summai: {price}.")
    if job_start:
        lines.append(f"Ja viss der, mērķis ir rezervēt darbu sākšanu {job_start}.")
    return "\n".join(lines)


def build_call_plan(client, tasks=None, memory_snapshot=None):
    client = _normalize_client(client)
    ctx = _build_context(client, tasks, memory_snapshot)
    voc = _client_vocative(client)
    subject = ctx.get("subject") or "pārrunāto darbu"
    price = ctx.get("price") or ""
    job_start = ctx.get("job_start_when") or ""
    call_when = ctx.get("call_when") or ""
    intro = _call_context_intro(ctx)

    price_question = "Vai par cenu ir kāds jautājums vai iebildums?" if price else "Vai ir kāds jautājums par cenu vai darba apjomu?"
    start_question = f"Ja viss der, vai varam rezervēt darbu sākšanu {job_start}?" if job_start else "Ja viss der, kad varam vienoties par nākamo soli?"
    price_line = f"Summa: {price}." if price else "Summa: vēl nav piefiksēta."
    start_line = f"Darbu sākšana: {job_start}." if job_start else "Darbu sākšana: jāprecizē sarunā."
    call_line = f"Zvana termiņš: {call_when}." if call_when else "Zvana termiņš: nav atsevišķi piefiksēts."

    variants = [
        (
            "Īsais zvana plāns",
            "\n".join([
                _call_goal(ctx),
                "",
                "1. Pajautā, vai piedāvājums ir apskatīts.",
                f"2. Pārbaudi kontekstu: {intro}.",
                f"3. {price_question}",
                f"4. {start_question}",
                "5. Noslēdz ar konkrētu nākamo soli: piekrītam / precizējam / pārzvanām.",
            ]),
        ),
        (
            "Sarunas skripts",
            "\n".join([
                f"Sveiks, {voc}! Zvanu par piedāvājumu par {subject}.",
                f"{price_line} {start_line}",
                "Gribēju saprast, vai sanāca to apskatīt un vai ir kāds punkts, ko vajag precizēt.",
                f"{start_question}",
                "Ja vajag, es varu pēc zvana uzreiz sagatavot precizētu variantu.",
            ]),
        ),
        (
            "Iebildumu un closing jautājumi",
            "\n".join([
                "Iebildumu jautājumi:",
                "• Kas šobrīd traucē pieņemt lēmumu?",
                "• Vai jautājums ir par cenu, termiņu vai darba apjomu?",
                "• Ko tieši vajag precizēt, lai varam virzīties tālāk?",
                "",
                "Closing frāzes:",
                f"• Ja viss der, varam rezervēt darbu sākšanu {job_start}." if job_start else "• Ja viss der, vienojamies par nākamo konkrēto soli.",
                "• Es piefiksēju precizējumus un atsūtu labotu piedāvājumu.",
                "• Kad tev būtu ērti apstiprināt gala lēmumu?",
            ]),
        ),
    ]

    notes = [
        f"klients: {client}",
        f"zvans: {ctx.get('call_task') or 'jāzvana klientam'}",
        f"piedāvājums: {ctx.get('offer_task') or 'nav konkrēta piedāvājuma ieraksta'}",
        f"follow-up: {ctx.get('followup_task') or 'nav konkrēta follow-up ieraksta'}",
        call_line,
    ]
    return _render_variants(
        f"☎️ Zvana intelligence — {client}",
        variants,
        notes,
        "piezvani klientam, nofiksē rezultātu un pēc sarunas ieraksti īsu statusu, piemēram: `Andris piekrita, jānosūta precizēta tāme`.",
        ctx,
        mode="call",
    )

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
