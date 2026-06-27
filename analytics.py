"""
analytics.py — V15.6

Nina AI Platform analītikas modulis.
Šeit nav Telegram, WhatsApp, Stripe vai webhook koda.

Šis modulis veido lietotāja progresa pārskatu:
- atmiņas;
- mērķi;
- atgādinājumi;
- streak;
- XP;
- līmenis;
- dominējošās tēmas.
"""

from collections import Counter


def safe_int(value, default=0):
    try:
        return int(value or 0)
    except Exception:
        return default


def count_items(items):
    return len([x for x in (items or []) if str(x or "").strip()])


def build_activity_snapshot(memories=None, goals=None, reminders_count=0, streak_days=0, xp=0, level=1):
    memories = memories or []
    goals = goals or []

    return {
        "memories_count": count_items(memories),
        "goals_count": count_items(goals),
        "reminders_count": safe_int(reminders_count),
        "streak_days": safe_int(streak_days),
        "xp": safe_int(xp),
        "level": safe_int(level, 1),
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


def build_weekly_progress_text(snapshot, topic_counts=None, version="V15.6"):
    progress = build_progress_line(snapshot)
    topic_summary = build_topic_summary(topic_counts or {})

    memories = safe_int(snapshot.get("memories_count"))
    goals = safe_int(snapshot.get("goals_count"))
    reminders = safe_int(snapshot.get("reminders_count"))
    streak = safe_int(snapshot.get("streak_days"))
    xp = safe_int(snapshot.get("xp"))
    level = safe_int(snapshot.get("level"), 1)

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
        f"⭐ XP: {xp}",
        f"🏅 Līmenis: {level}",
    ]

    if topic_summary:
        lines.extend(["", f"🧠 {topic_summary}"])

    lines.extend([
        "",
        "💡 Mans ieteikums:",
        "Turpini ar vienu skaidru mērķi dienā. Mazs, bet konsekvents progress ilgtermiņā uzvar haosu.",
        "",
        f"Versija: {version}",
    ])

    return "\n".join(lines)


def build_empty_progress_text(version="V15.6"):
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
