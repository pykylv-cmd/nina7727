"""
conversation_engine.py — V16.1

Nina AI Platform
Conversation Engine

Atbild ne tikai uz tekstu, bet cenšas uzturēt sarunu.
"""

import random


INTENTS = {
    "capabilities": [
        "ko vari", "ko tu vari", "ko māki", "ko maki"
    ],
    "bad_day": [
        "slikta diena", "viss besī", "viss besi", "noguris", "nogurusi"
    ],
    "testing": [
        "testēju", "testeju", "pārbaudu", "parbaudu"
    ]
}


def detect_intent(text: str) -> str:
    t = (text or "").lower()

    for intent, words in INTENTS.items():
        if any(w in t for w in words):
            return intent

    if "?" in t:
        return "question"

    return "general"


def build_reply(text: str):
    intent = detect_intent(text)

    if intent == "capabilities":
        return random.choice([
            "😊 Labs jautājums.\n\nPirms lielos ar sevi, gribu saprast tevi. Kas tev ikdienā visvairāk traucē — haoss, aizmirstas lietas vai laika trūkums?",
            "Es varētu uzreiz uzskaitīt savas iespējas... bet labāk pasaki vienu problēmu. Mēģināšu to atrisināt kopā ar tevi. 😉",
            "Man vairāk patīk pierādīt savu vērtību, nevis par to stāstīt. Iedod man vienu īstu uzdevumu."
        ])

    if intent == "bad_day":
        return random.choice([
            "😔 Izklausās, ka šodien nav tava vieglākā diena. Kas tieši notika?",
            "Dažreiz pietiek ar vienu sliktu brīdi, lai visa diena šķistu pelēka. Gribi izstāstīt?"
        ])

    if intent == "testing":
        return random.choice([
            "😄 Droši testē mani. Jo vairāk mani izaicināsi, jo labāku mani uztaisīs mans izstrādātājs.",
            "Man patīk testi. Tikai neesi pārāk saudzīgs. 😉"
        ])

    if intent == "question":
        return "Interesants jautājums. 😊 Pastāsti mazliet vairāk, lai varu atbildēt ne tikai pareizi, bet arī noderīgi."

    return random.choice([
        "Es klausos. 😊 Kas šobrīd tev ir svarīgākais?",
        "Pastāsti vairāk. Man šķiet, ka aiz šī ir interesantāks stāsts.",
        "Labi, sākam ar vienu soli. Kas šobrīd ir pirmais, ko gribi atrisināt?"
    ])
