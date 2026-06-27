"""
coach.py — V15.4

Ninas ikdienas ieteikumu modulis ar brain.py secinājumiem.
"""


def _clean_list(items):
    cleaned = []
    for item in items or []:
        text = str(item or "").strip()
        if text:
            cleaned.append(text)
    return cleaned


def _clean_goal_text(text):
    text = str(text or "").strip()
    lowered = text.lower()
    prefixes = [
        "šodien jāizdara ", "sodien jaizdara ",
        "šodien jāpabeidz ", "sodien japabeidz ",
        "šodien jāuztaisa ", "sodien jauztaisa ",
    ]
    for prefix in prefixes:
        if lowered.startswith(prefix):
            return text[len(prefix):].strip() or text
    return text


def _clean_memory_text(text):
    text = str(text or "").strip()
    lowered = text.lower()
    prefixes = ["neaizmirst ", "atceries, ka ", "atceries ka "]
    for prefix in prefixes:
        if lowered.startswith(prefix):
            return text[len(prefix):].strip() or text
    return text


def build_daily_coach_tip(goals=None, memories=None, reminders=0, brain_summary=None):
    goals = _clean_list(goals)
    memories = _clean_list(memories)
    reminders = int(reminders or 0)

    brain_line = ""
    if brain_summary:
        brain_line = f"\n\n🧠 Ko es pamanu: {brain_summary}"

    if goals and memories:
        main_goal = _clean_goal_text(goals[0])
        memory = _clean_memory_text(memories[0])
        return (
            "💡 Mans ieteikums šodien:\n\n"
            f"Izskatās, ka šodien galvenais virziens ir: {main_goal}.\n"
            f"Es arī paturu prātā: {memory}."
            f"{brain_line}\n\n"
            "Sāc ar vienu mazu soli pie galvenā mērķa. Kad tas būs iekustināts, būs vieglāk mierīgi sakārtot arī pārējo."
        )

    if goals:
        main_goal = _clean_goal_text(goals[0])
        return (
            "💡 Mans ieteikums šodien:\n\n"
            f"Šodien tev ir viens skaidrs mērķis — {main_goal}."
            f"{brain_line}\n\n"
            "Sāc nevis ar visu uzreiz, bet ar pirmo mazo soli. Pat 10 minūtes kustības uz priekšu dos sajūtu, ka diena ir tavās rokās."
        )

    if memories:
        memory = _clean_memory_text(memories[0])
        return (
            "💡 Mans ieteikums šodien:\n\n"
            f"Es redzu, ka tev svarīgi nepazaudēt šo: {memory}."
            f"{brain_line}\n\n"
            "Ja tas ir jāizdara šodien, pārvērt to par mērķi. Ja tas ir vēlākam laikam, vari man paprasīt izveidot atgādinājumu."
        )

    if reminders > 0:
        return (
            "💡 Mans ieteikums šodien:\n\n"
            f"Tev ir {reminders} aktīvi atgādinājumi."
            f"{brain_line}\n\n"
            "Iesaku sākt ar to, kas prasa vismazāk laika, lai ātri noņemtu vienu lietu no galvas."
        )

    return (
        "💡 Mans ieteikums šodien:\n\n"
        "Šobrīd diena vēl ir tukša. Uzraksti vienu galveno lietu, ko gribi paveikt, un es palīdzēšu to pārvērst skaidrā virzienā."
    )
