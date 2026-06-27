"""
coach.py — V14.5

Ninas ikdienas ieteikumu modulis.
Šeit nav Stripe, Premium, webhook vai datubāzes koda.
"""


def _clean_list(items):
    cleaned = []
    for item in items or []:
        text = str(item or "").strip()
        if text:
            cleaned.append(text)
    return cleaned


def build_daily_coach_tip(goals=None, memories=None, reminders=0):
    goals = _clean_list(goals)
    memories = _clean_list(memories)
    reminders = int(reminders or 0)

    if goals and memories:
        main_goal = goals[0]
        memory = memories[0]
        return (
            "💡 Mans ieteikums šodien:\n\n"
            f"Galvenais virziens šodien ir: {main_goal}\n"
            f"Es arī atceros: {memory}\n\n"
            "Sāc ar vienu mazu soli pie galvenā mērķa. Pēc tam pārbaudi, vai saglabātā lieta nav jāieplāno konkrētā laikā."
        )

    if goals:
        main_goal = goals[0]
        return (
            "💡 Mans ieteikums šodien:\n\n"
            f"Tavs galvenais mērķis ir: {main_goal}\n\n"
            "Sāc ar pirmo mazo soli. Ja mērķis šķiet liels, sadali to vienā konkrētā darbībā, ko vari izdarīt tagad."
        )

    if memories:
        memory = memories[0]
        return (
            "💡 Mans ieteikums šodien:\n\n"
            f"Es redzu, ka tev ir svarīga lieta: {memory}\n\n"
            "Iesaku to nepaturēt tikai galvā. Ja tas jāizdara šodien, uzraksti to kā mērķi."
        )

    if reminders > 0:
        return (
            "💡 Mans ieteikums šodien:\n\n"
            f"Tev ir {reminders} aktīvi atgādinājumi. Pārbaudi tos un izvēlies, kas šodien ir svarīgākais."
        )

    return (
        "💡 Mans ieteikums šodien:\n\n"
        "Uzraksti vienu galveno lietu, ko šodien gribi paveikt. Viena skaidra prioritāte padara dienu daudz vieglāk vadāmu."
    )
