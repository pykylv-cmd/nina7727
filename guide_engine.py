"""
guide_engine.py
NinaOS Guide Engine — V1.0

Mērķis:
- iemācīt lietotājam, kā lietot Ninu;
- dot skaidru palīdzības / spēju karti;
- pievienot konteksta hintus pēc svarīgām atbildēm;
- padarīt Ninu saprotamu klientiem bez ārējas instrukcijas.

Šis modulis nemaina datubāzi.
Tas tikai ģenerē tekstus un hintus.
"""

GUIDE_ENGINE_VERSION = "Guide Engine V1.0"


def _clean(text):
    return (text or "").strip()


def _lower(text):
    return _clean(text).lower()


def is_guide_command(text):
    lower = _lower(text)
    return lower in [
        "palīdzība",
        "palidziba",
        "help",
        "ko tu māki",
        "ko tu maki",
        "ko tu vari",
        "ko vari",
        "kā tevi lietot",
        "ka tevi lietot",
        "nina help",
        "guide",
        "pamācība",
        "pamaciba",
    ]


def is_start_command(text):
    lower = _lower(text)
    return lower in [
        "/start",
        "start",
        "sākt",
        "sakt",
        "sākam",
        "sakam",
    ]


def guide_welcome_answer(user_name=""):
    name = _clean(user_name)
    greeting = f"Sveiks, {name}." if name else "Sveiks."

    return (
        f"{greeting} Es esmu Nina — tavs AI darba asistents. 😊\n\n"
        "Es varu palīdzēt tev ne tikai čatot, bet sakārtot reālus darbus:\n\n"
        "1. Uzdevumi\n"
        "- “rīt jānosūta piedāvājums Andrim”\n"
        "- “mani uzdevumi”\n\n"
        "2. Klienti / CRM\n"
        "- “kas notiek ar Andri”\n"
        "- “pipeline”\n"
        "- “kam jānosūta piedāvājums”\n\n"
        "3. Atmiņa\n"
        "- “atceries, ka man patīk BMW”\n"
        "- “ko tu par mani zini”\n\n"
        "4. Dienas plānošana\n"
        "- “sakārto manu dienu”\n"
        "- “ko man šodien darīt”\n\n"
        "Sāc vienkārši: uzraksti vienu īstu darbu, piemēram:\n"
        "rīt jānosūta piedāvājums Andrim\n\n"
        f"Versija: {GUIDE_ENGINE_VERSION}"
    )


def guide_capabilities_answer():
    return (
        "🧭 Ko Nina māk\n\n"
        "Ninu vari lietot dabiskā valodā. Nav obligāti jāzina komandas.\n\n"
        "📋 Uzdevumi\n"
        "- “rīt jānosūta piedāvājums Andrim”\n"
        "- “piektdien jāpajautā Andrim par atbildi”\n"
        "- “mani uzdevumi”\n\n"
        "👥 Klienti / CRM\n"
        "- “kas notiek ar Andri”\n"
        "- “pipeline”\n"
        "- “mani klienti”\n"
        "- “kam jānosūta piedāvājums”\n"
        "- “kam jātaisa follow-up”\n"
        "- “kas iestrēdzis”\n\n"
        "🧠 Atmiņa\n"
        "- “atceries, ka man patīk BMW”\n"
        "- “ko tu par mani zini”\n\n"
        "🗓️ Diena\n"
        "- “sakārto manu dienu”\n"
        "- “ko man šodien darīt”\n\n"
        "🔧 Sistēmas pārbaude\n"
        "- “persistence health”\n"
        "- “sales pipeline”\n"
        "- “client work”\n\n"
        "Labs sākums:\n"
        "uzraksti vienu īstu klienta darbu, un es to sakārtošu.\n\n"
        f"Versija: {GUIDE_ENGINE_VERSION}"
    )


def guide_status_answer():
    return (
        "🧭 Guide Engine V1.0 ir aktīvs. ✅\n\n"
        "Uzdevums:\n"
        "- parādīt, ko Nina māk;\n"
        "- palīdzēt jaunam lietotājam sākt;\n"
        "- dot nākamā soļa hintus pēc svarīgām atbildēm.\n\n"
        "Komandas:\n"
        "- palīdzība\n"
        "- ko tu māki\n"
        "- kā tevi lietot\n"
        "- /start\n\n"
        f"Versija: {GUIDE_ENGINE_VERSION}"
    )


def next_hint_for_context(context):
    """
    Dod īsu, neuzbāzīgu hintu pēc svarīgām Nina atbildēm.
    context piemēri:
    - task_list
    - client_view
    - pipeline
    - active_clients
    - offer_to_send
    - followup_clients
    - stuck
    - task_saved
    """
    ctx = _clean(context).lower()

    hints = {
        "task_list": (
            "\n\nKo vari darīt tālāk:\n"
            "- “sakārto manu dienu”\n"
            "- “kas notiek ar Andri”\n"
            "- “pipeline”"
        ),
        "client_view": (
            "\n\nKo vari darīt tālāk:\n"
            "- “pipeline”\n"
            "- “kam jānosūta piedāvājums”\n"
            "- iedod jaunu darbu, piemēram: “otrdien jāpiezvana Andrim”"
        ),
        "pipeline": (
            "\n\nĀtrie CRM skati:\n"
            "- “mani klienti”\n"
            "- “kam jānosūta piedāvājums”\n"
            "- “kas iestrēdzis”"
        ),
        "active_clients": (
            "\n\nVari prasīt konkrētu klientu:\n"
            "- “kas notiek ar Andri”\n"
            "- vai “pipeline”"
        ),
        "offer_to_send": (
            "\n\nNākamais solis:\n"
            "- atver klienta skatu: “kas notiek ar Andri”\n"
            "- pēc nosūtīšanas pieraksti: “piedāvājums Andrim nosūtīts”"
        ),
        "followup_clients": (
            "\n\nJa klients jāatgādina:\n"
            "- uzraksti follow-up darbu, piemēram: “piektdien jāpajautā Andrim par atbildi”"
        ),
        "stuck": (
            "\n\nJa gribi sakārtot pārdošanu:\n"
            "- “pipeline”\n"
            "- “mani klienti”"
        ),
        "task_saved": (
            "\n\nVari pārbaudīt:\n"
            "- “mani uzdevumi”\n"
            "- “sakārto manu dienu”"
        ),
    }

    return hints.get(ctx, "")


def append_hint(answer, context):
    """
    Pievieno hintu tikai tad, ja tas vēl nav pievienots.
    """
    answer = _clean(answer)
    hint = next_hint_for_context(context)

    if not answer or not hint:
        return answer

    if "Ko vari darīt tālāk:" in answer or "Ātrie CRM skati:" in answer:
        return answer

    return answer + hint


def guide_short_tip():
    return (
        "Padoms: vari rakstīt dabiski, piemēram "
        "“rīt jānosūta piedāvājums Andrim”, nevis meklēt pareizo komandu."
    )
