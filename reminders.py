"""
reminders.py — V15.2

Nina AI Platform atgādinājumu modulis.
Šeit nav Stripe, Telegram adaptera vai webhook koda.
Modulis:
- atpazīst "atgādini..." tekstu;
- mēģina saprast vienkāršu laiku;
- sagatavo datus saglabāšanai.
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import re


WEEKDAYS_LV = {
    "pirmdien": 0,
    "otrdien": 1,
    "trešdien": 2,
    "tresdien": 2,
    "ceturtdien": 3,
    "piektdien": 4,
    "sestdien": 5,
    "svētdien": 6,
    "svetdien": 6,
}


def _clean_body(text):
    raw = (text or "").strip()
    lower = raw.lower()
    for prefix in ["atgādini man ", "atgadini man ", "atgādini ", "atgadini "]:
        if lower.startswith(prefix):
            return raw[len(prefix):].strip()
    return raw


def _extract_time(lower):
    m = re.search(r"(\d{1,2})[:\.](\d{2})", lower)
    if m:
        hour = int(m.group(1))
        minute = int(m.group(2))
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return hour, minute

    m = re.search(r"\b(\d{1,2})\b", lower)
    if m:
        hour = int(m.group(1))
        if 0 <= hour <= 23:
            return hour, 0

    return 9, 0


def _remove_time_words(body):
    text = body
    patterns = [
        r"\brīt\b",
        r"\brit\b",
        r"\bšodien\b",
        r"\bsodien\b",
        r"\bpēc\s+\d+\s+stundām\b",
        r"\bpec\s+\d+\s+stundam\b",
        r"\b\d{1,2}[:\.]\d{2}\b",
    ]
    for day in WEEKDAYS_LV:
        patterns.append(r"\b" + re.escape(day) + r"\b")
    for p in patterns:
        text = re.sub(p, "", text, flags=re.IGNORECASE)
    return " ".join(text.split()).strip(" ,.-")


def parse_reminder_request(text, default_timezone="Europe/Riga"):
    raw = (text or "").strip()
    lower = raw.lower()

    if not (lower.startswith("atgādini") or lower.startswith("atgadini")):
        return None

    body = _clean_body(raw)
    if not body:
        return {"ok": False, "reason": "empty"}

    tz = ZoneInfo(default_timezone)
    now = datetime.now(tz)
    target = None
    human = ""

    # pēc X stundām
    m = re.search(r"(pēc|pec)\s+(\d+)\s+stund", lower)
    if m:
        hours = int(m.group(2))
        target = now + timedelta(hours=hours)
        human = f"pēc {hours} stundām"

    # rīt / rit
    elif "rīt" in lower or "rit" in lower:
        hour, minute = _extract_time(lower)
        target = (now + timedelta(days=1)).replace(hour=hour, minute=minute, second=0, microsecond=0)
        human = f"rīt {hour:02d}:{minute:02d}"

    # šodien / sodien
    elif "šodien" in lower or "sodien" in lower:
        hour, minute = _extract_time(lower)
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target <= now:
            target = target + timedelta(days=1)
            human = f"rīt {hour:02d}:{minute:02d}"
        else:
            human = f"šodien {hour:02d}:{minute:02d}"

    # nedēļas dienas
    else:
        for word, weekday in WEEKDAYS_LV.items():
            if word in lower:
                hour, minute = _extract_time(lower)
                days_ahead = (weekday - now.weekday()) % 7
                if days_ahead == 0:
                    days_ahead = 7
                target = (now + timedelta(days=days_ahead)).replace(hour=hour, minute=minute, second=0, microsecond=0)
                human = f"{word} {hour:02d}:{minute:02d}"
                break

    reminder_text = _remove_time_words(body) or body

    if not target:
        return {
            "ok": True,
            "text": reminder_text,
            "remind_at": "",
            "local_time": "",
            "human_time": "",
            "needs_time": True,
        }

    return {
        "ok": True,
        "text": reminder_text,
        "remind_at": target.isoformat(),
        "local_time": target.strftime("%Y-%m-%d %H:%M"),
        "human_time": human,
        "needs_time": False,
    }


def save_reminder_logic(get_db_fn, db_execute_fn, user_id, reminder_text, remind_at="", local_time=""):
    try:
        conn = get_db_fn()
        c = conn.cursor()
        db_execute_fn(
            c,
            """
            INSERT INTO reminders (user_id, text, remind_at, local_time, status)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (str(user_id), reminder_text, remind_at or "", local_time or "", "active")
        )
        conn.commit()
        c.close()
        conn.close()
        return True
    except Exception as e:
        print("Reminder save kļūda:", e)
        return False


def build_reminder_saved_answer(reminder_text, human_time="", version="V15.2"):
    if human_time:
        return (
            "⏰ Atgādinājums saglabāts. ✅\n\n"
            f"Kas: {reminder_text}\n"
            f"Kad: {human_time}\n\n"
            "Es to paturēšu Ninas plānā.\n\n"
            f"Versija: {version}"
        )

    return (
        "⏰ Pierakstīju kā atgādinājumu. ✅\n\n"
        f"Kas: {reminder_text}\n\n"
        "Laiku vēl vajag precizēt, piemēram:\n"
        "atgādini rīt 10:00 piezvanīt klientam\n\n"
        f"Versija: {version}"
    )


def build_reminder_help_answer(version="V15.2"):
    return (
        "⏰ Raksti šādi:\n\n"
        "atgādini rīt 10:00 piezvanīt klientam\n"
        "atgādini pirmdien 9:00 sapulce\n"
        "atgādini pēc 2 stundām pārbaudīt e-pastu\n\n"
        f"Versija: {version}"
    )
