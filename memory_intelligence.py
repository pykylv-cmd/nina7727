"""
memory_intelligence.py
NinaOS Core 2.8 — Memory Intelligence V1

Mērķis:
- dot Ninai aktīvu darba atmiņas snapshotu;
- saprast īsās turpinājuma komandas pēc iepriekšējā darba konteksta;
- neiejaukties Task / Follow-up / Initiative / Client Work ceļos, ja komanda jau ir pilna.
"""

from datetime import datetime, timezone

MEMORY_INTELLIGENCE_VERSION = "Core 2.8 — Memory Intelligence V1"


def _clean(text):
    return str(text or "").strip()


def _lower(text):
    return _clean(text).lower()


def _now():
    return datetime.now(timezone.utc).isoformat()


def _task_title(task):
    if not isinstance(task, dict):
        return ""
    return _clean(task.get("title") or task.get("raw_text") or task.get("text") or "")


def _extract_client_from_task(task):
    title = _task_title(task).lower()
    if "andrim" in title or "andri" in title or "andris" in title:
        return "Andris"
    client = _clean((task or {}).get("client") or (task or {}).get("client_name") or "")
    if client:
        return client[:1].upper() + client[1:]
    return ""


def _classify_task(task):
    title = _task_title(task).lower()
    if "piedāv" in title or "piedav" in title:
        return "offer"
    if "jāpajaut" in title or "japajaut" in title or "par atbildi" in title or "follow" in title:
        return "follow_up"
    if "jāzvana" in title or "jazvana" in title or "piezvan" in title:
        return "call"
    return "task"


def build_memory_snapshot(user_id, tasks=None, context=None, recent_messages=None):
    """Atgriež strukturētu aktīvās darba atmiņas snapshotu."""
    tasks = tasks or []
    context = context or {}
    recent_messages = recent_messages or []

    active_tasks = []
    seen = set()
    for task in tasks:
        title = _task_title(task)
        if not title:
            continue
        key = title.lower()
        if key in seen:
            continue
        seen.add(key)
        if isinstance(task, dict) and str(task.get("status") or "open").lower() == "completed":
            continue
        active_tasks.append(task)

    last_client = context.get("client") or context.get("last_client") or ""
    if not last_client:
        for task in active_tasks:
            last_client = _extract_client_from_task(task)
            if last_client:
                break

    offer_task = ""
    followup_task = ""
    call_task = ""
    last_task = ""

    for task in active_tasks:
        title = _task_title(task)
        kind = _classify_task(task)
        if not last_task:
            last_task = title
        if kind == "offer" and not offer_task:
            offer_task = title
        if kind == "follow_up" and not followup_task:
            followup_task = title
        if kind == "call" and not call_task:
            call_task = title

    return {
        "user_id": str(user_id),
        "version": MEMORY_INTELLIGENCE_VERSION,
        "last_client": last_client,
        "topic": context.get("topic") or "",
        "last_deadline": context.get("last_deadline") or "",
        "last_task": last_task,
        "offer_task": offer_task,
        "followup_task": followup_task,
        "call_task": call_task,
        "active_task_count": len(active_tasks),
        "recent_messages": recent_messages[-5:],
        "created_at": _now(),
    }


def memory_status_answer(snapshot=None):
    snapshot = snapshot or {}
    lines = [
        "🧠 Core 2.8 — Memory Intelligence V1 ir aktīvs. ✅",
        "",
        "Ko tas dara:",
        "• savāc aktīvo darba atmiņas snapshotu;",
        "• atceras pēdējo klientu, tasku, follow-up un piedāvājumu;",
        "• palīdz īsām turpinājuma komandām nenokrist tukšā čatā.",
        "",
        "Aktīvā darba atmiņa:",
        f"• klients: {snapshot.get('last_client') or '-'}",
        f"• tēma: {snapshot.get('topic') or '-'}",
        f"• pēdējais task: {snapshot.get('last_task') or '-'}",
        f"• piedāvājums: {snapshot.get('offer_task') or '-'}",
        f"• follow-up: {snapshot.get('followup_task') or '-'}",
        f"• zvans: {snapshot.get('call_task') or '-'}",
        f"• aktīvie darbi: {snapshot.get('active_task_count', 0)}",
        "",
        "Testi:",
        "• memory status",
        "• un pēc tam?",
        "• ko vēl?",
        "• un ar to klientu?",
        "",
        f"Versija: {MEMORY_INTELLIGENCE_VERSION}",
    ]
    return "\n".join(lines)


def is_memory_status_command(text):
    lower = _lower(text)
    return lower in {
        "memory status", "memory intelligence", "atmiņas statuss", "atminas statuss",
        "darba atmiņa", "darba atmina", "core 2.8", "core 28",
    }


def resolve_memory_command(text, snapshot=None):
    """Pārraksta īsas turpinājuma komandas, izmantojot aktīvo darba atmiņu."""
    raw = _clean(text)
    lower = raw.lower().strip(" .!?;")
    snapshot = snapshot or {}
    client = snapshot.get("last_client") or ""

    if not raw:
        return raw

    # Ja komanda jau ir skaidra darba komanda, neiejaucamies.
    explicit_markers = [
        "jā", "ja", "rīt", "rit", "šodien", "sodien", "piektdien",
        "kas notiek ar", "klienti", "mana diena", "ko man tagad darīt",
    ]
    if any(lower.startswith(m) for m in explicit_markers):
        return raw

    if lower in ["un pēc tam", "un pec tam", "pēc tam", "pec tam", "ko tālāk", "ko talak", "tālāk", "talak", "ko vēl", "ko vel"]:
        return "ko man tagad darīt"

    if client and lower in ["un ar to klientu", "ar to klientu", "kas ar klientu", "kas ar viņu", "kas ar vinu"]:
        if client == "Andris":
            return "kas notiek ar Andri"
        return f"kas notiek ar {client}"

    if client and lower in ["un piedāvājums", "piedāvājums", "piedavajums", "un par piedāvājumu", "un par piedavajumu"]:
        if client == "Andris":
            return "kas notiek ar Andri"
        return f"kas notiek ar {client}"

    if client and lower in ["un follow up", "un follow-up", "follow up", "follow-up", "un atbilde", "par atbildi"]:
        if client == "Andris":
            return "kas notiek ar Andri"
        return f"kas notiek ar {client}"

    return raw
