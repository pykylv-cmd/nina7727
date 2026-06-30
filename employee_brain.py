"""
employee_brain.py
Nina Core Evolution 2.4 — Employee Brain + Think Engine + Learning Engine

Šajā versijā Employee Brain vairs nemēģina pats minēt visu ar haotiskiem if.
Vispirms Think Engine nosaka nodomu, tikai tad Employee Brain veido atbildi.
"""

CORE_VERSION = "Core Evolution 2.4"

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


def _clean(value):
    return (value or "").strip()


def _split_items(value):
    value = _clean(value)
    if not value:
        return []
    import re
    return [p.strip() for p in re.split(r"[;\n|]+", value) if p.strip()]


def build_employee_context(user=None):
    user = user or {}
    name = _clean(user.get("name"))
    profession = _clean(user.get("profession"))
    projects = _clean(user.get("projects"))
    facts = _clean(user.get("facts"))
    hobbies = _clean(user.get("hobbies"))

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
            "NinaOS mērķis ir izveidot pasaulē labāko AI darbinieku platformu, "
            "kur cilvēki, uzņēmumi, AI darbinieki un nākotnē arī roboti sadarbojas vienotā sistēmā. "
            "Mēs neaizstājam cilvēkus — mēs palīdzam viņiem būt tehnoloģiju virsotnē."
        ),
        "current_work": "Core Evolution 2.4 — Learning Engine",
        "current_priority": (
            "iemācīt Ninai konkrēti fiksēt, ko viņa iemācījās, "
            "ko nedrīkst atkārtot un kā mainās nākamā rīcība"
        ),
        "next_real_step": (
            "pārbaudīt Learning Engine uz MISTAKE, QUALITY un NEXT_STEP; "
            "pēc tam sākt Core 2.5 Quality Engine"
        ),
    }


def employee_brain_status(user=None):
    ctx = build_employee_context(user)
    name = ctx.get("display_name")
    return _with_version(
        f"🧠 Nina Core Evolution 2.4 ir aktīvs. ✅\n\n"
        f"{name}, tagad mans fokuss ir Learning Engine — es ne tikai atzīstu kļūdu, bet pasaku, ko no tās mācos.\n\n"
        "Jaunā secība:\n"
        "1. Lietotājs uzraksta ziņu\n"
        "2. Think Engine nosaka nodomu\n"
        "3. Employee Brain izvēlas pareizo darba ceļu\n"
        "4. Atbilde tiek pārbaudīta pret Ninas darbinieces standartu\n\n"
        "Think Engine kategorijas:\n"
        "IDENTITY, MISSION, WORK, MEMORY, QUALITY, MISTAKE, RESPONSIBILITY, NEXT_STEP, LEARNING, VISION, GENERAL.\n\n"
        f"Pašreizējā prioritāte: {ctx.get('current_priority')}\n\n"
        "Learning princips: kļūda nav kauns. Kļūda ir darba kvalitātes signāls, no kura man jāizdara praktiska izmaiņa nākamajā rīcībā."
    )


def _with_version(answer):
    answer = _clean(answer)
    if f"Versija: {CORE_VERSION}" not in answer:
        answer += f"\n\nVersija: {CORE_VERSION}"
    return answer


def _ensure_next_step(answer):
    lower = answer.lower()
    if "nākamais" not in lower and "solis" not in lower:
        answer = answer.rstrip() + "\n\nNākamais solis: pasaki vienu konkrētu lietu, ko virzām tālāk."
    return answer


def employee_reply(user_id=None, text="", user=None):
    ctx = build_employee_context(user)
    thought = classify_intent(text)
    intent = thought.get("intent", "GENERAL")

    routes = {
        "STATUS": _status_reply,
        "IDENTITY": _identity_reply,
        "MISSION": _mission_reply,
        "MISTAKE": _mistake_reply,
        "RESPONSIBILITY": _responsibility_reply,
        "NEXT_STEP": _next_step_reply,
        "WORK": _work_reply,
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
    return _with_version(answer)


def _status_reply(ctx, thought):
    return employee_brain_status({"name": ctx.get("name")})


def _identity_reply(ctx, thought):
    name = ctx.get("name")
    if name:
        return (
            f"Jā, {name}. Es zinu tavu vārdu. 🙂\n\n"
            "Think Engine šo atpazina kā IDENTITY jautājumu, tāpēc man nebija jāmin vai jāiet uz vispārīgu sarunu.\n\n"
            f"Pašreizējais darbs: {ctx.get('current_work')}.\n\n"
            "Nākamais solis: pārbaudām, vai identitāte tiek izmantota arī darba sarunās, ne tikai tiešā jautājumā."
        )
    return (
        "Es vēl droši nezinu tavu vārdu.\n\n"
        "Uzraksti, piemēram: mani sauc Jānis. Tad tas jāglabā kā identitāte, nevis parasta atmiņa.\n\n"
        "Nākamais solis: pasaki savu vārdu, un es to turpmāk izmantošu sarunā."
    )


def _mission_reply(ctx, thought):
    name = ctx.get("display_name")
    return (
        f"{name}, NinaOS misija nav uztaisīt vēl vienu čatbotu.\n\n"
        f"{ctx.get('mission')}\n\n"
        "Nina ir pirmais AI darbinieks un kvalitātes paraugs. Ja Nina kļūs izcila, pārējie AI darbinieki varēs mantot šo domāšanas kodolu.\n\n"
        f"Pašreizējais darbs: {ctx.get('current_work')}.\n\n"
        "Nākamais solis: pārbaudām Think Engine, lai katra svarīga ziņa nonāk pareizajā darba ceļā, nevis vispārīgā atbildē."
    )


def _mistake_reply(ctx, thought):
    name = ctx.get("display_name")
    snapshot = build_learning_snapshot("MISTAKE", thought.get("raw_text", ""))
    learning_text = format_learning_snapshot(snapshot)
    return (
        f"{name}, šeit es atzīstu kļūdu konkrēti, nevis vispārīgi.\n\n"
        "Kļūda: iepriekš es dažas frāzes apstrādāju ar nepareizu ceļu — jautājums par kļūdu aizgāja uz vispārīgu atbildi.\n\n"
        "Cēlonis: Employee Brain mēģināja pats minēt nodomu, nevis balstījās uz atsevišķu Think Engine.\n\n"
        f"{learning_text}\n\n"
        "Nākamais solis: testē arī `ko tu iemācījies?`, lai redzam, vai Learning Engine atbild ar mācīšanās protokolu."
    )

def _responsibility_reply(ctx, thought):
    name = ctx.get("display_name")
    return (
        f"{name}, mans uzdevums šobrīd ir skaidrs.\n\n"
        "Es uzņemos atbildību par Core Evolution kvalitāti: lai Nina kļūst par gudru AI darbinieci, nevis vēl vienu čatbotu ar daudz funkcijām.\n\n"
        "Ko es uzņemos praktiski:\n"
        "1. Sekot, lai katra nākamā izmaiņa tuvina NinaOS misijai.\n"
        "2. Brīdināt, ja sākam iet haotiski vai būvēt liekas funkcijas.\n"
        "3. Atzīt kļūdas un pārlabot uzvedību, nevis aizbildināties.\n"
        "4. Vienmēr dot skaidru nākamo soli.\n\n"
        "Nākamais solis: testē mani ar `kur tu kļūdījies?`, lai pārbaudām, vai atbildība un kļūdu analīze tagad ir atdalītas."
    )


def _next_step_reply(ctx, thought):
    name = ctx.get("display_name")
    return (
        f"{name}, nākamais pareizais solis tagad ir Core Evolution 2.4 pārbaude.\n\n"
        "Think Engine jau strādā. Tagad pārbaudām, vai Learning Engine māca Ninu ne tikai atzīt kļūdu, bet arī mainīt nākamo rīcību.\n\n"
        "Šodienas tests:\n"
        "1. `kur tu kļūdījies?` → MISTAKE + learning snapshot\n"
        "2. `ko tu iemācījies?` → LEARNING\n"
        "3. `tu atbildi kā robots` → QUALITY + mācīšanās virziens\n"
        "4. `kas tālāk?` → NEXT_STEP bez vecu soļu atkārtošanas\n\n"
        "Nākamais solis: testēt Learning Engine; pēc tam sākt Core 2.5 Quality Engine, kas vērtēs atbildes pirms nosūtīšanas."
    )

def _work_reply(ctx, thought):
    name = ctx.get("display_name")
    return (
        f"{name}, uzdevumu pieņemu kā AI darbiniece.\n\n"
        "Es to neuztveru kā parastu sarunu. Mans darbs ir virzīt NinaOS uz mērķi, nevis skaitīt idejas.\n\n"
        f"Pašreizējais darbs: {ctx.get('current_work')}.\n"
        f"Pašreizējā prioritāte: {ctx.get('current_priority')}.\n\n"
        "Ko darām tagad:\n"
        "1. Nostiprinām Think Engine.\n"
        "2. Pēc tam būvējam Learning Engine.\n"
        "3. Tikai pēc tam ejam uz darba prasmēm: e-pasti, dokumenti, balss, zvani.\n\n"
        "Nākamais solis: pārbaudīt, vai darba pieprasījumos es dodu ne tikai plānu, bet arī ko mācos un kā uzņemos atbildību."
    )


def _quality_reply(ctx, thought):
    name = ctx.get("display_name")
    return (
        f"{name}, pieņemu šo kā kvalitātes signālu.\n\n"
        "Ja es atbildu robotiski vai garlaicīgi, tā nav tava problēma — tā ir mana darba kvalitātes problēma.\n\n"
        "Core 2.3 uzdevums ir panākt, lai šāda atsauksme nonāk QUALITY ceļā, nevis tiek sajaukta ar tavu emocionālo stāvokli.\n\n"
        "Nākamais solis: pēc Think Engine pārbaudes būvēsim Quality Engine, kas vērtēs atbildi pirms nosūtīšanas."
    )


def _learning_reply(ctx, thought):
    name = ctx.get("display_name")
    snapshot = build_learning_snapshot(thought.get("intent", "LEARNING"), thought.get("raw_text", ""))
    learning_text = format_learning_snapshot(snapshot)
    return (
        f"{name}, Core 2.4 nozīmē, ka es vairs tikai nesaku 'sapratu'.\n\n"
        "Man jāpasaka, ko tieši iemācījos un kā tas maina manu nākamo rīcību.\n\n"
        f"{learning_text}\n\n"
        f"Pašreizējais fokuss: {current_learning_focus()}\n\n"
        "Nākamais solis: pārbaudīt Learning Engine uz kļūdu, kvalitātes komentāru un nākamā soļa jautājumu."
    )

def _memory_reply(ctx, thought):
    name = ctx.get("display_name")
    return (
        f"{name}, šo Think Engine atpazina kā MEMORY tēmu.\n\n"
        "Pagaidām Core 2.3 vēl tikai maršrutē nodomus. Pilnu atmiņas kvalitātes pārvaldību taisīsim atsevišķi, lai Nina neglabā visu pēc kārtas.\n\n"
        "Nākamais solis: pēc Think Engine nostiprināšanas būvēsim gudrāku Memory Filter."
    )


def _vision_reply(ctx, thought):
    name = ctx.get("display_name")
    return (
        f"{name}, šo Think Engine atpazina kā VISION tēmu.\n\n"
        "Vision vēl paliek esošajā pārbaudītajā ceļā. Core 2.3 uzdevums nav analizēt bildes, bet saprast, ka ziņa prasa vizuālu analīzi.\n\n"
        "Nākamais solis: pēc Core nostiprināšanas Vision Pro kļūs par atsevišķu darba prasmi."
    )


def _empty_reply(ctx, thought):
    name = ctx.get("display_name")
    return (
        f"{name}, esmu te.\n\n"
        "Uzraksti vienu konkrētu lietu, ko virzām uz priekšu.\n\n"
        "Nākamais solis: izvēlamies darbu, nevis pļāpājam tukšumā."
    )


def _general_reply(ctx, thought):
    name = ctx.get("display_name")
    return (
        f"{name}, sapratu.\n\n"
        "Think Engine šo vēl neklasificēja kā konkrētu darba ceļu, tāpēc es neatbildēšu pārlieku gudri bez pamata.\n\n"
        "Lai virzāmies precīzi, pasaki, vai tas ir uzdevums, jautājums, ideja, kritika vai nākamais solis.\n\n"
        "Nākamais solis: dod vienu skaidru virzienu, un es to novirzīšu pareizajā Nina Core ceļā."
    )
