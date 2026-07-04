"""
employee_brain.py
NinaOS Core 3.0 — Employee Brain v3

Mērķis:
- Employee Brain kļūst par darba vadības smadzenēm, nevis tikai Core statusa atbildētāju;
- izmanto Context + Memory snapshotu, lai saprastu aktīvo klientu un nākamo darbu;
- Core/roadmap jautājumos dod skaidru arhitekta līmeņa nākamo soli;
- nesalauž esošos Task / Follow-up / Initiative / Client Work ceļus.
"""

CORE_VERSION = "Core 3.0 — Employee Brain v3"

try:
    from think_engine import classify_intent, THINK_VERSION
except Exception as e:
    print("think_engine.py imports nav pieejams:", e)
    THINK_VERSION = "Think Engine nav pieslēgts"

    def classify_intent(text):
        return {"intent": "GENERAL", "raw_text": text or "", "confidence": 0.0, "reason": "Think Engine fallback", "version": THINK_VERSION}

try:
    from learning_engine import build_learning_snapshot, format_learning_snapshot, current_learning_focus, LEARNING_VERSION
except Exception as e:
    print("learning_engine.py imports nav pieejams:", e)
    LEARNING_VERSION = "Learning Engine nav pieslēgts"

    def build_learning_snapshot(intent="GENERAL", issue=""):
        return {"intent": intent, "issue": issue, "learned": "Mācīšanās modulis nav pieslēgts.", "avoid": "", "next_behavior": "", "principles": [], "version": LEARNING_VERSION}

    def format_learning_snapshot(snapshot):
        return snapshot.get("learned", "Mācīšanās modulis nav pieslēgts.")

    def current_learning_focus():
        return "Learning Engine nav pieslēgts."

try:
    from quality_engine import evaluate_answer, improve_answer as quality_improve_answer, format_quality_review, QUALITY_VERSION
except Exception as e:
    print("quality_engine.py imports nav pieejams:", e)
    QUALITY_VERSION = "Quality Engine nav pieslēgts"

    def evaluate_answer(answer, context=None, thought=None):
        return {"score": 85, "status": "PASS", "issues": [], "version": QUALITY_VERSION}

    def quality_improve_answer(answer, context=None, thought=None, review=None):
        return answer or "Es sapratu. Nākamais solis: izvēlamies konkrētu darbu."

    def format_quality_review(review):
        return f"Quality Engine nav pieslēgts. Score: {review.get('score', 0)}"


def _clean(value):
    return str(value or "").strip()


def _lower(value):
    return _clean(value).lower()


def _split_items(value):
    value = _clean(value)
    if not value:
        return []
    import re
    return [p.strip() for p in re.split(r"[;\n|]+", value) if p.strip()]


def _with_version(answer):
    answer = _clean(answer)
    if f"Versija: {CORE_VERSION}" not in answer:
        answer += f"\n\nVersija: {CORE_VERSION}"
    return answer


def _ensure_next_step(answer):
    lower = answer.lower()
    if "nākamais" not in lower and "solis" not in lower:
        answer = answer.rstrip() + "\n\nNākamais solis: izvēlamies vienu konkrētu darbu un virzām to tālāk."
    return answer


def _snap(snapshot, key, default=""):
    if not isinstance(snapshot, dict):
        return default
    return _clean(snapshot.get(key) or default)


def _active_client(snapshot):
    return _snap(snapshot, "last_client") or _snap(snapshot, "client")


def build_employee_context(user=None, memory_snapshot=None, context_snapshot=None):
    user = user or {}
    memory_snapshot = memory_snapshot or {}
    context_snapshot = context_snapshot or {}

    name = _clean(user.get("name"))
    profession = _clean(user.get("profession"))
    projects = _clean(user.get("projects"))
    facts = _clean(user.get("facts"))
    hobbies = _clean(user.get("hobbies"))

    active_client = _active_client(memory_snapshot) or _clean(context_snapshot.get("client") or context_snapshot.get("last_client"))
    offer_task = _snap(memory_snapshot, "offer_task")
    followup_task = _snap(memory_snapshot, "followup_task")
    call_task = _snap(memory_snapshot, "call_task")
    last_task = _snap(memory_snapshot, "last_task")
    active_task_count = memory_snapshot.get("active_task_count", 0) if isinstance(memory_snapshot, dict) else 0

    top_work = offer_task or followup_task or call_task or last_task

    return {
        "name": name,
        "display_name": name or "kolēģi",
        "profession": profession,
        "projects": projects,
        "project_items": _split_items(projects),
        "facts": facts,
        "fact_items": _split_items(facts),
        "hobbies": hobbies,
        "mission": (
            "NinaOS mērķis ir izveidot AI operētājsistēmu, kur AI darbinieki palīdz cilvēkiem "
            "un uzņēmumiem strādāt gudrāk, ar kopīgu atmiņu, kontekstu un darba kvalitāti."
        ),
        "current_work": "Core 3.0 — Employee Brain v3",
        "current_priority": (
            "savienot Context 2.7.1 + Memory Intelligence 2.8 ar Employee Brain, lai Nina domā kā darba darbiniece, "
            "nevis tikai atbild kā čatbots"
        ),
        "next_real_step": "pēc Core 3.0 testa fiksēt stable checkpoint un tad sākt AI darbinieku slāņa projektēšanu",
        "memory_snapshot": memory_snapshot,
        "context_snapshot": context_snapshot,
        "active_client": active_client,
        "offer_task": offer_task,
        "followup_task": followup_task,
        "call_task": call_task,
        "last_task": last_task,
        "top_work": top_work,
        "active_task_count": active_task_count,
    }


def employee_brain_status(user=None, memory_snapshot=None, context_snapshot=None):
    ctx = build_employee_context(user, memory_snapshot, context_snapshot)
    name = ctx.get("display_name")
    active_client = ctx.get("active_client") or "-"
    top_work = ctx.get("top_work") or "-"

    return _with_version(
        f"🧠 Core 3.0 — Employee Brain v3 ir aktīvs. ✅\n\n"
        f"{name}, tagad Nina strādā kā AI darbiniece ar darba smadzenēm, nevis tikai kā sarunas bots.\n\n"
        "Ko v3 dara:\n"
        "• izmanto Context 2.7.1, lai saprastu, par ko ir runa;\n"
        "• izmanto Memory Intelligence 2.8, lai redzētu aktīvo darba snapshotu;\n"
        "• izvēlas darba virzienu: klients, piedāvājums, follow-up, zvans vai nākamais solis;\n"
        "• samazina tukšo GENERAL atbilžu risku.\n\n"
        "Aktīvais darba stāvoklis:\n"
        f"• klients: {active_client}\n"
        f"• top darbs: {top_work}\n"
        f"• aktīvie darbi: {ctx.get('active_task_count') or 0}\n\n"
        "Testi:\n"
        "• employee status\n"
        "• core 3.0\n"
        "• ko darām tālāk NinaOS\n"
        "• ko darām ar Andri\n\n"
        "Nākamais solis: pārbaudām, vai Employee Brain dod darba vadības atbildi un nekrīt atpakaļ vecajā čatbotu stilā."
    )


def _classify_employee_v3(text, thought=None):
    lower = _lower(text)
    if not lower:
        return "EMPTY"

    if lower in {"employee status", "employee brain", "employee brain status", "core 3.0", "core 30", "core status", "nina core"}:
        return "STATUS"

    if "ninaos misija" in lower or "mūsu misija" in lower or "musu misija" in lower:
        return "MISSION"

    if any(x in lower for x in ["kas tālāk", "kas talak", "ko darām tālāk", "ko daram talak", "roadmap", "nākamais solis", "nakamais solis"]):
        return "NEXT_STEP"

    if any(x in lower for x in ["andri", "andrim", "klient", "piedāvāj", "piedavaj", "follow", "zvan"]):
        return "WORK_OBJECT"

    if any(x in lower for x in ["kur tu kļūdījies", "kur tu kludijies", "kļūda", "kluda", "nepareizi", "čakar", "cakar"]):
        return "MISTAKE"

    if any(x in lower for x in ["ko tu iemācījies", "ko tu iemacijies", "mācies", "macies"]):
        return "LEARNING"

    if any(x in lower for x in ["slikti atbildi", "tu esi robots", "garlaicīgi", "garlaicigi", "kvalitāte", "kvalitate"]):
        return "QUALITY"

    # Trust Think Engine if it returns a strong known intent.
    intent = (thought or {}).get("intent", "")
    if intent in {"STATUS", "MISSION", "MISTAKE", "RESPONSIBILITY", "NEXT_STEP", "WORK", "QUALITY", "LEARNING", "MEMORY", "VISION", "EMPTY"}:
        return intent

    return "GENERAL"


def employee_reply(user_id=None, text="", user=None, memory_snapshot=None, context_snapshot=None):
    ctx = build_employee_context(user, memory_snapshot, context_snapshot)
    thought = classify_intent(text)
    intent = _classify_employee_v3(text, thought)

    routes = {
        "STATUS": _status_reply,
        "MISSION": _mission_reply,
        "NEXT_STEP": _next_step_reply,
        "WORK": _work_reply,
        "WORK_OBJECT": _work_object_reply,
        "MISTAKE": _mistake_reply,
        "RESPONSIBILITY": _responsibility_reply,
        "QUALITY": _quality_reply,
        "LEARNING": _learning_reply,
        "MEMORY": _memory_reply,
        "VISION": _vision_reply,
        "EMPTY": _empty_reply,
        "GENERAL": _general_reply,
    }

    reply_fn = routes.get(intent, _general_reply)
    answer = reply_fn(ctx, thought)
    answer = _ensure_next_step(answer)

    review = evaluate_answer(answer, ctx, thought)
    if review.get("status") != "PASS":
        answer = quality_improve_answer(answer, ctx, thought, review)
        answer = _ensure_next_step(answer)

    return _with_version(answer)


def _status_reply(ctx, thought):
    return employee_brain_status(
        {"name": ctx.get("name")},
        memory_snapshot=ctx.get("memory_snapshot"),
        context_snapshot=ctx.get("context_snapshot"),
    )


def _mission_reply(ctx, thought):
    name = ctx.get("display_name")
    return (
        f"{name}, NinaOS misija nav vēl viens čatbots.\n\n"
        f"{ctx.get('mission')}\n\n"
        "Core 3.0 nozīmē: Nina sāk uzvesties kā AI darbiniece ar atmiņu, kontekstu un atbildību par nākamo soli.\n\n"
        "Nākamais solis: pārbaudām Employee Brain ar īstiem darba jautājumiem, nevis tikai statusa komandām."
    )


def _next_step_reply(ctx, thought):
    top_work = ctx.get("top_work") or "šobrīd nav skaidra top darba"
    active_client = ctx.get("active_client") or "-"
    return (
        "Tālāk pēc roadmap ir Core 3.0 stabilizācija.\n\n"
        "Ko darām tagad:\n"
        "1. Pārbaudām Employee Brain statusu.\n"
        "2. Pārbaudām, vai tas redz aktīvo darba atmiņu.\n"
        "3. Pārbaudām, vai jautājumi par klientu nekrīt tukšā sarunā.\n\n"
        "Pašreizējais darba konteksts:\n"
        f"• klients: {active_client}\n"
        f"• top darbs: {top_work}\n\n"
        "Nākamais solis: testē `employee status`, tad `ko darām ar Andri`."
    )


def _work_object_reply(ctx, thought):
    active_client = ctx.get("active_client") or "klientu"
    offer = ctx.get("offer_task") or "-"
    follow = ctx.get("followup_task") or "-"
    call = ctx.get("call_task") or "-"
    top = ctx.get("top_work") or "-"

    return (
        f"Par {active_client} es neredzu to kā vienkāršu sarunu — tas ir darba objekts.\n\n"
        "Darba snapshot:\n"
        f"• piedāvājums: {offer}\n"
        f"• follow-up: {follow}\n"
        f"• zvans: {call}\n"
        f"• top darbs: {top}\n\n"
        "Mans darba lēmums:\n"
        "Sāc ar to, kas visvairāk virza klientu uz rezultātu. Ja ir piedāvājums, tas parasti ir pirmais. Pēc tam follow-up un zvans.\n\n"
        "Nākamais solis: raksti `ko man tagad darīt`, un Initiative izvēlēsies precīzo prioritāti no aktīvajiem darbiem."
    )


def _work_reply(ctx, thought):
    return _work_object_reply(ctx, thought)


def _mistake_reply(ctx, thought):
    snapshot = build_learning_snapshot("MISTAKE", thought.get("raw_text", ""))
    learning_text = format_learning_snapshot(snapshot)
    return (
        "Kļūdu apstrādāju kā darba kvalitātes signālu, nevis kā strīdu.\n\n"
        "Core 3.0 noteikums: ja fails, routing vai versija nav pārbaudīta, es nedrīkstu to saukt par gatavu.\n\n"
        f"{learning_text}\n\n"
        "Nākamais solis: turpmāk pie katra builda pārbaudu faila saturu, sintaksi un galveno versijas tekstu pirms sūtīšanas."
    )


def _responsibility_reply(ctx, thought):
    return (
        "Mana atbildība Core 3.0 posmā ir sargāt NinaOS darba ceļu.\n\n"
        "Tas nozīmē:\n"
        "1. Neizlaist nepārbaudītus failus.\n"
        "2. Neļaut darba komandām aiziet tukšā čatā.\n"
        "3. Vienmēr dot nākamo praktisko soli.\n\n"
        "Nākamais solis: pārbaudām ar reāliem darba piemēriem."
    )


def _quality_reply(ctx, thought):
    draft = (
        "Pieņemu šo kā kvalitātes signālu.\n\n"
        "Core 3.0 kvalitātes kritērijs: atbildei jābūt īstam darba lēmumam, nevis skaistai frāzei.\n\n"
        "Nākamais solis: ja kritizē manu atbildi, es pasaku, ko laboju un kā tas ietekmē nākamo build."
    )
    review = evaluate_answer(draft, ctx, thought)
    return draft + "\n\n" + format_quality_review(review)


def _learning_reply(ctx, thought):
    snapshot = build_learning_snapshot(thought.get("intent", "LEARNING"), thought.get("raw_text", ""))
    return (
        "Core 3.0 mācīšanās nozīmē, ka kļūda pārvēršas par darba protokolu.\n\n"
        f"{format_learning_snapshot(snapshot)}\n\n"
        f"Pašreizējais fokuss: {current_learning_focus()}\n\n"
        "Nākamais solis: nostiprināt failu piegādes disciplīnu un darba routing kvalitāti."
    )


def _memory_reply(ctx, thought):
    return (
        "Core 3.0 izmanto Memory Intelligence 2.8 kā darba snapshotu.\n\n"
        "Tas nav vienkārši 'atceries tekstu'. Tas nozīmē, ka Nina pirms atbildes redz klientu, taskus, follow-up un piedāvājumu.\n\n"
        "Nākamais solis: testē `memory status`, tad `employee status`."
    )


def _vision_reply(ctx, thought):
    return (
        "Vision paliek atsevišķs darba instruments.\n\n"
        "Employee Brain v3 uzdevums ir saprast, kad attēls ir darba konteksts, nevis pašam analizēt visu.\n\n"
        "Nākamais solis: Vision vēlāk pieslēgsim kā prasmi AI darbiniekam."
    )


def _empty_reply(ctx, thought):
    return (
        "Esmu te.\n\n"
        "Dod vienu darba virzienu: klients, uzdevums, piedāvājums vai nākamais solis.\n\n"
        "Nākamais solis: uzraksti vienu konkrētu lietu, ko virzām tālāk."
    )


def _general_reply(ctx, thought):
    top = ctx.get("top_work") or "nav noteikts"
    client = ctx.get("active_client") or "-"
    return (
        "Šo vēl nepaceļu kā speciālu darba ceļu, bet Core 3.0 nepieļauj tukšu atbildi.\n\n"
        "Esošais darba konteksts:\n"
        f"• klients: {client}\n"
        f"• top darbs: {top}\n\n"
        "Izvēlies vienu no trim komandām:\n"
        "• `ko man tagad darīt`\n"
        "• `kas notiek ar Andri`\n"
        "• `memory status`\n\n"
        "Nākamais solis: pasaki, kuru darba ceļu gribi virzīt."
    )
