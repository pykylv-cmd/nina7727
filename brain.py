"""
brain.py
Nina AI Platform V15.3

Šeit dzīvo Ninas "smadzenes".

NAV Telegram.
NAV WhatsApp.
NAV Stripe.
NAV webhook.

Tikai AI loģika.
"""

from collections import Counter

# ==========================================
# Tēmu atslēgvārdi
# ==========================================

IMPORTANT_KEYWORDS = {

    "darbs": [
        "klients",
        "projekts",
        "sapulce",
        "darbs",
        "piedāvājums",
        "epasts",
        "e-pasts",
        "klientam",
        "zvans"
    ],

    "ģimene": [
        "mamma",
        "tētis",
        "berns",
        "bērns",
        "sieva",
        "vīrs",
        "ģimene"
    ],

    "veselība": [
        "ārsts",
        "zobārsts",
        "vitamīni",
        "sports",
        "slims"
    ],

    "finanses": [
        "nauda",
        "rēķins",
        "stripe",
        "premium",
        "banka",
        "eiro"
    ],

    "iepirkšanās": [
        "nopirkt",
        "veikals",
        "piens",
        "maize",
        "produkti"
    ]
}


# ==========================================
# Atrod tēmas vienā tekstā
# ==========================================

def detect_topics(text):

    lower = text.lower()

    found = []

    for topic, words in IMPORTANT_KEYWORDS.items():

        for word in words:

            if word in lower:

                found.append(topic)

                break

    return found


# ==========================================
# Analizē vairākas atmiņas
# ==========================================

def analyze_memories(memory_list):

    topics = []

    for memory in memory_list:

        topics.extend(detect_topics(memory))

    counter = Counter(topics)

    return dict(counter)


# ==========================================
# Atrod svarīgāko tēmu
# ==========================================

def most_important_topic(memory_list):

    stats = analyze_memories(memory_list)

    if not stats:

        return None

    return max(stats, key=stats.get)


# ==========================================
# Dod īsu kopsavilkumu Coach modulim
# ==========================================

def build_brain_summary(memory_list):

    topic = most_important_topic(memory_list)

    if topic is None:

        return None

    summaries = {

        "darbs":
            "Pēdējā laikā tev daudz uzmanības prasa darbs.",

        "ģimene":
            "Šobrīd svarīga loma ir ģimenei.",

        "veselība":
            "Izskatās, ka veselība tev šobrīd ir prioritāte.",

        "finanses":
            "Pēdējā laikā bieži parādās finanšu tēmas.",

        "iepirkšanās":
            "Tev ir vairāki sadzīves pirkumi, ko neaizmirst."
    }

    return summaries.get(topic)
