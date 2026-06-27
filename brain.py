"""
brain.py — V15.4

Nina AI Platform smadzeņu modulis.
Šeit nav Telegram, WhatsApp, Stripe vai webhook koda.
"""

from collections import Counter


IMPORTANT_KEYWORDS = {
    "darbs": ["klients", "klientam", "projekts", "sapulce", "darbs", "piedāvājums", "epasts", "e-pasts", "zvans", "piezvanīt"],
    "ģimene": ["mamma", "tētis", "berns", "bērns", "sieva", "vīrs", "ģimene"],
    "veselība": ["ārsts", "arsts", "zobārsts", "zobarsts", "vitamīni", "sports", "slims"],
    "finanses": ["nauda", "rēķins", "rekins", "stripe", "premium", "banka", "eiro"],
    "iepirkšanās": ["nopirkt", "veikals", "piens", "maize", "produkti"],
}


def detect_topics(text):
    lower = (text or "").lower()
    found = []
    for topic, words in IMPORTANT_KEYWORDS.items():
        for word in words:
            if word in lower:
                found.append(topic)
                break
    return found


def analyze_memories(memory_list):
    topics = []
    for memory in memory_list or []:
        topics.extend(detect_topics(memory))
    return dict(Counter(topics))


def most_important_topic(memory_list):
    stats = analyze_memories(memory_list)
    if not stats:
        return None
    return max(stats, key=stats.get)


def build_brain_summary(memory_list):
    topic = most_important_topic(memory_list)
    if topic is None:
        return None

    summaries = {
        "darbs": "pēdējā laikā tev daudz uzmanības prasa darbs vai klienti.",
        "ģimene": "šobrīd svarīga loma ir ģimenei un personīgām lietām.",
        "veselība": "veselība šobrīd parādās kā svarīga tēma.",
        "finanses": "pēdējā laikā parādās finanšu vai maksājumu tēmas.",
        "iepirkšanās": "tev ir vairāki sadzīves pirkumi, ko nevajadzētu aizmirst.",
    }
    return summaries.get(topic)
