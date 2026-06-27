"""
daily.py — V14.0.1

Daily Assistant teksti atsevišķā modulī.
Šeit nav Stripe, Premium, webhook vai datubāzes savienojuma.
Tas nozīmē: varam mainīt Ninas ikdienas tekstus, neriskējot ar maksājumiem.
"""


def build_daily_answer(name="", plan="Free", is_premium=False, goals=None, memories=None, reminders=0, version="V14.0.1"):
    goals = goals or []
    memories = memories or []

    greeting = f"👋 Sveiks, {name}!" if name else "👋 Sveiks!"
    premium_line = "💎 Premium aktīvs" if is_premium else "🔓 Free režīms"

    if goals:
        goal_lines = ["🎯 Šodienas galvenais mērķis:"]
        for goal in goals:
            goal_lines.append(f"• {goal}")
        goals_text = "\n".join(goal_lines)
    else:
        goals_text = "🎯 Šodien vēl nav pierakstīts galvenais mērķis."

    if memories:
        memory_lines = ["🧠 Es atceros:"]
        for memory in memories:
            memory_lines.append(f"• {memory}")
        memories_text = "\n".join(memory_lines)
    else:
        memories_text = "🧠 Es vēl neatceros nevienu svarīgu lietu, ko esi man uzticējis."

    reminder_text = "⏰ Šobrīd tev nav aktīvu atgādinājumu." if reminders == 0 else f"⏰ Tev ir {reminders} aktīvi atgādinājumi."

    return (
        f"{greeting}\n\n"
        "Šī ir tava diena ar Ninu. 🌅\n\n"
        f"{goals_text}\n\n"
        f"{memories_text}\n\n"
        f"{reminder_text}\n\n"
        f"{premium_line}\n"
        f"Plāns: {plan}\n\n"
        "Ko darām tālāk?\n"
        "• mērķis: tavs šodienas mērķis\n"
        "• atceries, ka...\n"
        "• vai vienkārši pastāsti, kas šodien jāizdara.\n\n"
        f"Versija: {version}"
    )


def build_morning_answer(name="", version="V14.0.1"):
    greeting = f"🌅 Labrīt, {name}!" if name else "🌅 Labrīt!"
    return (
        f"{greeting}\n\n"
        "Sākam dienu mierīgi un gudri.\n\n"
        "Pastāsti man vienu lietu:\n"
        "Kas šodien ir pats svarīgākais?\n\n"
        "Es varu palīdzēt:\n"
        "• saplānot dienu;\n"
        "• atcerēties svarīgo;\n"
        "• izveidot atgādinājumu;\n"
        "• sakārtot domas, ja galvā ir haoss.\n\n"
        "Raksti, piemēram:\n"
        "Šodien man jāizdara...\n\n"
        f"Versija: {version}"
    )


def build_evening_answer(version="V14.0.1"):
    return (
        "🌙 Vakara pārskats ar Ninu\n\n"
        "Pirms diena beidzas, vari man īsi uzrakstīt:\n"
        "1. Kas šodien izdevās?\n"
        "2. Kas palika neizdarīts?\n"
        "3. Ko vajag atcerēties rītdienai?\n\n"
        "Es palīdzēšu sakārtot domas un saglabāt svarīgāko.\n\n"
        "Raksti, piemēram:\n"
        "Šodien izdevās..., rīt jāatceras...\n\n"
        f"Versija: {version}"
    )


def build_goal_prompt_answer(version="V14.0.1"):
    return (
        "🎯 Šodienas mērķis\n\n"
        "Uzraksti vienu galveno lietu, ko šodien gribi paveikt.\n\n"
        "Piemēram:\n"
        "mērķis: piezvanīt klientam un pabeigt piedāvājumu\n\n"
        "Kad mērķis ir skaidrs, diena kļūst vieglāk vadāma.\n\n"
        f"Versija: {version}"
    )
