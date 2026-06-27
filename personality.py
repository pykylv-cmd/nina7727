"""
personality.py — V15.1

Nina AI Platform personības modulis.
Šeit dzīvo Ninas tonis, sajūta, stils un kopējā personība.
Šeit nav Stripe, datubāzes, Telegram vai webhook koda.
"""


def nina_signature_line():
    return "Nina – tava personīgā AI asistente, kas atceras, plāno un palīdz katru dienu."


def nina_start_intro():
    return (
        "Es neesmu tikai čats. Es esmu tava personīgā AI asistente.\n\n"
        "Es palīdzēšu atcerēties svarīgo, sakārtot dienu un virzīties uz priekšu soli pa solim.\n\n"
        "Tu vari rakstīt dabiski, piemēram:\n"
        "• rīt jāzvana klientam\n"
        "• šodien jāpabeidz projekts\n"
        "• neaizmirst nopirkt pienu"
    )


def nina_daily_closing_line():
    return "Es esmu tepat. Uzraksti vienu lietu, ko šodien gribi sakārtot."


def nina_memory_tone_line():
    return "Es to paturēšu prātā, lai tev pašam nav viss jānes galvā."


def nina_goal_tone_line():
    return "Tagad dienai ir skaidrāks virziens. Svarīgākais ir sākt ar vienu mazu soli."
