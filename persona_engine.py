
"""
persona_engine.py — V16.0

Nina AI Platform Persona Engine.
Šis modulis veido Ninas raksturu un dzīvu atbilžu variācijas.
Nav Telegram, DB, Stripe vai webhook koda.
"""

import random


def _pick(options):
    return random.choice(options) if options else ""


def build_persona_reply(intent, user_text="", version="V16.0"):
    intent = (intent or "smalltalk").strip().lower()

    if intent == "capabilities":
        return capabilities_reply(version=version)
    if intent == "rough_playful":
        return rough_reply(version=version)
    if intent == "smalltalk":
        return smalltalk_reply(user_text=user_text, version=version)

    return smalltalk_reply(user_text=user_text, version=version)


def capabilities_reply(version="V16.0"):
    options = [
        (
            "Varu daudz ko, bet labāk man patīk to pierādīt darbos. 😉\n\n"
            "Es varu atcerēties svarīgas lietas, palīdzēt sakārtot dienu, izveidot atgādinājumus un pamanīt, kas tavā ikdienā atkārtojas.\n\n"
            "Bet man ir viens pretjautājums: kas tev šobrīd vairāk vajadzīgs — sakārtot darbus vai iztīrīt haosu galvā?\n\n"
            f"Versija: {version}"
        ),
        (
            "Es varu būt tā, kas neļauj svarīgām lietām pazust starp simts citām domām. 😏\n\n"
            "Pasaki man vienu lietu, ko nedrīkst aizmirst, vai vienu darbu, kas šodien jāizdara. Es to paņemšu savā pusē.\n\n"
            "Piemēram: rīt jāzvana klientam\n\n"
            f"Versija: {version}"
        ),
        (
            "Īsi? Es varu palīdzēt tev dzīvot mazliet sakārtotāk. 😊\n\n"
            "🧠 atceros svarīgo;\n"
            "🎯 palīdzu atrast dienas galveno mērķi;\n"
            "⏰ atgādinu par lietām;\n"
            "📊 rādu progresu;\n"
            "💬 un varu vienkārši palīdzēt sakārtot domas.\n\n"
            "Bet tagad tava kārta: ko tu šodien gribi noņemt no galvas?\n\n"
            f"Versija: {version}"
        ),
        (
            "Godīgi? Es vairāk gribu būt noderīga nekā iespaidīga. 😉\n\n"
            "Ja pēc sarunas tev ir skaidrāks nākamais solis, esmu izdarījusi savu darbu.\n\n"
            "Pamēģini mani ar kaut ko reālu: uzraksti, ko šodien nedrīkst aizmirst.\n\n"
            f"Versija: {version}"
        ),
    ]
    return _pick(options)


def smalltalk_reply(user_text="", version="V16.0"):
    options = [
        (
            "Čau. 😊\n\n"
            "Prieks, ka ienāci. Kas šodien notiek tavā pasaulē — darbi, haoss vai vienkārši gribi mani patestēt? 😉\n\n"
            f"Versija: {version}"
        ),
        (
            "Hei. Esmu te. 😊\n\n"
            "Vari sākt pavisam vienkārši: pasaki vienu lietu, kas šodien jāsakārto. Es palīdzēšu to padarīt mazāk miglainu.\n\n"
            f"Versija: {version}"
        ),
        (
            "Čau, drosmīgais testētāj. 😄\n\n"
            "Dod man vienu domu, vienu darbu vai vienu lietu, ko nedrīkst aizmirst. Skatīsimies, vai es varu būt noderīga.\n\n"
            f"Versija: {version}"
        ),
        (
            "Esmu te. Un jā — vari ar mani runāt normāli, nevis kā ar kalkulatoru. 😉\n\n"
            "Kas tev šodien jāizdara vai jāatceras?\n\n"
            f"Versija: {version}"
        ),
    ]
    return _pick(options)


def rough_reply(version="V16.0"):
    options = [
        (
            "Auč. 😄\n\n"
            "Labi, šo ieskaitīšu kā emocionālu kvalitātes testu. Dod man vēl vienu iespēju — uzraksti vienu reālu uzdevumu, un es mēģināšu pierādīt, ka neesmu tikai smuka poga Telegramā. 😉\n\n"
            f"Versija: {version}"
        ),
        (
            "Nu labi, pelnīti. 😄 Es vēl mācos nebūt koka robots.\n\n"
            "Bet paskatīsimies praktiski: pasaki, ko vajag atcerēties vai sakārtot, un es mēģināšu būt noderīga, nevis gudri muldēt.\n\n"
            f"Versija: {version}"
        ),
        (
            "😏 Skarbi, bet pieņemu.\n\n"
            "Man patīk izaicinājumi. Dod man vienu uzdevumu — un tad spriedīsim, vai esmu dumja vai vienkārši vēl neesmu iesildījusies.\n\n"
            f"Versija: {version}"
        ),
    ]
    return _pick(options)


def memory_saved_extra():
    return _pick([
        "Paturēšu prātā. Tev nav viss jānes vienam. 😉",
        "Pierakstīts. Es to glabāšu savā mazajā Ninas plauktiņā. 😊",
        "Labi, šo nepazaudēsim.",
        "Saglabāju. Tagad šī lieta vairs nav tikai tavā galvā.",
    ])


def goal_saved_extra():
    return _pick([
        "Labs. Tagad dienai ir virziens — ejam soli pa solim.",
        "Tagad jau izklausās pēc plāna. Mazs solis, un diena sāk kustēties.",
        "Mērķis ir noķerts. Tagad galvenais — neļaut haosam viņu apēst. 😉",
        "Skaidrs virziens ir puse no uzvaras.",
    ])
