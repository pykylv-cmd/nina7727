"""
analytics.py — V15.8

Nina AI Platform analītikas modulis.

Šis modulis gatavo:
- progresa pārskatu;
- tēmu pārskatu;
- XP/līmeņa tekstus;
- lietotāja aktivitātes snapshot.
Šeit nav Telegram, WhatsApp, Stripe vai webhook koda.
"""

from collections import Counter


XP_PER_LEVEL = 100


def safe_int(value, default=0):
    try:
        return int(value or 0)
    except Exception:
        return default


def count_items(items):
    return len([x for x in (items or []) if str(x or "").strip()])


def calculate_level_from_xp(xp):
    xp = safe_int(xp)
    return max(1, xp // XP_PER_LEVEL + 1)


def calculate_next_level_xp(xp):
    xp = safe_int(xp)
    current_level = calculate_level_from_xp(xp)
    return current_level * XP_PER_LEVEL


def build_activity_snapshot(memories=None, goals=None, reminders_count=0, streak_days=0, xp=0, level=None):
    memories = memories or []
    goals = goals or []
    xp = safe_int(xp)

    if level is None:
        level = calculate_level_from_xp(xp)

    return {
        "memories_count": count_items(memories),
        "goals_count": count_items(goals),
        "reminders_count": safe_int(reminders_count),
        "streak_days": safe_int(streak_days),
        "xp": xp,
        "level": safe_int(level, 1),
        "next_level_xp": calculate_next_level_xp(xp),
    }


def build_progress_line(snapshot):
    memories = safe_int(snapshot.get("memories_count"))
    goals = safe_int(snapshot.get("goals_count"))
    reminders = safe_int(snapshot.get("reminders_count"))
    streak = safe_int(snapshot.get("streak_days"))

    parts = []

    if goals > 0:
        parts.append(f"{goals} mērķi")
    if memories > 0:
        parts.append(f"{memories} atmiņas")
    if reminders > 0:
        parts.append(f"{reminders} atgādinājumi")
    if streak > 1:
        parts.append(f"{streak} dienu streak")

    if not parts:
        return "Šodien vēl sākam no tīras lapas."

    return "Šobrīd tavā Ninas ritmā ir: " + ", ".join(parts) + "."


def detect_dominant_topics(topic_counts):
    if not topic_counts:
        return []

    counter = Counter(topic_counts)
    return [topic for topic, _ in counter.most_common(3)]


def build_topic_summary(topic_counts):
    topics = detect_dominant_topics(topic_counts)

    if not topics:
        return None

    readable = {
        "darbs": "darbs un klienti",
        "ģimene": "ģimene",
        "veselība": "veselība",
        "finanses": "finanses",
        "iepirkšanās": "ikdienas pirkumi",
    }

    nice_topics = [readable.get(t, t) for t in topics]

    if len(nice_topics) == 1:
        return f"Pēdējā laikā visbiežāk parādās tēma: {nice_topics[0]}."

    return "Pēdējā laikā biežāk parādās šīs tēmas: " + ", ".join(nice_topics) + "."


def build_topic_list(topic_counts):
    if not topic_counts:
        return []

    readable = {
        "darbs": "darbs un klienti",
        "ģimene": "ģimene",
        "veselība": "veselība",
        "finanses": "finanses",
        "iepirkšanās": "ikdienas pirkumi",
    }

    counter = Counter(topic_counts)
    lines = []

    for topic, count in counter.most_common(5):
        name = readable.get(topic, topic)
        lines.append(f"• {name}: {count}")

    return lines


def build_xp_summary(snapshot):
    xp = safe_int(snapshot.get("xp"))
    level = safe_int(snapshot.get("level"), 1)
    next_level = safe_int(snapshot.get("next_level_xp"), XP_PER_LEVEL)
    remaining = max(0, next_level - xp)

    return (
        f"⭐ XP: {xp}\n"
        f"🏅 Līmenis: {level}\n"
        f"➡️ Līdz nākamajam līmenim: {remaining} XP"
    )


def build_weekly_progress_text(snapshot, topic_counts=None, version="V15.8"):
    progress = build_progress_line(snapshot)
    topic_summary = build_topic_summary(topic_counts or {})
    topic_lines = build_topic_list(topic_counts or {})

    memories = safe_int(snapshot.get("memories_count"))
    goals = safe_int(snapshot.get("goals_count"))
    reminders = safe_int(snapshot.get("reminders_count"))
    streak = safe_int(snapshot.get("streak_days"))

    lines = [
        "📊 Tavs progress ar Ninu",
        "",
        progress,
        "",
        f"🧠 Saglabātās atmiņas: {memories}",
        f"🎯 Aktīvie mērķi: {goals}",
        f"⏰ Aktīvie atgādinājumi: {reminders}",
        "",
        f"🔥 Streak: {streak} dienas",
        build_xp_summary(snapshot),
    ]

    if topic_summary:
        lines.extend(["", f"🧠 {topic_summary}"])

    if topic_lines:
        lines.extend(["", "TOP tēmas:"])
        lines.extend(topic_lines)

    lines.extend([
        "",
        "💡 Mans ieteikums:",
        "Skaties, kuras tēmas atkārtojas visbiežāk. Tieši tur parasti slēpjas lietas, kas visvairāk ietekmē tavu ikdienu.",
        "",
        f"Versija: {version}",
    ])

    return "\n".join(lines)


def build_empty_progress_text(version="V15.8"):
    return (
        "📊 Tavs progress ar Ninu\n\n"
        "Vēl nav pietiekami daudz datu, lai veidotu īstu pārskatu.\n\n"
        "Sāc vienkārši:\n"
        "• uzraksti vienu mērķi;\n"
        "• saglabā vienu svarīgu lietu;\n"
        "• izveido vienu atgādinājumu.\n\n"
        "Pēc dažām dienām Nina varēs parādīt daudz vērtīgāku progresu.\n\n"
        f"Versija: {version}"
    )
