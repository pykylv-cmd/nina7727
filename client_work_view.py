"""
client_work_view.py
NinaOS Client Work View — V1.1 + Sales Pipeline bridge

V1.1:
- saglabā veco Client Work View komandu;
- labo "Kas notiek ar Andris" -> "Kas notiek ar Andri";
- ja sales_pipeline.py ir pieejams, rāda CRM/Pipeline skatu klientam;
- ja sales_pipeline.py nav pieejams, droši atgriežas uz V1.0 klienta darbu skatu.
"""

CLIENT_WORK_VIEW_VERSION = "Client Work View V1.1 + Sales Pipeline bridge"

try:
    from sales_pipeline import (
        format_client_crm_view,
        SALES_PIPELINE_VERSION,
    )
except Exception as e:
    print("sales_pipeline.py imports nav pieejams client_work_view.py:", e)
    SALES_PIPELINE_VERSION = "Sales Pipeline nav pieslēgts"

    def format_client_crm_view(client_name, tasks):
        return ""


def _clean(text):
    return (text or "").strip()


def normalize_client_name_v1(name):
    raw = _clean(name)
    if not raw:
        return ""

    mapping = {
        "andrim": "Andris",
        "andri": "Andris",
        "andris": "Andris",
        "annai": "Anna",
        "anna": "Anna",
        "jānim": "Jānis",
        "janim": "Jānis",
        "janis": "Jānis",
        "jānis": "Jānis",
    }
    lower = raw.lower().strip(" .,!?:;")
    if lower in mapping:
        return mapping[lower]
    return raw[:1].upper() + raw[1:]


def client_name_dative_v1(client_name):
    """
    V1.1 kosmētiskais locījums virsrakstam.
    Tas labo galveno zināmo kļūdu:
    "Kas notiek ar Andris" -> "Kas notiek ar Andri".
    """
    name = normalize_client_name_v1(client_name)
    mapping = {
        "Andris": "Andri",
        "Jānis": "Jāni",
        "Janis": "Jāni",
        "Anna": "Annu",
    }
    return mapping.get(name, name)


def extract_client_from_query(text):
    raw = _clean(text)
    lower = raw.lower()

    prefixes = [
        "kas notiek ar ",
        "kas ar ",
        "client work ",
        "andra pipeline",
        "andra statuss",
        "andris pipeline",
        "andris statuss",
    ]

    # Speciālie īsie testi Andrim
    if lower in ["andra pipeline", "andra statuss", "andris pipeline", "andris statuss", "kas ar andri tālāk", "kas ar andri talak"]:
        return "Andris"

    for prefix in prefixes:
        if lower.startswith(prefix):
            tail = raw[len(prefix):].strip(" .,!?:;")
            return normalize_client_name_v1(tail)

    return ""


def task_matches_client(task, client_name):
    client_name = normalize_client_name_v1(client_name)
    if not client_name:
        return False

    task = task or {}
    task_client = normalize_client_name_v1(task.get("client", ""))
    title = _clean(task.get("title", ""))
    raw_text = _clean(task.get("raw_text", ""))

    if task_client and task_client.lower() == client_name.lower():
        return True

    blob = f"{title} {raw_text}".lower()

    variants = {
        "Andris": ["andris", "andri", "andrim"],
        "Jānis": ["jānis", "janis", "jāni", "jani", "jānim", "janim"],
        "Anna": ["anna", "annu", "annai"],
    }.get(client_name, [client_name.lower()])

    return any(v in blob for v in variants)


def _legacy_client_work_view(client_name, matched):
    header_name = client_name_dative_v1(client_name)

    lines = [
        f"👥 Kas notiek ar {header_name}",
        "",
        f"Aktīvie darbi: {len(matched)}",
        ""
    ]

    for i, task in enumerate(matched, 1):
        title = _clean(task.get("title", ""))
        deadline = _clean(task.get("deadline_label", "")) or _clean(task.get("deadline", ""))
        followup = bool(task.get("followup"))
        suffix = []
        if deadline:
            suffix.append(deadline)
        if followup:
            suffix.append("follow-up")
        suffix_text = f" ({', '.join(suffix)})" if suffix else ""
        lines.append(f"{i}. {title}{suffix_text}")

    lines.append("")
    lines.append("Šis ir klienta skats — visi darbi vienā vietā.")
    lines.append("")
    lines.append(f"Versija: {CLIENT_WORK_VIEW_VERSION}")
    return "\n".join(lines)


def build_client_work_view(client_name, tasks):
    client_name = normalize_client_name_v1(client_name)

    if not client_name:
        return (
            "👥 Client Work View\n\n"
            "Pasaki klienta vārdu, piemēram:\n"
            "kas notiek ar Andri\n\n"
            f"Versija: {CLIENT_WORK_VIEW_VERSION}"
        )

    matched = [task for task in (tasks or []) if task_matches_client(task, client_name)]

    if not matched:
        return (
            f"👥 Klientam {client_name_dative_v1(client_name)} šobrīd neredzu aktīvus darbus.\n\n"
            "Ja vajag, vispirms iedod uzdevumu.\n\n"
            f"Versija: {CLIENT_WORK_VIEW_VERSION}"
        )

    # Ja sales_pipeline.py ir pieslēgts, rādām augstāka līmeņa CRM skatu.
    try:
        crm_view = format_client_crm_view(client_name, matched)
        if crm_view:
            return crm_view
    except Exception as e:
        print("build_client_work_view sales pipeline kļūda:", repr(e))

    # Drošs fallback uz veco Client Work View.
    return _legacy_client_work_view(client_name, matched)


def client_work_status():
    return (
        "👥 Client Work View V1.1 ir aktīvs. ✅\n\n"
        "Ja sales_pipeline.py ir pieslēgts, komanda rāda arī CRM/Pipeline skatu.\n\n"
        "Tests:\n"
        "kas notiek ar Andri\n\n"
        "Sagaidāmais rezultāts:\n"
        "- pareizs virsraksts: Kas notiek ar Andri\n"
        "- redzami Andra aktīvie darbi\n"
        "- redzams pipeline statuss un nākamais solis\n\n"
        f"Client Work versija: {CLIENT_WORK_VIEW_VERSION}\n"
        f"Sales Pipeline: {SALES_PIPELINE_VERSION}"
    )
