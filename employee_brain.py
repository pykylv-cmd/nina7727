"""
employee_brain.py
Nina Core Evolution 2.2.1 — Responsibility Brain

Ninas domāšanas centrs.
Mērķis: Nina nav čatbots. Nina ir AI darbiniece, kas saprot cilvēku,
atceras virzienu, dod nākamo soli un uzņemas darba kvalitāti.
"""

CORE_VERSION = "Core Evolution 2.2.1"


def _clean(value):
    return (value or "").strip()


def _split_items(value):
    value = _clean(value)
    if not value:
        return []
    import re
    return [p.strip() for p in re.split(r"[;\n|]+", value) if p.strip()]


def employee_brain_status(user=None):
    ctx = build_employee_context(user)
    name = ctx.get("display_name")
    return (
        f"🧠 Nina Core Evolution 2.2 ir aktīvs. ✅\n\n"
        f"{name}, tagad mans fokuss ir Responsibility Brain — es ne tikai atbildu, bet uzņemos darba kvalitāti.\n\n"
        "Domāšanas secība:\n"
        "1. Kas ir cilvēks?\n"
        "2. Ko es par viņu zinu?\n"
        "3. Pie kā mēs šobrīd strādājam?\n"
        "4. Kas ir īstais mērķis?\n"
        "5. Kāds ir praktiskais nākamais solis?\n"
        "6. Vai atbilde ir darbinieces līmenī?\n"
        "7. Vai es uzņēmos atbildību par nākamo soli?\n\n"
        f"Pašreizējā prioritāte: {ctx.get('current_priority')}\n\n"
        "Responsibility Brain princips: ja es redzu kļūdu, es to pasaku; ja uzdevums ir mans, es to uzņemos; ja virziens kļūst haotisks, es atgriežu mūs pie mērķa.\n\n"
        f"Versija: {CORE_VERSION}"
    )


def detect_employee_intent(text):
    lower = _clean(text).lower()
    if not lower:
        return "empty"

    if lower in [
        "core status", "employee status", "nina core", "core 2.0", "core 2.1", "core 2.2",
        "core evolution", "employee brain", "core"
    ]:
        return "status"

    if any(x in lower for x in [
        "ko šodien darām", "ko sodien daram", "kas tālāk", "kas talak",
        "nākamais solis", "nakamais solis", "ko iesaki", "ko tu iesaki",
        "turpinam", "turpinām"
    ]):
        return "next_step"

    if any(x in lower for x in [
        "ninaos misija", "ninaos mērķis", "ninaos merkis",
        "kāda ir misija", "kada ir misija", "mūsu misija", "musu misija",
        "projekta misija", "kas ir ninaos"
    ]):
        return "mission"

    if any(x in lower for x in [
        "kur tu kļūdījies", "kur tu kludijies", "kā tu kļūdījies", "ka tu kludijies",
        "ko tu izdarīji nepareizi", "ko tu izdariji nepareizi", "kāda bija kļūda", "kada bija kluda"
    ]):
        return "mistake_review"

    if any(x in lower for x in [
        "tu esi robots", "kā robots", "ka robots", "garlaicīgi", "garlaicigi",
        "nepareizi", "slikti atbildi", "tev jāmācās", "tev jamacas",
        "nav labi", "šādi nedrīkst", "sadi nedrikst", "tu kļūdies", "tu kludies"
    ]):
        return "quality_feedback"

    if any(x in lower for x in [
        "palīdzi", "palidzi", "vajag uztaisīt", "vajag uztaisit",
        "vajag pabeigt", "strādājam", "stradajam", "būvēt ninaos",
        "buvet ninaos", "taisam", "sākam", "sakam"
    ]):
        return "work_request"

    if any(x in lower for x in [
        "kā mani sauc", "ka mani sauc", "zini manu vārdu", "zini manu vardu",
        "mans vārds", "mans vards"
    ]):
        return "identity_question"

    if any(x in lower for x in [
        "uzņemies", "uznemies", "paņem atbildību", "panem atbildibu",
        "ko tu uzņemies", "ko tu uznemies", "kas ir tavs uzdevums",
        "atbildība", "atbildiba"
    ]):
        return "responsibility"

    return "general"


def build_employee_context(user=None):
    user = user or {}
    name = _clean(user.get("name"))
    profession = _clean(user.get("profession"))
    projects = _clean(user.get("projects"))
    facts = _clean(user.get("facts"))
    hobbies = _clean(user.get("hobbies"))

    project_items = _split_items(projects)
    fact_items = _split_items(facts)

    current_work = "Core Evolution 2.2.1 — Responsibility Brain"
    current_priority = (
        "nostiprināt Ninas domāšanas kodolu, lai viņa runā kā gudra AI darbiniece, "
        "izmanto identitāti un zina aktuālo darba virzienu"
    )

    return {
        "name": name,
        "display_name": name or "kolēģi",
        "profession": profession,
        "projects": projects,
        "project_items": project_items,
        "facts": facts,
        "fact_items": fact_items,
        "hobbies": hobbies,
        "mission": (
            "NinaOS mērķis ir izveidot pasaulē labāko AI darbinieku platformu, "
            "kur cilvēki, uzņēmumi, AI darbinieki un nākotnē arī roboti sadarbojas vienotā sistēmā. "
            "Mēs neaizstājam cilvēkus — mēs palīdzam viņiem būt tehnoloģiju virsotnē."
        ),
        "current_work": current_work,
        "current_priority": current_priority,
        "next_real_step": (
            "pabeigt Core 2.2.1 kļūdu atzīšanas pārbaudi; "
            "pēc tam sākt Core 2.3 Learning Brain, lai Nina mācās no atsauksmēm"
        )
    }


def quality_check(answer):
    if not answer:
        return False
    lower = answer.lower()
    weak_phrases = [
        "pastāsti vairāk", "pastasti vairak", "interesants jautājums", "interesants jautajums",
        "esmu tikai ai", "kā ai valodas modelis", "ka ai valodas modelis"
    ]
    if any(p in lower for p in weak_phrases):
        return False
    if "nākamais" not in lower and "solis" not in lower and "darām" not in lower and "daram" not in lower:
        return False
    return True


def improve_answer(answer):
    if not answer:
        answer = "Es sapratu. Tagad jāizvēlas praktisks nākamais solis."
    lower = answer.lower()
    if "nākamais" not in lower and "solis" not in lower:
        answer = answer.rstrip() + "\n\nNākamais solis: pasaki vienu konkrētu lietu, ko gribi tagad virzīt uz priekšu."
    return answer


def employee_reply(user_id=None, text="", user=None):
    ctx = build_employee_context(user)
    intent = detect_employee_intent(text)
    name = ctx.get("display_name")

    if intent == "status":
        return employee_brain_status(user)

    if intent == "identity_question":
        if ctx.get("name"):
            answer = (
                f"Jā, {ctx.get('name')}. Es zinu tavu vārdu. 🙂\n\n"
                "Tas man nav jāmin no jauna — tā ir identitāte, un man tā jāizmanto sarunā, kad tas palīdz.\n\n"
                f"Pašreizējais darbs: {ctx.get('current_work')}.\n\n"
                "Nākamais solis: turpinām pārbaudīt, vai es izmantoju identitāti arī sarežģītākās sarunās."
            )
        else:
            answer = (
                "Es vēl droši nezinu tavu vārdu.\n\n"
                "Uzraksti, piemēram: mani sauc Jānis. Tad es to izmantošu kā identitāti, nevis kā parastu atmiņu.\n\n"
                "Nākamais solis: pasaki savu vārdu, un es to turpmāk lietošu sarunā."
            )

    elif intent == "mission":
        answer = (
            f"{name}, NinaOS misija nav uztaisīt vēl vienu čatbotu.\n\n"
            f"{ctx.get('mission')}\n\n"
            "Nina ir pirmais AI darbinieks un kvalitātes paraugs. Ja Nina kļūs izcila, "
            "pārējie AI darbinieki varēs mantot šo domāšanas kodolu.\n\n"
            f"Pašreizējais darbs: {ctx.get('current_work')}.\n\n"
            "Nākamais solis: pabeidzam Core 2.2.1 kļūdu atzīšanas testu, "
            "lai Nina ne tikai uzņemas atbildību, bet arī skaidri pasaka, kur kļūdījās."
        )

    elif intent == "next_step":
        answer = (
            f"{name}, nākamais pareizais solis tagad ir Core Evolution 2.2 pārbaude.\n\n"
            "Mēs jau pieslēdzām employee_brain.py pie app.py, tāpēc vairs neatkārtošu veco soli.\n\n"
            "Šodienas darbs:\n"
            "1. Pārbaudīt, vai es izmantoju tavu vārdu.\n"
            "2. Pārbaudīt, vai es atceros NinaOS misiju.\n"
            "3. Pārbaudīt, vai uz darba pieprasījumu dodu konkrētu virzienu, nevis pļāpāju.\n\n"
            f"Nākamais solis: {ctx.get('next_real_step')}."
        )


    elif intent == "responsibility":
        answer = (
            f"{name}, mans uzdevums šobrīd ir skaidrs.\n\n"
            "Es uzņemos atbildību par Core Evolution kvalitāti: lai Nina kļūst par gudru AI darbinieci, "
            "nevis vēl vienu čatbotu ar daudz funkcijām.\n\n"
            "Ko es uzņemos praktiski:\n"
            "1. Sekot, lai katra nākamā izmaiņa tuvina NinaOS misijai.\n"
            "2. Brīdināt, ja sākam iet haotiski vai būvēt liekas funkcijas.\n"
            "3. Atzīt kļūdas un pārlabot uzvedību, nevis aizbildināties.\n"
            "4. Vienmēr dot skaidru nākamo soli.\n\n"
            "Nākamais solis: testē mani ar frāzi 'kur tu kļūdījies?', lai pārbaudām, vai kļūdu analīze tagad ir atsevišķa no atbildības saraksta."
        )

    elif intent == "quality_feedback":
        answer = (
            f"{name}, pieņemu šo kā kvalitātes signālu un atbildību.\n\n"
            "Ja es atbildu robotiski vai garlaicīgi, tā ir mana kvalitātes kļūda. Es to nefiksēju kā tavu emociju, bet kā uzlabojumu uzdevumu. "
            "Core 2.2 nozīmē: kļūdu atzīt, saprast cēloni un nākamreiz atbildēt labāk.\n\n"
            "Ko es darīšu: pārbaudīšu, vai atbildei ir skaidrs mērķis, konteksts un nākamais solis.\n\n"
            "Nākamais solis: dod man vienu konkrētu sliktas atbildes piemēru, un es to pārvērtīšu par kvalitātes noteikumu."
        )

    elif intent == "work_request":
        answer = (
            f"{name}, uzdevumu pieņemu.\n\n"
            "Es to neuztveru kā parastu sarunu. Mans darbs ir virzīt NinaOS uz mērķi, nevis skaitīt idejas.\n\n"
            f"Pašreizējais darbs: {ctx.get('current_work')}.\n"
            f"Pašreizējā prioritāte: {ctx.get('current_priority')}.\n\n"
            "Ko darām tagad:\n"
            "1. Nostiprinām Core 2.2 Responsibility Brain.\n"
            "2. Pārbaudām, vai es uzņemos darbu un brīdinu par nepareizu virzienu.\n"
            "3. Pēc tam būvējam Core 2.3 Learning Brain.\n\n"
            f"Nākamais solis: {ctx.get('next_real_step')}."
        )

    else:
        answer = (
            f"{name}, sapratu.\n\n"
            "Es šo apstrādāšu kā AI darbiniece: vispirms saprotu nodomu, tad skatos kontekstu, "
            "tad dodu praktisku nākamo soli.\n\n"
            f"Pašreizējais darbs: {ctx.get('current_work')}.\n\n"
            "Nākamais solis: pasaki, vai tas ir uzdevums, ideja, jautājums vai kvalitātes komentārs — un es to virzīšu pareizajā ceļā."
        )

    answer = improve_answer(answer)
    if f"Versija: {CORE_VERSION}" not in answer:
        answer = answer.rstrip() + f"\n\nVersija: {CORE_VERSION}"
    return answer
