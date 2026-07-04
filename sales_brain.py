"""
sales_brain.py
NinaOS Core 3.1.1 — Sales Stage Detection

Mērķis:
- no reāliem taskiem noteikt klienta pārdošanas / darījuma posmu;
- parādīt klienta pipeline skatu;
- palīdzēt saprast, kurš klients ir tuvāk naudai un kurš ir iestrēdzis.

Šis modulis nemaina datubāzi.
Tas tikai analizē jau esošos taskus / memory snapshotu.
"""

import re

SALES_BRAIN_VERSION = "Core 3.1.1 — Sales Stage Detection"


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
        return normalize_client_name(task.get("client", ""))
    return ""


def normalize_client_name(name):
    raw = _clean(name).strip(" .,!?:;\"'")
    if not raw:
        return ""
    known = {
        "andris": "Andris", "andri": "Andris", "andrim": "Andris", "andriu": "Andris",
        "jānis": "Jānis", "janis": "Jānis", "jāni": "Jānis", "jani": "Jānis", "jānim": "Jānis", "janim": "Jānis",
        "anna": "Anna", "annu": "Anna", "annai": "Anna",
    }
    return known.get(raw.lower(), raw[:1].upper() + raw[1:])


def client_accusative(name):
    client = normalize_client_name(name)
    mapping = {"Andris": "Andri", "Jānis": "Jāni", "Anna": "Annu"}
    return mapping.get(client, client)


def client_dative(name):
    client = normalize_client_name(name)
    mapping = {"Andris": "Andrim", "Jānis": "Jānim", "Anna": "Annai"}
    if client in mapping:
        return mapping[client]
    if client.endswith("s"):
        return client[:-1] + "am"
    return client


def extract_client(text, tasks=None, memory_snapshot=None):
    raw = _clean(text)
    lower = raw.lower()
    for token in ["andrim", "andri", "andris", "andriu", "jānim", "janim", "jāni", "jani", "jānis", "janis", "annai", "annu", "anna"]:
        if re.search(rf"\b{re.escape(token)}\b", lower):
            return normalize_client_name(token)

    m = re.search(r"\b([A-ZĀČĒĢĪĶĻŅŠŪŽ][a-zāčēģīķļņšūž]+)\b", raw)
    if m:
        candidate = normalize_client_name(m.group(1))
        if candidate.lower() not in {"nina", "core", "sales", "pipeline", "brain", "telegram"}:
            return candidate

    snap = memory_snapshot or {}
    for key in ["client", "last_client", "active_client"]:
        if snap.get(key):
            return normalize_client_name(snap.get(key))

    for task in tasks or []:
        client = _task_client(task)
        if client:
            return client
    return ""


def _client_variants(client):
    client = normalize_client_name(client)
    variants = {
        "Andris": ["andris", "andri", "andrim"],
        "Jānis": ["jānis", "janis", "jāni", "jani", "jānim", "janim"],
        "Anna": ["anna", "annu", "annai"],
    }
    return variants.get(client, [client.lower()] if client else [])


def client_tasks(client, tasks=None):
    client = normalize_client_name(client)
    variants = _client_variants(client)
    result = []
    seen = set()
    for task in tasks or []:
        text = _task_text(task)
        if not text:
            continue
        task_client = _task_client(task)
        lower = text.lower()
        if task_client == client or any(v in lower for v in variants):
            key = text.lower()
            if key not in seen:
                seen.add(key)
                result.append(task)
    return result


def _contains(text, words):
    lower = _lower(text)
    return any(w in lower for w in words)


def _deadline_label(text):
    lower = _lower(text)
    mapping = [
        (["šodien", "sodien"], "šodien"),
        (["rīt", "rit"], "rīt"),
        (["parīt", "parit"], "parīt"),
        (["pirmdien"], "pirmdien"),
        (["otrdien"], "otrdien"),
        (["trešdien", "tresdien"], "trešdien"),
        (["ceturtdien"], "ceturtdien"),
        (["piektdien"], "piektdien"),
        (["sestdien"], "sestdien"),
        (["svētdien", "svetdien"], "svētdien"),
        (["nākamnedēļ", "nakamnedel"], "nākamnedēļ"),
    ]
    for needles, label in mapping:
        if any(re.search(rf"\b{re.escape(n)}\b", lower) for n in needles):
            return label
    return ""


def _extract_price(text):
    m = re.search(r"([0-9][0-9\s.,]*\s*(?:€|eur|eiro))", _clean(text), flags=re.I)
    return _clean(m.group(1)) if m else ""


def _extract_subject(text):
    raw = _clean(text)
    if not raw:
        return ""
    m = re.search(r"(?i)\bpar\s+([A-Za-zĀČĒĢĪĶĻŅŠŪŽāčēģīķļņšūž0-9\s\-]+?)(?:\s+(?:[0-9]+\s*(?:€|eur|eiro)|darbus|darbu|rīt|rit|šodien|sodien|nākamnedēļ|nakamnedel)|[.,;]|$)", raw)
    if m:
        subject = _clean(m.group(1))
        if subject and subject.lower() not in {"atbildi", "piedāvājumu", "piedavajumu"}:
            return subject[:80]
    lower = raw.lower()
    if "fasādes krāso" in lower or "fasades kraso" in lower:
        return "fasādes krāsošanas darbi"
    if "fasād" in lower or "fasad" in lower:
        return "fasādes darbi"
    if "jumt" in lower:
        return "jumta darbi"
    if "remont" in lower:
        return "remonta darbi"
    return ""


def _stage_score(stage_code):
    scores = {
        "won_reserved": 95,
        "objection": 82,
        "waiting_answer": 75,
        "offer_sent": 70,
        "offer_to_send": 62,
        "call_scheduled": 55,
        "needs_discovery": 40,
        "new_lead": 25,
        "unknown": 0,
    }
    return scores.get(stage_code, 0)


def _stage_label(stage_code):
    labels = {
        "won_reserved": "vienošanās / rezervācija",
        "objection": "iebildumi / sarunas",
        "waiting_answer": "gaida atbildi",
        "offer_sent": "piedāvājums nosūtīts",
        "offer_to_send": "piedāvājums jāsagatavo / jānosūta",
        "call_scheduled": "jāsazvana / jāvirza saruna",
        "needs_discovery": "jānoskaidro vajadzība",
        "new_lead": "jauns / aktīvs klients",
        "unknown": "nav skaidrs pipeline posms",
    }
    return labels.get(stage_code, "nav skaidrs pipeline posms")


def _stage_risk(stage_code):
    if stage_code in ["objection", "waiting_answer"]:
        return "vidējs"
    if stage_code in ["offer_to_send", "call_scheduled"]:
        return "zems"
    if stage_code == "won_reserved":
        return "zems"
    return "nav skaidrs"


def detect_stage_from_tasks(tasks):
    texts = [_task_text(t) for t in tasks or [] if _task_text(t)]
    blob = "\n".join(texts).lower()

    evidence = []
    stage = "unknown"

    if _contains(blob, ["piekrita", "apstiprināja", "apstiprinaja", "rezervē", "rezerve", "sākam", "sakam", "darbs rezervēts", "darbi rezervēti"]):
        stage = "won_reserved"
        evidence.append("ir pazīmes, ka klients piekritis / darbs rezervēts")
    elif _contains(blob, ["par dārgu", "par dargu", "padomās", "padomas", "salīdzin", "salidzin", "ne tagad", "vēlāk", "velak", "iebild"]):
        stage = "objection"
        evidence.append("ir klienta iebilduma vai vilcināšanās pazīmes")
    elif _contains(blob, ["piedāvājums nosūtīts", "piedavajums nosutits", "nosūtīju piedāvājumu", "nosutiju piedavajumu"]):
        stage = "offer_sent"
        evidence.append("piedāvājums izskatās jau nosūtīts")
    elif _contains(blob, ["jānosūta piedāvājums", "janosuta piedavajums", "jānosūta tāme", "janosuta tame", "sagatavot piedāvājumu", "uztaisi piedāvājumu"]):
        stage = "offer_to_send"
        evidence.append("ir uzdevums sagatavot / nosūtīt piedāvājumu")
    elif _contains(blob, ["jāpajautā", "japajauta", "par atbildi", "follow-up", "followup", "atgādin", "atgadin"]):
        stage = "waiting_answer"
        evidence.append("ir follow-up / jāprasa klienta atbilde")
    elif _contains(blob, ["jāzvana", "jazvana", "jāpiezvana", "japiezvana", "zvans", "sazvan"]):
        stage = "call_scheduled"
        evidence.append("ir zvana / saziņas uzdevums")
    elif texts:
        stage = "new_lead"
        evidence.append("ir aktīvi klienta darbi, bet pipeline posms vēl nav precīzs")

    return {
        "stage_code": stage,
        "stage": _stage_label(stage),
        "risk": _stage_risk(stage),
        "score": _stage_score(stage),
        "evidence": evidence,
    }


def _extract_deal_context(tasks):
    texts = [_task_text(t) for t in tasks or [] if _task_text(t)]
    combined = " | ".join(texts)
    subject = _extract_subject(combined)
    price = _extract_price(combined)
    offer_task = next((t for t in texts if _contains(t, ["piedāvāj", "piedavaj", "tāme", "tame", "jānosūta", "janosuta"])), "")
    followup_task = next((t for t in texts if _contains(t, ["jāpajautā", "japajauta", "par atbildi", "follow", "atgādin", "atgadin"])), "")
    call_task = next((t for t in texts if _contains(t, ["jāzvana", "jazvana", "jāpiezvana", "japiezvana", "zvans"])), "")
    job_start = ""
    m = re.search(r"(?i)(?:darbus|darbu)\s+(?:varam\s+)?(?:sākt|sakt|uzsākt|uzsakt)\s+(nākamnedēļ|nakamnedel|šonedēļ|sonedel|rīt|rit|parīt|parit|pirmdien|otrdien|trešdien|tresdien|ceturtdien|piektdien|sestdien|svētdien|svetdien)", combined)
    if m:
        job_start = _deadline_label(m.group(1))
    return {
        "subject": subject,
        "price": price,
        "offer_task": offer_task,
        "followup_task": followup_task,
        "call_task": call_task,
        "job_start": job_start,
    }


def _next_step_for_stage(stage_code, ctx):
    subject = ctx.get("subject") or "šo klienta darbu"
    job_start = ctx.get("job_start") or ""
    if stage_code == "offer_to_send":
        return "sagatavo un nosūti piedāvājumu; pēc nosūtīšanas uzliec follow-up termiņu."
    if stage_code == "waiting_answer":
        if job_start:
            return f"seko līdzi atbildei un mēģini dabūt konkrētu lēmumu / rezervēt darbu sākšanu {job_start}."
        return "seko līdzi atbildei un dabū konkrētu nākamo soli, nevis tikai “padomāšu”."
    if stage_code == "objection":
        return "noskaidro, vai iebildums ir par cenu, termiņu vai apjomu; tad dod precizētu atbildi un closing jautājumu."
    if stage_code == "call_scheduled":
        return "piezvani klientam un virzi sarunu uz konkrētu lēmumu vai precizējumu."
    if stage_code == "won_reserved":
        return "nofiksē rezervāciju / nākamo darba soli un pārbaudi, vai viss ir sagatavots izpildei."
    if stage_code == "new_lead":
        return f"noskaidro vajadzību un sagatavo nākamo soli par {subject}."
    return "iedod vairāk darba faktu par klientu, lai var noteikt pipeline posmu."


def build_client_sales_view(client_name, tasks=None, memory_snapshot=None):
    client = normalize_client_name(client_name)
    matched = client_tasks(client, tasks)
    stage = detect_stage_from_tasks(matched)
    ctx = _extract_deal_context(matched)

    if not client:
        return (
            "📈 Sales Brain\n\n"
            "Pasaki klienta vārdu, piemēram: `kurā posmā ir Andris`.\n\n"
            f"Versija: {SALES_BRAIN_VERSION}"
        )

    if not matched:
        return (
            f"📈 Sales pipeline — {client}\n\n"
            "Šim klientam šobrīd neredzu aktīvus darba taskus, tāpēc pipeline posmu nevaru noteikt.\n\n"
            f"Versija: {SALES_BRAIN_VERSION}"
        )

    lines = [
        f"📈 Sales pipeline — {client}",
        "",
        f"Stage: {stage['stage']}",
        f"Deal risks: {stage['risk']}",
        f"Deal score: {stage['score']}/100",
        "",
        "Darījuma konteksts:",
    ]
    if ctx.get("subject"):
        lines.append(f"• tēma: {ctx['subject']}")
    if ctx.get("price"):
        lines.append(f"• summa: {ctx['price']}")
    if ctx.get("job_start"):
        lines.append(f"• darbu sākšana: {ctx['job_start']}")
    if ctx.get("offer_task"):
        lines.append(f"• piedāvājums: {ctx['offer_task']}")
    if ctx.get("followup_task"):
        lines.append(f"• follow-up: {ctx['followup_task']}")
    if ctx.get("call_task"):
        lines.append(f"• zvans: {ctx['call_task']}")

    lines.extend(["", "Kāpēc šāds stage:"])
    if stage.get("evidence"):
        for item in stage["evidence"]:
            lines.append(f"• {item}")
    else:
        lines.append("• nav pietiekami daudz signālu")

    lines.extend([
        "",
        "Nākamais deal solis:",
        _next_step_for_stage(stage["stage_code"], ctx),
        "",
        "Ātrās komandas:",
        f"• ko rakstīt {client_dative(client)}",
        f"• sagatavo zvana plānu {client_dative(client)}",
        f"• ko atbildēt {client_dative(client)}",
        "",
        f"Versija: {SALES_BRAIN_VERSION}",
    ])
    return "\n".join(lines)


def _all_clients_from_tasks(tasks):
    clients = []
    seen = set()
    for task in tasks or []:
        text = _task_text(task)
        candidates = []
        c = _task_client(task)
        if c:
            candidates.append(c)
        for token in ["andris", "andri", "andrim", "jānis", "janis", "jānim", "janim", "anna", "annai"]:
            if re.search(rf"\b{re.escape(token)}\b", text.lower()):
                candidates.append(normalize_client_name(token))
        for c in candidates:
            if c and c not in seen:
                seen.add(c)
                clients.append(c)
    return clients


def _rank_clients(tasks):
    rows = []
    for client in _all_clients_from_tasks(tasks):
        matched = client_tasks(client, tasks)
        stage = detect_stage_from_tasks(matched)
        ctx = _extract_deal_context(matched)
        rows.append({"client": client, "stage": stage, "ctx": ctx, "task_count": len(matched)})
    rows.sort(key=lambda r: r["stage"]["score"], reverse=True)
    return rows


def build_sales_status_answer(tasks=None, memory_snapshot=None):
    rows = _rank_clients(tasks or [])
    lines = [
        "📈 Core 3.1.1 — Sales Stage Detection ir aktīvs. ✅",
        "",
        "Ko tas dara:",
        "• nosaka klienta pārdošanas / darījuma posmu no reālajiem taskiem;",
        "• izceļ klientus, kas ir tuvāk naudai;",
        "• pasaka nākamo deal soli, nevis tikai rāda tasku sarakstu.",
        "",
        "Komandas:",
        "• sales status",
        "• kurā posmā ir Andris",
        "• kas ar Andri pipeline",
        "• kurš klients ir tuvāk naudai",
        "• iestrēgušie klienti",
        "",
    ]
    if rows:
        lines.append("Aktīvie deal klienti:")
        for row in rows[:5]:
            ctx = row["ctx"]
            extra = []
            if ctx.get("price"):
                extra.append(ctx["price"])
            if ctx.get("subject"):
                extra.append(ctx["subject"])
            extra_text = f" | {'; '.join(extra)}" if extra else ""
            lines.append(f"• {row['client']} — {row['stage']['stage']} | score {row['stage']['score']}/100{extra_text}")
    else:
        lines.append("Aktīvie deal klienti: šobrīd nav atrasti klientu taski.")
    lines.extend(["", f"Versija: {SALES_BRAIN_VERSION}"])
    return "\n".join(lines)


def build_hot_deals_answer(tasks=None):
    rows = _rank_clients(tasks or [])
    if not rows:
        return f"🔥 Karstie klienti\n\nŠobrīd neredzu klientu deal taskus.\n\nVersija: {SALES_BRAIN_VERSION}"
    lines = ["🔥 Klienti tuvāk naudai", ""]
    for i, row in enumerate(rows[:5], 1):
        ctx = row["ctx"]
        bits = []
        if ctx.get("price"):
            bits.append(ctx["price"])
        if ctx.get("job_start"):
            bits.append(f"sākšana: {ctx['job_start']}")
        bits_text = f" ({', '.join(bits)})" if bits else ""
        lines.append(f"{i}. {row['client']} — {row['stage']['stage']}{bits_text}")
        lines.append(f"   Nākamais solis: {_next_step_for_stage(row['stage']['stage_code'], ctx)}")
    lines.extend(["", f"Versija: {SALES_BRAIN_VERSION}"])
    return "\n".join(lines)


def build_stuck_clients_answer(tasks=None):
    rows = [r for r in _rank_clients(tasks or []) if r["stage"]["stage_code"] in ["waiting_answer", "objection"]]
    if not rows:
        return f"⚠️ Iestrēgušie klienti\n\nŠobrīd neredzu klientus ar gaidīšanas vai iebildumu stage.\n\nVersija: {SALES_BRAIN_VERSION}"
    lines = ["⚠️ Iestrēgušie / riska klienti", ""]
    for row in rows[:5]:
        ctx = row["ctx"]
        lines.append(f"• {row['client']} — {row['stage']['stage']}")
        lines.append(f"  Risks: {row['stage']['risk']}")
        lines.append(f"  Nākamais solis: {_next_step_for_stage(row['stage']['stage_code'], ctx)}")
    lines.extend(["", f"Versija: {SALES_BRAIN_VERSION}"])
    return "\n".join(lines)


def sales_status_answer():
    return build_sales_status_answer([])


def is_sales_command(text):
    lower = _lower(text)
    if lower in ["sales", "sales status", "sales brain", "pipeline status", "deal status"]:
        return True
    if any(x in lower for x in ["pipeline", "kurā posmā", "kurā posma", "kura posmā", "kura posma", "sales stage", "darījuma posm", "darijuma posm"]):
        return True
    if any(x in lower for x in ["kurš klients ir tuvāk naudai", "kurs klients ir tuvak naudai", "karstie klienti", "hot deals", "tuvāk naudai", "tuvak naudai"]):
        return True
    if any(x in lower for x in ["iestrēgušie klienti", "iestregusie klienti", "iestrēgušie piedāvājumi", "iestregusie piedavajumi"]):
        return True
    return False


def build_sales_answer(user_text, tasks=None, memory_snapshot=None):
    lower = _lower(user_text)
    if lower in ["sales", "sales status", "sales brain", "pipeline status", "deal status"]:
        return build_sales_status_answer(tasks, memory_snapshot)
    if any(x in lower for x in ["kurš klients ir tuvāk naudai", "kurs klients ir tuvak naudai", "karstie klienti", "hot deals", "tuvāk naudai", "tuvak naudai"]):
        return build_hot_deals_answer(tasks)
    if any(x in lower for x in ["iestrēgušie klienti", "iestregusie klienti", "iestrēgušie piedāvājumi", "iestregusie piedavajumi"]):
        return build_stuck_clients_answer(tasks)
    client = extract_client(user_text, tasks=tasks, memory_snapshot=memory_snapshot)
    return build_client_sales_view(client, tasks, memory_snapshot)
