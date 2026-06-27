"""
memory.py — V14.1

Atmiņas un mērķu atbildes atsevišķā modulī.
Šeit nav Stripe, Premium, webhook vai datubāzes savienojuma.
Tas nozīmē: varam mainīt atmiņas tekstus, neriskējot ar maksājumiem.
"""


def build_memory_saved_answer(saved_text, version="V14.1"):
    return (
        "🧠 Pierakstīju. ✅\n\n"
        f"Atcerēšos: {saved_text}\n\n"
        "Ja vajadzēs, vēlāk varēsim no tā izveidot atgādinājumu vai papildināt šo domu.\n\n"
        f"Versija: {version}"
    )


def build_goal_saved_answer(goal_text, version="V14.1"):
    return (
        "🎯 Saglabāju šodienas mērķi. ✅\n\n"
        f"Mērķis: {goal_text}\n\n"
        "Tagad dienai ir skaidrs virziens. Ja gribi, vari man pastāstīt pirmo mazo soli.\n\n"
        f"Versija: {version}"
    )
