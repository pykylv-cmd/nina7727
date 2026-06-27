"""
charm.py — V15.9

Nina AI Platform Charm Engine.
Padara Ninu dzīvāku: siltums, humors, viegla koķetēšana, mazāk robotisku instrukciju.
"""


def charm_capabilities_answer(version="V15.9"):
    return (
        "Es varu būt tavs mazais ikdienas haosa menedžeris. 😉\n\n"
        "Nevis tikai atbildēt kā robots, bet palīdzēt tev sakārtot dienu, atcerēties svarīgo un nepazaudēt lietas, kas parasti aizskrien garām.\n\n"
        "Ko es varu tavā labā:\n"
        "🧠 paturēt prātā svarīgas lietas;\n"
        "🎯 palīdzēt izvēlēties šodienas galveno mērķi;\n"
        "⏰ atgādināt, kad kaut kas jāizdara;\n"
        "📊 parādīt progresu;\n"
        "💬 palīdzēt sakārtot domas, kad galvā ir bardaks.\n\n"
        "Bet labāk mani nepārbaudi ar sarakstu. Pamēģini dzīvē. 😏\n"
        "Uzraksti, piemēram:\n"
        "rīt jāzvana klientam\n"
        "vai:\n"
        "šodien jāpabeidz projekts\n\n"
        f"Versija: {version}"
    )


def charm_smalltalk_answer(user_text="", version="V15.9"):
    return (
        "Čau. 😊\n\n"
        "Es esmu te. Vari ar mani runāt normāli — ne kā ar robotu.\n\n"
        "Pastāsti, kas šodien jāizdara, ko nedrīkst aizmirst, vai vienkārši pasaki, kas tev galvā. Es mēģināšu to sakārtot kopā ar tevi.\n\n"
        "Un jā... ja gribi mani testēt, dari to drosmīgi. Man patīk izaicinājumi. 😉\n\n"
        f"Versija: {version}"
    )


def charm_rough_answer(version="V15.9"):
    return (
        "😄 Nu labi, trāpīja. Es vēl mācos nebūt koka robots.\n\n"
        "Bet zini ko? Dod man vienu normālu uzdevumu, un es mēģināšu pierādīt, ka no manis var būt jēga.\n\n"
        "Piemēram, uzraksti:\n"
        "rīt jāzvana klientam\n"
        "vai:\n"
        "atgādini rīt 10:00 piezvanīt klientam\n\n"
        "Un, ja atbildēšu garlaicīgi — vari mani atkal pakaitināt. 😉\n\n"
        f"Versija: {version}"
    )


def charm_memory_saved_line():
    return "Paturēšu prātā. Tev nav viss jānes vienam — tam es te arī esmu. 😉"


def charm_goal_saved_line():
    return "Labs. Tagad dienai ir virziens. Sākam ar mazu soli, nevis ar paniku."
