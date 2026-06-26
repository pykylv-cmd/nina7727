
"""
assistant.py — V13.0.1

Šeit dzīvo Ninas personība, sākuma teksts, "mana diena", "atceries" un invite teksti.
Mērķis: iznest lietotāja pieredzes tekstus ārpus lielā app.py, neskarot Stripe/Premium kodu.
"""

NINA_POSITIONING = "Nina – tava personīgā AI asistente, kas atceras, plāno un palīdz katru dienu."


def build_start_answer(version="V13.0.1"):
    return (
        "👋 Sveiks! Es esmu Nina.\n\n"
        f"{NINA_POSITIONING}.\n\n"
        "Es varu tev palīdzēt:\n"
        "🧠 atcerēties svarīgas lietas\n"
        "📅 sakārtot dienu\n"
        "⏰ atgādināt par svarīgiem notikumiem\n"
        "💬 būt tavs ikdienas AI palīgs\n\n"
        "Pamēģini uzreiz:\n"
        "mana diena\n"
        "atceries\n"
        "premium\n\n"
        "Ja gribi uzaicināt draugu:\n"
        "invite\n\n"
        f"Versija: {version}"
    )


def build_daily_habit_answer(name="", plan="Free", reminders=0, backups=0, is_premium=False, version="V13.0.1"):
    greeting = f"👋 Sveiks, {name}!" if name else "👋 Sveiks!"
    premium_line = "💎 Premium aktīvs" if is_premium else "🔓 Free režīms"

    if reminders == 0:
        reminder_text = "Šobrīd tev nav aktīvu atgādinājumu. Varbūt šodien ir laba diena ieplānot kaut ko svarīgu?"
    else:
        reminder_text = f"Tev ir {reminders} aktīvi atgādinājumi. Es palīdzēšu nepalaist garām svarīgo."

    if backups == 0:
        memory_text = "Es vēl neatceros nevienu svarīgu lietu, ko esi man uzticējis."
    else:
        memory_text = f"Es jau glabāju {backups} svarīgas lietas, ko esi man uzticējis."

    return (
        f"{greeting}\n\n"
        "Šī ir tava diena ar Ninu.\n\n"
        f"{reminder_text}\n"
        f"{memory_text}\n\n"
        f"{premium_line}\n"
        f"Plāns: {plan}\n\n"
        "Ar ko sākam?\n"
        "• pastāsti, kas šodien jāpaveic;\n"
        "• uzraksti: atceries;\n"
        "• vai palūdz man palīdzēt sakārtot dienu.\n\n"
        "Mans mērķis ir vienkāršs: palīdzēt tev neaizmirst svarīgo un virzīties uz priekšu katru dienu.\n\n"
        f"Versija: {version}"
    )


def build_remember_prompt_answer(version="V13.0.1"):
    return (
        "🧠 Ko vēlies, lai es atceros?\n\n"
        "Vari rakstīt vienkārši, piemēram:\n"
        "Atceries, ka pirmdien 10:00 jāzvana klientam.\n"
        "Atceries, ka man patīk melna BMW krāsa.\n"
        "Atceries, ka šonedēļ jāizdara projekta plāns.\n\n"
        "Ja tā ir svarīga doma, uzdevums vai fakts — uztici to man.\n\n"
        f"Versija: {version}"
    )


def build_invite_answer(link, version="V13.0.1"):
    return (
        "🔗 Uzaicini cilvēku pamēģināt Ninu\n\n"
        "Nosūti šo tekstu:\n\n"
        "🤖 Pamēģini Ninu!\n\n"
        "Nina ir personīgā AI asistente, kas atceras, plāno un palīdz katru dienu.\n\n"
        "Viņa var palīdzēt:\n"
        "• atcerēties svarīgas lietas;\n"
        "• sakārtot dienu;\n"
        "• veidot atgādinājumus;\n"
        "• būt tavs ikdienas AI palīgs.\n\n"
        "Sākt var bez maksas:\n"
        f"{link}\n\n"
        f"Versija: {version}"
    )
