
"""
employee_brain.py
Nina Core Evolution 2.0

Ninas jaunais domāšanas centrs.
Mērķis: nevis vienkārši atbildēt, bet domāt kā AI darbiniece.
"""

CORE_VERSION = "Core Evolution 2.0"
"""
employee_brain.py
Nina Core Evolution 2.0

Ninas jaunais domāšanas centrs.
Mērķis: nevis vienkārši atbildēt, bet domāt kā AI darbiniece.
"""

CORE_VERSION = "Core Evolution 2.0"


def employee_brain_status():
    return (
        "🧠 Nina Core Evolution 2.0 ir aktīvs. ✅\n\n"
        "Es vairs nedomāju kā parasts čatbots.\n"
        "Mana domāšanas secība:\n\n"
        "1. Saprast cilvēku\n"
        "2. Atcerēties kontekstu\n"
        "3. Saprast īsto mērķi\n"
        "4. Izvēlēties praktisku nākamo soli\n"
        "5. Pārbaudīt, vai atbilde ir noderīga\n\n"
        "Mērķis: kļūt par AI darbinieci, kurai cilvēks uztic darbu.\n\n"
        f"Versija: {CORE_VERSION}"
    )


def detect_employee_intent(text):
    lower = (text or "").strip().lower()

    if not lower:
        return "empty"

    if lower in ["core status", "employee status", "nina core", "core 2.0", "core evolution"]:
        return "status"

    if any(x in lower for x in [
        "ko šodien darām", "ko sodien daram",
        "kas tālāk", "kas talak",
        "nākamais solis", "nakamais solis",
        "ko iesaki", "ko tu iesaki"
    ]):
        return "next_step"

    if any(x in lower for x in [
        "ninaos mērķis", "ninaos merkis",
        "ninaos misija",
        "kāda ir misija", "kada ir misija",
        "mūsu misija", "musu misija"
    ]):
        return "mission"

    if any(x in lower for x in [
        "tu esi robots", "kā robots", "ka robots",
        "garlaicīgi", "garlaicigi",
        "nepareizi", "slikti atbildi",
        "tev jāmācās", "tev jamacas"
    ]):
        return "quality_feedback"

    if any(x in lower for x in [
        "palīdzi", "palidzi",
        "vajag uztaisīt", "vajag uztaisit",
        "vajag pabeigt",
        "strādājam", "stradajam"
    ]):
        return "work_request"

    return "general"


def build_employee_context(user=None):
    user = user or {}

    name = (user.get("name") or "").strip()
    profession = (user.get("profession") or "").strip()
    projects = (user.get("projects") or "").strip()
    facts = (user.get("facts") or "").strip()

    return {
        "name": name,
        "profession": profession,
        "projects": projects,
        "facts": facts,
        "mission": (
            "NinaOS mērķis ir izveidot pasaulē labāko AI darbinieku platformu, "
            "kur cilvēki, uzņēmumi, AI darbinieki un nākotnē arī roboti sadarbojas "
            "vienotā sistēmā. Nina ir pirmais AI darbinieks un kvalitātes paraugs."
        ),
        "current_priority": (
            "Šobrīd galvenā prioritāte ir Core Evolution 2.0 — padarīt Ninu par "
            "gudru, uzticamu, praktisku AI darbinieci, nevis tikai funkciju botu."
        )
    }


def quality_check(answer):
    if not answer:
        return False

    weak_phrases = [
        "pastāsti vairāk",
        "pastasti vairak",
        "interesants jautājums",
        "interesants jautajums",
        "esmu tikai ai",
    ]

    lower = answer.lower()
    if any(p in lower for p in weak_phrases):
        return False

    if "nākamais" not in lower and "solis" not in lower and "darām" not in lower and "daram" not in lower:
        return False

    return True


def improve_answer(answer):
    if not answer:
        answer = "Es sapratu. Tagad jāizvēlas praktisks nākamais solis."

    if "nākamais" not in answer.lower() and "solis" not in answer.lower():
        answer = answer.rstrip() + "\n\nNākamais solis: pasaki vienu konkrētu lietu, ko gribi tagad virzīt uz priekšu."

    return answer


def employee_reply(user_id=None, text="", user=None):
    context = build_employee_context(user)
    intent = detect_employee_intent(text)
    name = context.get("name") or "kolēģi"

    if intent == "status":
        return employee_brain_status()

    if intent == "mission":
        answer = (
            f"{name}, NinaOS misija nav uztaisīt vēl vienu čatbotu.\n\n"
            "Misija ir izveidot pasaulē labāko AI darbinieku platformu — sistēmu, "
            "kur AI darbinieki palīdz cilvēkiem būt tehnoloģiju virsotnē, nevis aizstāj viņus.\n\n"
            "Nina ir pirmais darbinieks un kvalitātes paraugs. Ja Nina kļūs izcila, "
            "pārējie AI darbinieki varēs mantot šo domāšanas kodolu.\n\n"
            "Nākamais solis: pabeidzam Core Evolution 2.0, lai Nina vispirms kļūst par uzticamu darbinieci."
        )

    elif intent == "next_step":
        answer = (
            f"{name}, nākamais pareizais solis ir nevis jauna funkcija, bet Core Evolution 2.0 nostiprināšana.\n\n"
            "Šodienas darbs:\n"
            "1. Pieslēgt employee_brain.py pie app.py.\n"
            "2. Pārbaudīt, vai Nina atbild caur jauno domāšanas ciklu.\n"
            "3. Testēt: vārds, misija, kritika, nākamais solis, darba pieprasījums.\n\n"
            "Nākamais solis: testējam Telegramā komandas `core 2.0`, `ninaos misija`, `kas tālāk?`."
        )

    elif intent == "quality_feedback":
        answer = (
            f"{name}, pieņemu šo kā kvalitātes signālu, nevis kā parastu sarunu.\n\n"
            "Ja es atbildu robotiski, problēma nav tikai tekstā — problēma ir domāšanas procesā. "
            "Tāpēc Core Evolution 2.0 mērķis ir pirms katras atbildes pārbaudīt: "
            "vai es sapratu cilvēku, izmantoju atmiņu un devu praktisku nākamo soli.\n\n"
            "Nākamais solis: turpinām trenēt Employee Brain, lai katra atbilde kļūst konkrētāka un noderīgāka."
        )

    elif intent == "work_request":
        answer = (
            f"{name}, pieņemu uzdevumu kā AI darbiniece.\n\n"
            "Es neskaitīšu tikai idejas. Es virzīšu darbu tā, lai tas tuvina NinaOS misijai.\n\n"
            "Šobrīd praktiskais fokuss ir viens: Core Evolution 2.0. "
            "Kad tas būs stabils, tikai tad būs jēga likt klāt e-pastus, dokumentus, balsi un zvanus.\n\n"
            "Nākamais solis: pārbaudām, vai employee_brain.py korekti atbild Telegramā."
        )

    else:
        answer = (
            f"{name}, es sapratu.\n\n"
            "Es skatīšos uz šo nevis kā parasts čatbots, bet kā AI darbiniece: "
            "kas tev palīdzēs ātrāk nonākt pie mērķa?\n\n"
            "Nākamais solis: uzraksti, vai šis ir uzdevums, ideja, kritika vai jautājums — un es to apstrādāšu pēc pareizā domāšanas ceļa."
        )

    answer = improve_answer(answer)

    if f"Versija: {CORE_VERSION}" not in answer:
        answer = answer.rstrip() + f"\n\nVersija: {CORE_VERSION}"

    return answer


def employee_brain_status():
    return (
        "🧠 Nina Core Evolution 2.0 ir aktīvs. ✅\n\n"
        "Es vairs nedomāju kā parasts čatbots.\n"
        "Mana domāšanas secība:\n\n"
        "1. Saprast cilvēku\n"
        "2. Atcerēties kontekstu\n"
        "3. Saprast īsto mērķi\n"
        "4. Izvēlēties praktisku nākamo soli\n"
        "5. Pārbaudīt, vai atbilde ir noderīga\n\n"
        "Mērķis: kļūt par AI darbinieci, kurai cilvēks uztic darbu.\n\n"
        f"Versija: {CORE_VERSION}"
    )


def detect_employee_intent(text):
    lower = (text or "").strip().lower()

    if not lower:
        return "empty"

    if lower in ["core status", "employee status", "nina core", "core 2.0", "core evolution"]:
        return "status"

    if any(x in lower for x in [
        "ko šodien darām", "ko sodien daram",
        "kas tālāk", "kas talak",
        "nākamais solis", "nakamais solis",
        "ko iesaki", "ko tu iesaki"
    ]):
        return "next_step"

    if any(x in lower for x in [
        "ninaos mērķis", "ninaos merkis",
        "kāda ir misija", "kada ir misija",
        "mūsu misija", "musu misija"
    ]):
        return "mission"

    if any(x in lower for x in [
        "tu esi robots", "kā robots", "ka robots",
        "garlaicīgi", "garlaicigi",
        "nepareizi", "slikti atbildi",
        "tev jāmācās", "tev jamacas"
    ]):
        return "quality_feedback"

    if any(x in lower for x in [
        "palīdzi", "palidzi",
        "vajag uztaisīt", "vajag uztaisit",
        "vajag pabeigt",
        "strādājam", "stradajam"
    ]):
        return "work_request"

    return "general"


def build_employee_context(user=None):
    user = user or {}

    name = (user.get("name") or "").strip()
    profession = (user.get("profession") or "").strip()
    projects = (user.get("projects") or "").strip()
    facts = (user.get("facts") or "").strip()

    return {
        "name": name,
        "profession": profession,
        "projects": projects,
        "facts": facts,
        "mission": (
            "NinaOS mērķis ir izveidot pasaulē labāko AI darbinieku platformu, "
            "kur cilvēki, uzņēmumi, AI darbinieki un nākotnē arī roboti sadarbojas "
            "vienotā sistēmā. Nina ir pirmais AI darbinieks un kvalitātes paraugs."
        ),
        "current_priority": (
            "Šobrīd galvenā prioritāte ir Core Evolution 2.0 — padarīt Ninu par "
            "gudru, uzticamu, praktisku AI darbinieci, nevis tikai funkciju botu."
        )
    }


def quality_check(answer):
    if not answer:
        return False

    weak_phrases = [
        "pastāsti vairāk",
        "pastasti vairak",
        "interesants jautājums",
        "interesants jautajums",
        "esmu tikai ai",
    ]

    lower = answer.lower()
    if any(p in lower for p in weak_phrases):
        return False

    if "nākamais" not in lower and "solis" not in lower and "darām" not in lower and "daram" not in lower:
        return False

    return True


def improve_answer(answer):
    if not answer:
        answer = "Es sapratu. Tagad jāizvēlas praktisks nākamais solis."

    if "nākamais" not in answer.lower() and "solis" not in answer.lower():
        answer = answer.rstrip() + "\n\nNākamais solis: pasaki vienu konkrētu lietu, ko gribi tagad virzīt uz priekšu."

    return answer


def employee_reply(user_id=None, text="", user=None):
    context = build_employee_context(user)
    intent = detect_employee_intent(text)
    name = context.get("name") or "kolēģi"

    if intent == "status":
        return employee_brain_status()

    if intent == "mission":
        answer = (
            f"{name}, NinaOS misija nav uztaisīt vēl vienu čatbotu.\n\n"
            "Misija ir izveidot pasaulē labāko AI darbinieku platformu — sistēmu, "
            "kur AI darbinieki palīdz cilvēkiem būt tehnoloģiju virsotnē, nevis aizstāj viņus.\n\n"
            "Nina ir pirmais darbinieks un kvalitātes paraugs. Ja Nina kļūs izcila, "
            "pārējie AI darbinieki varēs mantot šo domāšanas kodolu.\n\n"
            "Nākamais solis: pabeidzam Core Evolution 2.0, lai Nina vispirms kļūst par uzticamu darbinieci."
        )

    elif intent == "next_step":
        answer = (
            f"{name}, nākamais pareizais solis ir nevis jauna funkcija, bet Core Evolution 2.0 nostiprināšana.\n\n"
            "Šodienas darbs:\n"
            "1. Pieslēgt employee_brain.py pie app.py.\n"
            "2. Pārbaudīt, vai Nina atbild caur jauno domāšanas ciklu.\n"
            "3. Testēt: vārds, misija, kritika, nākamais solis, darba pieprasījums.\n\n"
            "Nākamais solis: pieslēdzam šo failu galvenajam app.py."
        )

    elif intent == "quality_feedback":
        answer = (
            f"{name}, pieņemu šo kā kvalitātes signālu, nevis kā parastu sarunu.\n\n"
            "Ja es atbildu robotiski, problēma nav tikai tekstā — problēma ir domāšanas procesā. "
            "Tāpēc Core Evolution 2.0 mērķis ir pirms katras atbildes pārbaudīt: "
            "vai es sapratu cilvēku, izmantoju atmiņu un devu praktisku nākamo soli.\n\n"
            "Nākamais solis: turpinām trenēt Employee Brain, lai katra atbilde kļūst konkrētāka un noderīgāka."
        )

    elif intent == "work_request":
        answer = (
            f"{name}, pieņemu uzdevumu kā AI darbiniece.\n\n"
            "Es neskaitīšu tikai idejas. Es virzīšu darbu tā, lai tas tuvina NinaOS misijai.\n\n"
            "Šobrīd praktiskais fokuss ir viens: Core Evolution 2.0. "
            "Kad tas būs stabils, tikai tad būs jēga likt klāt e-pastus, dokumentus, balsi un zvanus.\n\n"
            "Nākamais solis: pieslēdzam employee_brain.py pie app.py un pārbaudām Telegramā."
        )

    else:
        answer = (
            f"{name}, es sapratu.\n\n"
            "Es skatīšos uz šo nevis kā parasts čatbots, bet kā AI darbiniece: "
            "kas tev palīdzēs ātrāk nonākt pie mērķa?\n\n"
            "Nākamais solis: uzraksti, vai šis ir uzdevums, ideja, kritika vai jautājums — un es to apstrādāšu pēc pareizā domāšanas ceļa."
        )

    answer = improve_answer(answer)

    if f"Versija: {CORE_VERSION}" not in answer:
        answer = answer.rstrip() + f"\n\nVersija: {CORE_VERSION}"

    return answer
