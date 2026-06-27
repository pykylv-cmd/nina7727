"""
learning.py — V16.4

Nina AI Platform
Learning Engine

Vienkāršs modulis, kas apkopo lietotāja intereses un
palīdz Ninai kļūt personiskākai.
"""

from collections import Counter


class LearningProfile:
    def __init__(self):
        self.topics = []
        self.reply_style = "warm"
        self.visits = 0

    def add_topic(self, topic: str):
        topic = (topic or "").strip().lower()
        if topic:
            self.topics.append(topic)

    def register_visit(self):
        self.visits += 1

    def favorite_topics(self, limit=3):
        return Counter(self.topics).most_common(limit)

    def summary(self):
        fav = self.favorite_topics()
        if not fav:
            return "Es vēl tikai mācos iepazīt tevi."

        names = ", ".join(name for name, _ in fav)
        return (
            f"Pamazām iepazīstu tevi. 😊 "
            f"Šobrīd visbiežāk mūsu sarunās parādās: {names}."
        )

    def choose_style(self):
        if self.visits >= 20:
            return "friendly"
        if self.visits >= 5:
            return "warm"
        return "polite"


def detect_topic(text: str) -> str:
    t = (text or "").lower()

    mapping = {
        "darbs": ["klients", "projekts", "darbs", "e-pasts"],
        "plānošana": ["mērķis", "plāns", "diena"],
        "atmiņa": ["atceries", "neaizmirst", "jāzvana"],
        "iepirkšanās": ["nopirkt", "veikals", "piens"],
    }

    for topic, words in mapping.items():
        if any(w in t for w in words):
            return topic

    return "saruna"


def debug(profile: LearningProfile):
    return (
        "🧠 Learning Engine\n\n"
        f"Apmeklējumi: {profile.visits}\n"
        f"Stils: {profile.choose_style()}\n"
        f"Tēmas: {profile.favorite_topics()}"
    )
