"""
sales_pipeline.py
NinaOS — Sales Pipeline / Client CRM V1.0

Mērķis:
- Noteikt klienta pārdošanas/pipeline statusu no darbiem un teksta.
- Sagatavot klienta CRM skatu.
- Sagatavot kopējo klientu pipeline skatu.
- Atrast riskus: follow-up, piedāvājumi, iestrēguši klienti.

Šis modulis ir drošs: tas pats nemaina datubāzi.
Tas tikai analizē jau esošu tekstu / taskus / klienta kontekstu un atgriež strukturētu rezultātu.
"""

SALES_PIPELINE_VERSION = "Sales Pipeline / Client CRM V1.0"


PIPELINE_STAGES = {
    "lead": "jauns leads",
    "contacted": "kontakts uzsākts",
    "waiting_reply": "gaida atbildi",
    "offer_to_send": "jānosūta piedāvājums",
    "offer_sent": "piedāvājums nosūtīts",
    "negotiation": "sarunās",
    "won": "uzvarēts",
    "lost": "zaudēts",
    "unknown": "nav skaidrs",
}


def _clean(text):
    return (text or "").strip()


def _lower(text):
    return _clean(text).lower()


def _contains_any(text, phrases):
    lower = _lower(text)
    return any(p in lower for p in phrases)


def normalize_client_name(name):
    """
    V1.0 vienkārša normalizācija.
    Locījumu labošanu vēlāk var paplašināt Client Work View V1.1.
    """
    name = _clean(name)
    if not name:
        return ""
    return name[0].upper() + name[1:]


def detect_pipeline_stage(text):
    """
    Nosaka pārdošanas stadiju no dabiskas valodas.
    Atgriež:
    {
        stage,
        confidence,
        reason,
        offer_status,
        next_step_hint
    }
    """
    raw = _clean(text)
    lower = raw.lower()

    if not lower:
        return _result("unknown", 0.1, "Tukšs teksts")

    # Won / lost jābūt augstāk, lai tie pārsit citus signālus
    if _contains_any(lower, [
        "piekrita", "apstiprināja", "apstiprinaja", "darījums notika", "darijums notika",
        "samaksāja", "samaksaja", "paņēma", "panema", "noslēdzām", "nosledzam",
        "klients piekrita", "ir mūsu klients", "ir musu klients"
    ]):
        return _result("won", 0.96, "Tekstā redzams pozitīvs darījuma iznākums", "accepted", "nofiksēt nākamo apkalpošanas soli")

    if _contains_any(lower, [
        "atteicās", "atteicas", "negrib", "neinteresē", "neinterese", "pa dārgu", "pa dargu",
        "nebūs", "nebus", "nenotiks", "zaudēts", "zaudets"
    ]):
        return _result("lost", 0.94, "Tekstā redzams atteikums vai zaudēts darījums", "rejected", "atzīmēt iemeslu")

    if _contains_any(lower, [
        "jānosūta piedāvājums", "janosuta piedavajums", "nosūtīt piedāvājumu", "nosutit piedavajumu",
        "sagatavot piedāvājumu", "sagatavot piedavajumu", "piedāvājums jānosūta", "piedavajums janosuta",
        "rīt jānosūta piedāvājums", "rit janosuta piedavajums"
    ]):
        return _result("offer_to_send", 0.95, "Tekstā ir uzdevums nosūtīt/sagatavot piedāvājumu", "to_send", "nosūtīt piedāvājumu")

    if _contains_any(lower, [
        "piedāvājums nosūtīts", "piedavajums nosutits", "nosūtīju piedāvājumu", "nosutiju piedavajumu",
        "aizsūtīju piedāvājumu", "aizsutiju piedavajumu"
    ]):
        return _result("offer_sent", 0.95, "Tekstā redzams, ka piedāvājums jau nosūtīts", "sent", "sekot atbildei")

    if _contains_any(lower, [
        "gaidu atbildi", "gaida atbildi", "jāpajautā par atbildi", "japajauta par atbildi",
        "jāpajautā andrim par atbildi", "japajauta andrim par atbildi",
        "follow-up", "folowup", "pajautāt par atbildi", "pajautat par atbildi",
        "atgādināt", "atgadinat"
    ]):
        return _result("waiting_reply", 0.92, "Tekstā ir gaidīšanas/follow-up signāls", "unknown", "uztaisīt follow-up")

    if _contains_any(lower, [
        "sarunās", "sarunas", "runājam", "runajam", "vienojamies", "precizējam", "precizejam",
        "apspriežam", "apspriezam"
    ]):
        return _result("negotiation", 0.86, "Tekstā ir sarunu/precizēšanas signāls", "unknown", "turpināt sarunu")

    if _contains_any(lower, [
        "sazinājos", "sazinajos", "uzrakstīju", "uzrakstiju", "piezvanīju", "piezvaniju",
        "pirmais kontakts", "kontakts"
    ]):
        return _result("contacted", 0.78, "Tekstā ir kontakta uzsākšanas signāls", "unknown", "noteikt nākamo soli")

    if _contains_any(lower, [
        "klients", "leads", "potenciāls klients", "potencials klients"
    ]):
        return _result("lead", 0.65, "Tekstā ir klienta/leada signāls", "unknown", "noskaidrot vajadzību")

    return _result("unknown", 0.2, "Nav pietiekama pipeline signāla", "unknown", "")


def _result(stage, confidence, reason, offer_status="unknown", next_step_hint=""):
    return {
        "stage": stage,
        "stage_label": PIPELINE_STAGES.get(stage, PIPELINE_STAGES["unknown"]),
        "confidence": float(confidence),
        "reason": reason,
        "offer_status": offer_status,
        "next_step_hint": next_step_hint,
        "version": SALES_PIPELINE_VERSION,
    }


def analyze_client_tasks(client_name, tasks):
    """
    Analizē klienta aktīvos darbus un izsecina CRM statusu.

    tasks var būt saraksts ar stringiem vai dict:
    - "rīt jānosūta piedāvājums Andrim"
    - {"text": "...", "due": "rīt", "type": "follow-up"}
    """
    client = normalize_client_name(client_name)
    task_texts = []

    for task in tasks or []:
        if isinstance(task, dict):
            text = task.get("text") or task.get("title") or task.get("task") or ""
        else:
            text = str(task)
        if text:
            task_texts.append(text)

    combined = "\n".join(task_texts)
    stage_result = detect_pipeline_stage(combined)

    offer_status = stage_result.get("offer_status", "unknown")
    if offer_status == "unknown":
        if _contains_any(combined, ["piedāvājums", "piedavajums"]):
            offer_status = "mentioned"
        else:
            offer_status = "none"

    followup_count = 0
    offer_task_count = 0

    for text in task_texts:
        if _contains_any(text, ["follow-up", "atbildi", "atgādināt", "atgadinat", "pajautāt", "pajautat"]):
            followup_count += 1
        if _contains_any(text, ["piedāvājums", "piedavajums"]):
            offer_task_count += 1

    risk = detect_client_risk(
        stage=stage_result["stage"],
        tasks=task_texts,
        followup_count=followup_count,
        offer_task_count=offer_task_count,
    )

    next_step = infer_next_step(stage_result["stage"], task_texts, stage_result.get("next_step_hint", ""))

    return {
        "client_name": client,
        "pipeline_stage": stage_result["stage"],
        "pipeline_stage_label": stage_result["stage_label"],
        "pipeline_confidence": stage_result["confidence"],
        "pipeline_reason": stage_result["reason"],
        "offer_status": offer_status,
        "active_tasks": task_texts,
        "active_task_count": len(task_texts),
        "followup_count": followup_count,
        "offer_task_count": offer_task_count,
        "next_step": next_step,
        "risk": risk,
        "version": SALES_PIPELINE_VERSION,
    }


def infer_next_step(stage, task_texts, fallback=""):
    """
    Izvēlas praktisku nākamo soli.
    Prioritāte:
    1) konkrēts task ar follow-up/atbildi
    2) konkrēts task ar piedāvājumu
    3) stage fallback
    """
    for text in task_texts:
        if _contains_any(text, ["follow-up", "atbildi", "pajautāt", "pajautat", "atgādināt", "atgadinat"]):
            return text

    for text in task_texts:
        if _contains_any(text, ["piedāvājums", "piedavajums"]):
            return text

    if fallback:
        return fallback

    defaults = {
        "lead": "uzsākt kontaktu un noskaidrot vajadzību",
        "contacted": "nofiksēt nākamo konkrēto soli",
        "waiting_reply": "uztaisīt follow-up",
        "offer_to_send": "nosūtīt piedāvājumu",
        "offer_sent": "sekot klienta atbildei",
        "negotiation": "virzīt sarunu uz lēmumu",
        "won": "nofiksēt nākamo apkalpošanas soli",
        "lost": "pierakstīt atteikuma iemeslu",
    }
    return defaults.get(stage, "nav noteikts nākamais solis")


def detect_client_risk(stage, tasks, followup_count=0, offer_task_count=0):
    """
    V1.0 riska noteikšana bez datumu matemātikas.
    Datumu salīdzināšanu pievienos V1.1, kad būs droši zināms esošais task datu formāts.
    """
    risks = []

    if stage == "waiting_reply" and followup_count == 0:
        risks.append("klients gaida atbildes stadijā, bet nav follow-up darba")

    if stage == "offer_to_send" and offer_task_count == 0:
        risks.append("piedāvājuma stadija, bet nav redzama piedāvājuma uzdevuma")

    if not tasks:
        risks.append("klientam nav aktīva nākamā soļa")

    if stage == "unknown" and tasks:
        risks.append("ir aktīvi darbi, bet nav skaidrs pipeline statuss")

    if not risks:
        return {
            "has_risk": False,
            "risk_level": "low",
            "reasons": [],
        }

    level = "medium"
    if any("nav aktīva nākamā soļa" in r for r in risks):
        level = "high"

    return {
        "has_risk": True,
        "risk_level": level,
        "reasons": risks,
    }


def format_client_crm_view(client_name, tasks):
    """
    Gatavs teksts Telegram/Nina atbildei.
    Šo var pieslēgt pie komandas:
    - kas notiek ar Andri
    - Andra pipeline
    - Andra statuss
    """
    crm = analyze_client_tasks(client_name, tasks)

    lines = []
    lines.append(f"👤 {crm['client_name']}")
    lines.append("")
    lines.append(f"Pipeline: {crm['pipeline_stage_label']}")
    lines.append(f"Piedāvājums: {format_offer_status(crm['offer_status'])}")
    lines.append(f"Aktīvie darbi: {crm['active_task_count']}")

    if crm["active_tasks"]:
        lines.append("")
        for idx, task in enumerate(crm["active_tasks"], start=1):
            lines.append(f"{idx}. {task}")

    lines.append("")
    lines.append("Nākamais solis:")
    lines.append(crm["next_step"])

    if crm["risk"]["has_risk"]:
        lines.append("")
        lines.append("Risks:")
        for reason in crm["risk"]["reasons"]:
            lines.append(f"- {reason}")
    else:
        lines.append("")
        lines.append("Risks: zems")

    lines.append("")
    lines.append(f"Versija: {SALES_PIPELINE_VERSION}")
    return "\n".join(lines)


def format_offer_status(status):
    labels = {
        "none": "nav",
        "unknown": "nav skaidrs",
        "mentioned": "pieminēts",
        "to_send": "jānosūta",
        "sent": "nosūtīts",
        "accepted": "pieņemts",
        "rejected": "atteikts",
    }
    return labels.get(status, status or "nav skaidrs")


def get_pipeline_overview(client_task_map):
    """
    client_task_map piemērs:
    {
        "Andris": ["piektdien jāpajautā Andrim par atbildi", "rīt jānosūta piedāvājums Andrim"],
        "Jānis": ["jānosūta piedāvājums Jānim"]
    }
    """
    grouped = {stage: [] for stage in PIPELINE_STAGES.keys()}

    for client_name, tasks in (client_task_map or {}).items():
        crm = analyze_client_tasks(client_name, tasks)
        grouped.setdefault(crm["pipeline_stage"], []).append(crm)

    return grouped


def format_pipeline_overview(client_task_map):
    grouped = get_pipeline_overview(client_task_map)

    lines = []
    lines.append("📊 Sales Pipeline / Client CRM")
    lines.append("")

    any_clients = False

    order = [
        "waiting_reply",
        "offer_to_send",
        "offer_sent",
        "negotiation",
        "contacted",
        "lead",
        "won",
        "lost",
        "unknown",
    ]

    for stage in order:
        clients = grouped.get(stage, [])
        if not clients:
            continue

        any_clients = True
        lines.append(f"{PIPELINE_STAGES.get(stage, stage)}:")
        for crm in clients:
            risk_mark = " ⚠️" if crm["risk"]["has_risk"] else ""
            lines.append(f"- {crm['client_name']} — {crm['next_step']}{risk_mark}")
        lines.append("")

    if not any_clients:
        lines.append("Nav aktīvu klientu pipeline skatam.")

    lines.append(f"Versija: {SALES_PIPELINE_VERSION}")
    return "\n".join(lines).strip()


def get_stuck_clients(client_task_map):
    stuck = []

    for client_name, tasks in (client_task_map or {}).items():
        crm = analyze_client_tasks(client_name, tasks)
        if crm["risk"]["has_risk"]:
            stuck.append(crm)

    return stuck


def format_stuck_clients(client_task_map):
    stuck = get_stuck_clients(client_task_map)

    lines = []
    lines.append("⚠️ Klienti ar risku / iestrēgumu")
    lines.append("")

    if not stuck:
        lines.append("Šobrīd nav redzamu CRM risku.")
    else:
        for crm in stuck:
            lines.append(f"{crm['client_name']} — {crm['pipeline_stage_label']}")
            for reason in crm["risk"]["reasons"]:
                lines.append(f"- {reason}")
            lines.append(f"Nākamais solis: {crm['next_step']}")
            lines.append("")

    lines.append(f"Versija: {SALES_PIPELINE_VERSION}")
    return "\n".join(lines).strip()


def is_pipeline_command(text):
    lower = _lower(text)
    return lower in [
        "pipeline",
        "mani klienti",
        "klienti",
        "klientu statuss",
        "parādi manus klientus",
        "paradi manus klientus",
        "sales pipeline",
        "crm",
        "client crm",
    ]


def is_stuck_command(text):
    lower = _lower(text)
    return lower in [
        "kas iestrēdzis",
        "kas iestredzis",
        "kur deg",
        "kam jātaisa follow-up",
        "kam jataisa follow-up",
        "kam jānosūta piedāvājums",
        "kam janosuta piedavajums",
        "kurš klients stāv uz vietas",
        "kurs klients stav uz vietas",
    ]


def is_client_pipeline_command(text):
    lower = _lower(text)
    return (
        "pipeline" in lower
        or "statuss" in lower
        or "kas notiek ar" in lower
        or "kas ar" in lower
        or "tālāk" in lower
        or "talak" in lower
    )
