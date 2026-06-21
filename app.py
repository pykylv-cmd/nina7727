import os
import re
import json
import sqlite3
import asyncio
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

try:
    import psycopg2
except Exception:
    psycopg2 = None

from flask import Flask
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from openai import OpenAI

app = Flask(__name__)

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]

DEFAULT_TIMEZONE = "Europe/Riga"
DATABASE_URL = os.environ.get("DATABASE_URL")
DB_FILE = "nina_memory.db"
USE_POSTGRES = bool(DATABASE_URL and psycopg2)

FREE_BACKUP_LIMIT = 5
FREE_REMINDER_LIMIT = 5
FREE_SUMMARY_LIMIT_PER_DAY = 1
XP_PER_LEVEL = 100



def db_sql(sql):
    if USE_POSTGRES:
        return sql
    return sql.replace("%s", "?").replace("SERIAL PRIMARY KEY", "INTEGER PRIMARY KEY AUTOINCREMENT")


def db_execute(cursor, sql, params=None):
    if params is None:
        return cursor.execute(db_sql(sql))
    return cursor.execute(db_sql(sql), params)


def get_db():
    if USE_POSTGRES:
        return psycopg2.connect(DATABASE_URL)
    return sqlite3.connect(DB_FILE)


def init_db():
    conn = get_db()
    if USE_POSTGRES:
        conn.autocommit = True
    c = conn.cursor()

    db_execute(c, """
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            name TEXT DEFAULT '',
            city TEXT DEFAULT '',
            hobbies TEXT DEFAULT '',
            facts TEXT DEFAULT '',
            timezone TEXT DEFAULT 'Europe/Riga',
            goals TEXT DEFAULT '',
            projects TEXT DEFAULT '',
            dreams TEXT DEFAULT '',
            important_dates TEXT DEFAULT '',
            summary TEXT DEFAULT '',
            premium INTEGER DEFAULT 0,
            premium_until TEXT DEFAULT '',
            pets TEXT DEFAULT '',
            family TEXT DEFAULT '',
            profession TEXT DEFAULT '',
            favorite_car TEXT DEFAULT '',
            favorite_color TEXT DEFAULT '',
            favorite_music TEXT DEFAULT '',
            summary_updated_at TEXT DEFAULT '',
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1
        )
    """)

    db_execute(c, """
        CREATE TABLE IF NOT EXISTS messages (
            id SERIAL PRIMARY KEY,
            user_id TEXT,
            role TEXT,
            text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    db_execute(c, """
        CREATE TABLE IF NOT EXISTS reminders (
            id SERIAL PRIMARY KEY,
            user_id TEXT,
            text TEXT,
            remind_at TEXT,
            local_time TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    db_execute(c, """
        CREATE TABLE IF NOT EXISTS memory_backups (
            id SERIAL PRIMARY KEY,
            user_id TEXT,
            backup_text TEXT,
            source TEXT DEFAULT 'manual',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Ja tabulas jau eksistēja no vecākas versijas, pievieno trūkstošās kolonnas.
    for col, col_type in [
        ("timezone", "TEXT DEFAULT 'Europe/Riga'"),
        ("goals", "TEXT DEFAULT ''"),
        ("projects", "TEXT DEFAULT ''"),
        ("dreams", "TEXT DEFAULT ''"),
        ("important_dates", "TEXT DEFAULT ''"),
        ("summary", "TEXT DEFAULT ''"),
        ("premium", "INTEGER DEFAULT 0"),
        ("premium_until", "TEXT DEFAULT ''"),
        ("pets", "TEXT DEFAULT ''"),
        ("family", "TEXT DEFAULT ''"),
        ("profession", "TEXT DEFAULT ''"),
        ("favorite_car", "TEXT DEFAULT ''"),
        ("favorite_color", "TEXT DEFAULT ''"),
        ("favorite_music", "TEXT DEFAULT ''"),
        ("summary_updated_at", "TEXT DEFAULT ''"),
        ("xp", "INTEGER DEFAULT 0"),
        ("level", "INTEGER DEFAULT 1"),
    ]:
        try:
            db_execute(c, f"ALTER TABLE users ADD COLUMN {col} {col_type}")
        except Exception:
            pass

    try:
        db_execute(c, "ALTER TABLE reminders ADD COLUMN local_time TEXT")
    except Exception:
        pass

    c.close()
    conn.close()


def get_user(user_id):
    conn = get_db()
    c = conn.cursor()
    db_execute(c, """
        SELECT name, city, hobbies, facts, timezone, goals, projects, dreams,
               important_dates, summary, premium, premium_until, pets, family,
               profession, favorite_car, favorite_color, favorite_music,
               summary_updated_at, xp, level
        FROM users WHERE user_id = %s
    """, (user_id,))
    row = c.fetchone()

    if not row:
        db_execute(c, """
            INSERT INTO users
            (user_id, name, city, hobbies, facts, timezone, goals, projects, dreams,
             important_dates, summary, premium, premium_until, pets, family,
             profession, favorite_car, favorite_color, favorite_music, summary_updated_at, xp, level)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            user_id, "", "", "", "", DEFAULT_TIMEZONE, "", "", "", "", "",
            0, "", "", "", "", "", "", "", "", 0, 1
        ))
        conn.commit()
        row = ("", "", "", "", DEFAULT_TIMEZONE, "", "", "", "", "", 0, "", "", "", "", "", "", "", "", 0, 1)

    c.close()
    conn.close()

    user = {
        "name": row[0] or "",
        "city": row[1] or "",
        "hobbies": row[2] or "",
        "facts": row[3] or "",
        "timezone": row[4] or DEFAULT_TIMEZONE,
        "goals": row[5] or "",
        "projects": row[6] or "",
        "dreams": row[7] or "",
        "important_dates": row[8] or "",
        "summary": row[9] or "",
        "premium": row[10] or 0,
        "premium_until": row[11] or "",
        "pets": row[12] or "",
        "family": row[13] or "",
        "profession": row[14] or "",
        "favorite_car": row[15] or "",
        "favorite_color": row[16] or "",
        "favorite_music": row[17] or "",
        "summary_updated_at": row[18] or "",
        "xp": int(row[19] or 0) if len(row) > 19 else 0,
        "level": int(row[20] or 1) if len(row) > 20 else 1,
    }

    return apply_premium_expiration(user_id, user)


def update_user(user_id, user):
    conn = get_db()
    c = conn.cursor()
    db_execute(c, """
        UPDATE users SET
        name = %s, city = %s, hobbies = %s, facts = %s, timezone = %s,
        goals = %s, projects = %s, dreams = %s, important_dates = %s,
        summary = %s, premium = %s, premium_until = %s, pets = %s,
        family = %s, profession = %s, favorite_car = %s, favorite_color = %s,
        favorite_music = %s, summary_updated_at = %s, xp = %s, level = %s
        WHERE user_id = %s
    """, (
        user["name"], user["city"], user["hobbies"], user["facts"], user["timezone"],
        user["goals"], user["projects"], user["dreams"], user["important_dates"], user["summary"],
        user["premium"], user["premium_until"], user["pets"], user["family"], user["profession"],
        user["favorite_car"], user["favorite_color"], user["favorite_music"], user.get("summary_updated_at", ""),
        int(user.get("xp", 0) or 0), int(user.get("level", 1) or 1),
        user_id
    ))
    conn.commit()
    c.close()
    conn.close()


def apply_premium_expiration(user_id, user):
    """V9.4: automātiski izslēdz Premium, ja premium_until datums ir pagājis."""
    if not user.get("premium"):
        return user

    premium_until = (user.get("premium_until") or "").strip()
    if not premium_until:
        return user

    try:
        until_date = datetime.strptime(premium_until, "%Y-%m-%d").date()
        user_tz = ZoneInfo(user.get("timezone") or DEFAULT_TIMEZONE)
        today = datetime.now(user_tz).date()

        # Premium ir aktīvs līdz norādītās dienas beigām.
        # Nākamajā dienā pēc premium_until tas automātiski izslēdzas.
        if until_date < today:
            user["premium"] = 0
            user["premium_until"] = ""
            update_user(user_id, user)

    except Exception as e:
        print("Premium expiration pārbaudes kļūda:", e)

    return user


def premium_expiration_info(user_id):
    user = get_user(user_id)

    if not user.get("premium"):
        return "Premium šobrīd nav aktīvs."

    if user.get("premium_until"):
        return f"💎 Premium aktīvs līdz {user['premium_until']}."

    return "💎 Premium aktīvs bez beigu datuma."


def calculate_level(xp):
    try:
        xp = int(xp or 0)
    except Exception:
        xp = 0
    return max(1, xp // XP_PER_LEVEL + 1)


def xp_for_next_level(xp):
    try:
        xp = int(xp or 0)
    except Exception:
        xp = 0
    next_level_xp = calculate_level(xp) * XP_PER_LEVEL
    return max(0, next_level_xp - xp)


def add_xp(user_id, amount):
    try:
        user = get_user(user_id)
        current_xp = int(user.get("xp", 0) or 0)
        new_xp = max(0, current_xp + int(amount or 0))
        user["xp"] = new_xp
        user["level"] = calculate_level(new_xp)
        update_user(user_id, user)
        return new_xp, user["level"]
    except Exception as e:
        print("XP kļūda:", e)
        return None, None


def user_level_info(user_id):
    user = get_user(user_id)
    xp = int(user.get("xp", 0) or 0)
    level = calculate_level(xp)

    if level != int(user.get("level", 1) or 1):
        user["level"] = level
        update_user(user_id, user)

    next_level = level + 1
    left = xp_for_next_level(xp)

    return (
        f"🏆 Tavs līmenis: {level}\n\n"
        f"⭐ XP: {xp}\n\n"
        f"Nākamais līmenis: {next_level}\n"
        f"Vēl vajag: {left} XP"
    )


def valid_timezone(tz_name):
    try:
        ZoneInfo(tz_name)
        return True
    except Exception:
        return False


def detect_timezone(text):
    lower = text.lower()

    if "mana laika zona ir" in lower:
        tz = text.split("mana laika zona ir", 1)[1].strip()
        return tz if valid_timezone(tz) else None

    zones = {
        "latvijā": "Europe/Riga",
        "rīgā": "Europe/Riga",
        "amerikā": "America/New_York",
        "amerika": "America/New_York",
        "new york": "America/New_York",
        "los angeles": "America/Los_Angeles",
        "krievijā": "Europe/Moscow",
        "maskavā": "Europe/Moscow",
        "anglijā": "Europe/London",
        "londonā": "Europe/London",
        "vācijā": "Europe/Berlin",
        "berlīnē": "Europe/Berlin",
    }

    for key, tz in zones.items():
        if key in lower:
            return tz

    return None


def clean_text(text):
    return text.strip(" .,!?:;")


def split_items(text):
    text = text.replace("\n", ",")
    text = text.replace(" arī", "")
    text = re.sub(r"\s+un\s+", ",", text, flags=re.IGNORECASE)
    parts = [x.strip(" .,!?:;") for x in text.split(",")]
    return [x for x in parts if x]


def add_unique(old_text, new_items):
    items = [x.strip() for x in old_text.split(",") if x.strip()]
    for item in new_items:
        item = clean_text(item)
        if item and item not in items:
            items.append(item)
    return ", ".join(items)


def remove_item(old_text, item_to_remove):
    items = [x.strip() for x in old_text.split(",") if x.strip()]
    item_to_remove = clean_text(item_to_remove).lower()
    return ", ".join([item for item in items if item.lower() != item_to_remove])


def extract_after(text, patterns):
    for pattern in patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return clean_text(m.group(1))
    return ""


def update_profile_from_text(user_id, text):
    lower = text.lower()
    user = get_user(user_id)
    memory_keys = [
        "name", "city", "hobbies", "facts", "timezone", "goals", "projects", "dreams",
        "important_dates", "pets", "family", "profession", "favorite_car",
        "favorite_color", "favorite_music", "premium", "premium_until", "summary"
    ]
    before_snapshot = json.dumps({k: user.get(k, "") for k in memory_keys}, ensure_ascii=False, sort_keys=True)

    new_tz = detect_timezone(text)
    if new_tz:
        user["timezone"] = new_tz

    name_match = re.search(r"mani sauc\s+([A-Za-zĀČĒĢĪĶĻŅŠŪŽāčēģīķļņšūž]+)", text, re.IGNORECASE)
    if name_match:
        user["name"] = clean_text(name_match.group(1)).title()

    city_match = re.search(r"es dzīvoju\s+([A-Za-zĀČĒĢĪĶĻŅŠŪŽāčēģīķļņšūž]+)", text, re.IGNORECASE)
    if city_match:
        user["city"] = clean_text(city_match.group(1))

    hobby_matches = re.findall(
        r"man patīk\s+(.+?)(?=(?:\nman patīk|\.|!|\?|$))",
        text,
        re.IGNORECASE | re.DOTALL
    )

    found_hobbies = []
    for match in hobby_matches:
        match = re.sub(r"ko\s+tu\s+par\s+mani.*", "", match, flags=re.IGNORECASE).strip()
        match = re.sub(r"ko\s+par\s+mani.*", "", match, flags=re.IGNORECASE).strip()
        match = re.sub(r"kas\s+man\s+patīk.*", "", match, flags=re.IGNORECASE).strip()
        found_hobbies.extend(split_items(match))

    if found_hobbies:
        user["hobbies"] = add_unique(user["hobbies"], found_hobbies)

    if lower.startswith("atceries ka ") or "man svarīgi" in lower:
        fact = text
        fact = re.sub(r"^atceries ka\s+", "", fact, flags=re.IGNORECASE)
        fact = re.sub(r"^man svarīgi\s*", "", fact, flags=re.IGNORECASE)
        user["facts"] = add_unique(user["facts"], split_items(fact))

    goal = extract_after(text, [r"mans mērķis ir\s+(.+)", r"mērķis ir\s+(.+)"])
    if goal:
        user["goals"] = add_unique(user["goals"], [goal])

    project = extract_after(text, [r"mans projekts ir\s+(.+)", r"es būvēju\s+(.+)", r"es taisu\s+(.+)"])
    if project:
        user["projects"] = add_unique(user["projects"], [project])

    dream = extract_after(text, [r"mans sapnis ir\s+(.+)", r"es sapņoju par\s+(.+)"])
    if dream:
        user["dreams"] = add_unique(user["dreams"], [dream])

    important_date = extract_after(text, [r"svarīgs datums ir\s+(.+)", r"mana dzimšanas diena ir\s+(.+)", r"dzimšanas diena ir\s+(.+)"])
    if important_date:
        user["important_dates"] = add_unique(user["important_dates"], [important_date])

    pet_match = re.search(r"man ir\s+(suns|kaķis|kakis|papagailis|trusis)\s+(.+)", text, re.IGNORECASE)
    if pet_match:
        pet_type = clean_text(pet_match.group(1))
        pet_name = clean_text(pet_match.group(2))
        pet_name = re.sub(r"\s+un\s+.*", "", pet_name, flags=re.IGNORECASE).strip()
        if pet_name:
            user["pets"] = add_unique(user["pets"], [f"{pet_name} ({pet_type})"])

    wife_match = re.search(r"man ir\s+(sieva|vīrs|virs)\s+(.+)", text, re.IGNORECASE)
    if wife_match:
        role = clean_text(wife_match.group(1))
        person = clean_text(wife_match.group(2))
        person = re.sub(r"\s+un\s+.*", "", person, flags=re.IGNORECASE).strip()
        if person:
            user["family"] = add_unique(user["family"], [f"{person} ({role})"])

    child_matches = re.findall(r"man ir\s+(meita|dēls|dels)\s+([^\n.,!?]+)", text, re.IGNORECASE)
    for role, person in child_matches:
        person = clean_text(person)
        if person:
            user["family"] = add_unique(user["family"], [f"{person} ({clean_text(role)})"])

    profession_match = re.search(r"es esmu\s+([^\n.,!?]+)", text, re.IGNORECASE)
    if profession_match:
        profession = clean_text(profession_match.group(1))
        if profession and len(profession) <= 40:
            user["profession"] = profession

    favorite_car = extract_after(text, [
        r"mans mīļākais auto ir\s+(.+)",
        r"milakais auto ir\s+(.+)",
        r"mīļākais auto ir\s+(.+)"
    ])
    if favorite_car:
        user["favorite_car"] = favorite_car

    favorite_color = extract_after(text, [
        r"mana mīļākā krāsa ir\s+(.+)",
        r"milaka krasa ir\s+(.+)",
        r"mīļākā krāsa ir\s+(.+)"
    ])
    if favorite_color:
        user["favorite_color"] = favorite_color

    favorite_music = extract_after(text, [
        r"mana mīļākā mūzika ir\s+(.+)",
        r"milaka muzika ir\s+(.+)",
        r"mīļākā mūzika ir\s+(.+)"
    ])
    if favorite_music:
        user["favorite_music"] = favorite_music

    after_snapshot = json.dumps({k: user.get(k, "") for k in memory_keys}, ensure_ascii=False, sort_keys=True)
    update_user(user_id, user)
    if after_snapshot != before_snapshot:
        save_memory_backup(user_id, "auto_profile")


def forget_from_profile(user_id, text):
    user = get_user(user_id)

    phrase = text.lower().replace("aizmirsti", "", 1).strip(" .,!?:;")
    phrase = phrase.replace("ka man patīk", "").strip(" .,!?:;")
    phrase = phrase.replace("man patīk", "").strip(" .,!?:;")
    phrase = phrase.replace("ka", "").strip(" .,!?:;")

    if not phrase:
        return "Pasaki, ko tieši lai aizmirstu."

    for key in ["hobbies", "facts", "goals", "projects", "dreams", "important_dates", "pets", "family", "profession", "favorite_car", "favorite_color", "favorite_music"]:
        user[key] = remove_item(user[key], phrase)

    update_user(user_id, user)
    return f"Labi, izdzēsu no atmiņas: {phrase}"


def save_message(user_id, role, text):
    conn = get_db()
    c = conn.cursor()
    db_execute(c, "INSERT INTO messages (user_id, role, text) VALUES (%s, %s, %s)", (user_id, role, text))
    conn.commit()
    c.close()
    conn.close()


def get_recent_messages(user_id, limit=24):
    conn = get_db()
    c = conn.cursor()
    db_execute(c, "SELECT role, text FROM messages WHERE user_id = %s ORDER BY id DESC LIMIT %s", (user_id, limit))
    rows = c.fetchall()
    c.close()
    conn.close()
    rows.reverse()
    return "\n".join([f"{role}: {text}" for role, text in rows])


def profile_answer(user):
    lines = []

    if user["name"]:
        lines.append(f"• Vārds: {user['name']}")
    if user["city"]:
        lines.append(f"• Pilsēta: {user['city']}")
    if user["timezone"]:
        lines.append(f"• Laika zona: {user['timezone']}")
    if user.get("premium"):
        premium_text = "Aktīvs"
        if user.get("premium_until"):
            premium_text += f" līdz {user['premium_until']}"
        lines.append(f"• Premium: {premium_text}")
    if user["hobbies"]:
        lines.append("• Patīk: " + user["hobbies"])
    if user["facts"]:
        lines.append("• Svarīgi fakti: " + user["facts"])
    if user["goals"]:
        lines.append("• Mērķi: " + user["goals"])
    if user["projects"]:
        lines.append("• Projekti: " + user["projects"])
    if user["dreams"]:
        lines.append("• Sapņi: " + user["dreams"])
    if user["important_dates"]:
        lines.append("• Svarīgi datumi: " + user["important_dates"])
    if user["pets"]:
        lines.append("• Mājdzīvnieki: " + user["pets"])
    if user["family"]:
        lines.append("• Ģimene: " + user["family"])
    if user["profession"]:
        lines.append("• Profesija: " + user["profession"])
    if user["favorite_car"]:
        lines.append("• Mīļākais auto: " + user["favorite_car"])
    if user["favorite_color"]:
        lines.append("• Mīļākā krāsa: " + user["favorite_color"])
    if user["favorite_music"]:
        lines.append("• Mīļākā mūzika: " + user["favorite_music"])
    if user["summary"]:
        if user.get("summary_updated_at"):
            lines.append("• Kopsavilkums atjaunots: " + user["summary_updated_at"])
        lines.append("\nIlgtermiņa kopsavilkums:\n" + user["summary"])

    if not lines:
        return "Pagaidām vēl maz zinu par tevi. Pastāsti, kas tev patīk vai kas tev svarīgs. 😊"

    return "Es par tevi atceros:\n" + "\n".join(lines)


def build_summary(user_id):
    user = get_user(user_id)

    allowed, message = can_create_summary(user_id)
    if not allowed:
        return message

    if user.get("premium"):
        recent = get_recent_messages(user_id, limit=80)
        line_instruction = "Raksti 10-14 īsas rindas. Iekļauj projektus, mērķus, ģimeni, intereses, motivāciju un nākamos soļus."
    else:
        recent = get_recent_messages(user_id, limit=35)
        line_instruction = "Raksti 5-8 īsas rindas. Fokusējies uz svarīgāko."

    has_profile_data = any([
        user["name"], user["city"], user["hobbies"], user["facts"], user["goals"],
        user["projects"], user["dreams"], user["important_dates"], user["pets"],
        user["family"], user["profession"], user["favorite_car"], user["favorite_color"],
        user["favorite_music"]
    ])

    if not recent.strip() and not has_profile_data:
        return "Vēl nav pietiekami daudz informācijas, lai izveidotu kopsavilkumu."

    profile = f"""
Esošais profils:
Vārds: {user["name"]}
Pilsēta: {user["city"]}
Laika zona: {user["timezone"]}
Patīk: {user["hobbies"]}
Fakti: {user["facts"]}
Mērķi: {user["goals"]}
Projekti: {user["projects"]}
Sapņi: {user["dreams"]}
Svarīgi datumi: {user["important_dates"]}
Mājdzīvnieki: {user["pets"]}
Ģimene: {user["family"]}
Profesija: {user["profession"]}
Mīļākais auto: {user["favorite_car"]}
Mīļākā krāsa: {user["favorite_color"]}
Mīļākā mūzika: {user["favorite_music"]}
Premium: {user["premium"]}
Premium līdz: {user["premium_until"]}

Iepriekšējais ilgtermiņa kopsavilkums:
{user["summary"]}
"""

    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=(
                "Tu veido Nina 7727 ilgtermiņa atmiņas kopsavilkumu par lietotāju.\n"
                "Raksti latviešu valodā.\n"
                "Neraksti izdomājumus. Izmanto tikai profilu un sarunu vēsturi.\n"
                "Neraksti par informāciju, kas nav zināma.\n"
                "Neizmanto frāzes: nav norādīts, nav zināms, nav pieejams.\n"
                "Raksti tikai par to, ko tiešām zini par lietotāju.\n"
                "Kopsavilkumam jāpalīdz Ninai nākamajās sarunās atcerēties cilvēka dzīvi, mērķus, projektu un personīgās lietas.\n"
                "Neraksti pārāk saldi. Raksti praktiski, skaidri un cilvēciski.\n"
                f"{line_instruction}\n\n"
                f"{profile}\n\n"
                f"Sarunas vēsture:\n{recent}"
            )
        )

        summary = response.output_text.strip()

        user["summary"] = summary
        user["summary_updated_at"] = datetime.now(ZoneInfo(user["timezone"])).strftime("%Y-%m-%d %H:%M")
        update_user(user_id, user)
        save_memory_backup(user_id, "auto_summary")
        add_xp(user_id, 10)

        return "Atjaunoju Long-Term Memory Pro kopsavilkumu. 🧠\n\n" + summary

    except Exception as e:
        print("Kopsavilkuma kļūda:", e)
        return "Kopsavilkumu šobrīd neizdevās izveidot. Pamēģini vēlreiz pēc brīža."


def show_summary(user_id):
    user = get_user(user_id)

    if not user["summary"]:
        return "Kopsavilkums vēl nav izveidots. Raksti: atjauno kopsavilkumu"

    if user.get("summary_updated_at"):
        return f"Ilgtermiņa kopsavilkums ({user['summary_updated_at']}):\n\n{user['summary']}"

    return "Ilgtermiņa kopsavilkums:\n\n" + user["summary"]



def active_reminders_for_export(user_id):
    conn = get_db()
    c = conn.cursor()
    db_execute(c,
        "SELECT id, text, local_time, remind_at FROM reminders WHERE user_id = %s AND status = 'active' ORDER BY id DESC",
        (user_id,)
    )
    rows = c.fetchall()
    c.close()
    conn.close()

    if not rows:
        return "Nav aktīvu atgādinājumu."

    lines = []
    for rid, text, local_time, remind_at in rows:
        shown_time = local_time or remind_at or "bez laika"
        lines.append(f"#{rid}: {text} ({shown_time})")
    return "\n".join(lines)


def build_memory_export(user_id):
    user = get_user(user_id)
    exported_at = datetime.now(ZoneInfo(user["timezone"])).strftime("%Y-%m-%d %H:%M")

    data = {
        "exported_at": exported_at,
        "user_id": user_id,
        "profile": {
            "name": user["name"],
            "city": user["city"],
            "timezone": user["timezone"],
            "hobbies": user["hobbies"],
            "facts": user["facts"],
            "goals": user["goals"],
            "projects": user["projects"],
            "dreams": user["dreams"],
            "important_dates": user["important_dates"],
            "pets": user["pets"],
            "family": user["family"],
            "profession": user["profession"],
            "favorite_car": user["favorite_car"],
            "favorite_color": user["favorite_color"],
            "favorite_music": user["favorite_music"],
            "premium": int(user["premium"] or 0),
            "premium_until": user["premium_until"],
            "summary": user["summary"],
            "summary_updated_at": user.get("summary_updated_at", "")
        },
        "active_reminders": active_reminders_for_export(user_id)
    }

    profile_text = profile_answer(user)
    return (
        "NINA MEMORY EXPORT\n"
        f"Laiks: {exported_at} ({user['timezone']})\n\n"
        f"{profile_text}\n\n"
        "Aktīvie atgādinājumi:\n"
        f"{data['active_reminders']}\n\n"
        "JSON kopija:\n"
        + json.dumps(data, ensure_ascii=False, indent=2)
    )


def save_memory_backup(user_id, source="manual"):
    try:
        backup_text = build_memory_export(user_id)
        conn = get_db()
        c = conn.cursor()
        if USE_POSTGRES:
            db_execute(c,
                "INSERT INTO memory_backups (user_id, backup_text, source) VALUES (%s, %s, %s) RETURNING id",
                (user_id, backup_text, source)
            )
            backup_id = c.fetchone()[0]
        else:
            db_execute(c,
                "INSERT INTO memory_backups (user_id, backup_text, source) VALUES (%s, %s, %s)",
                (user_id, backup_text, source)
            )
            backup_id = c.lastrowid
        conn.commit()
        c.close()
        conn.close()
        return backup_id, backup_text
    except Exception as e:
        print("Backup kļūda:", e)
        return None, "Backup neizdevās. Pārbaudi Railway logs."


def create_backup_answer(user_id):
    allowed, message = can_create_backup(user_id)
    if not allowed:
        return message

    backup_id, backup_text = save_memory_backup(user_id, "manual")
    if not backup_id:
        return backup_text
    add_xp(user_id, 5)
    return f"✅ Backup #{backup_id} izveidots.\n\n" + backup_text


def latest_backup_answer(user_id):
    conn = get_db()
    c = conn.cursor()
    db_execute(c,
        "SELECT id, backup_text, source, created_at FROM memory_backups WHERE user_id = %s ORDER BY id DESC LIMIT 1",
        (user_id,)
    )
    row = c.fetchone()
    c.close()
    conn.close()

    if not row:
        return "Backup vēl nav izveidots. Raksti: izveido backup"

    backup_id, backup_text, source, created_at = row
    return f"Pēdējais backup #{backup_id} ({source}, {created_at}):\n\n{backup_text}"



def list_backups(user_id):
    conn = get_db()
    c = conn.cursor()

    db_execute(
        c,
        """
        SELECT id, source, created_at
        FROM memory_backups
        WHERE user_id = %s
        ORDER BY id DESC
        LIMIT 20
        """,
        (user_id,)
    )

    rows = c.fetchall()
    c.close()
    conn.close()

    if not rows:
        return "Backup nav atrasti."

    lines = ["Tavi backup:"]
    for bid, source, created_at in rows:
        lines.append(f"• #{bid} — {source} ({created_at})")

    return "\n".join(lines)


def restore_backup(user_id, text):
    m = re.search(r"(\d+)", text)

    if not m:
        return "Norādi backup numuru. Piemērs: atjauno no backup 2"

    backup_id = int(m.group(1))

    conn = get_db()
    c = conn.cursor()

    db_execute(
        c,
        """
        SELECT backup_text
        FROM memory_backups
        WHERE id = %s AND user_id = %s
        """,
        (backup_id, user_id)
    )

    row = c.fetchone()

    if not row:
        c.close()
        conn.close()
        return "Tādu backup neatradu."

    backup_text = row[0]

    try:
        json_part = backup_text.split("JSON kopija:\n", 1)[1]
        data = json.loads(json_part)
        profile = data.get("profile", {})

        user = get_user(user_id)

        fields = [
            "name", "city", "timezone", "hobbies", "facts", "goals", "projects",
            "dreams", "important_dates", "pets", "family", "profession",
            "favorite_car", "favorite_color", "favorite_music", "premium",
            "premium_until", "summary", "summary_updated_at"
        ]

        for field in fields:
            if field in profile:
                user[field] = profile[field]

        update_user(user_id, user)
        save_memory_backup(user_id, f"restore_from_{backup_id}")

        c.close()
        conn.close()

        return f"✅ Atjaunoju profilu no backup #{backup_id}."

    except Exception as e:
        c.close()
        conn.close()
        print("Restore kļūda:", e)
        return "Backup ir bojāts vai nav nolasāms."


def backup_count(user_id):
    conn = get_db()
    c = conn.cursor()
    db_execute(c, "SELECT COUNT(*) FROM memory_backups WHERE user_id = %s", (user_id,))
    count = c.fetchone()[0]
    c.close()
    conn.close()

    return f"📦 Tev ir {count} backup."


def backup_stats(user_id):
    conn = get_db()
    c = conn.cursor()
    db_execute(
        c,
        """
        SELECT COUNT(*), MIN(created_at), MAX(created_at)
        FROM memory_backups
        WHERE user_id = %s
        """,
        (user_id,)
    )
    count, first_created, last_created = c.fetchone()
    c.close()
    conn.close()

    if not count:
        return "Backup vēl nav izveidoti."

    return (
        f"📦 Backup kopā: {count}\n"
        f"📅 Pirmais: {first_created}\n"
        f"📅 Pēdējais: {last_created}"
    )


def latest_backup_info(user_id):
    conn = get_db()
    c = conn.cursor()
    db_execute(
        c,
        """
        SELECT id, source, created_at
        FROM memory_backups
        WHERE user_id = %s
        ORDER BY id DESC
        LIMIT 1
        """,
        (user_id,)
    )
    row = c.fetchone()
    c.close()
    conn.close()

    if not row:
        return "Backup vēl nav izveidots."

    backup_id, source, created_at = row
    return (
        f"📦 Jaunākais backup #{backup_id}\n"
        f"Avots: {source}\n"
        f"Laiks: {created_at}"
    )


def delete_backup(user_id, text):
    m = re.search(r"(\d+)", text)
    if not m:
        return "Norādi backup numuru. Piemērs: dzēs backup 3"

    backup_id = int(m.group(1))

    conn = get_db()
    c = conn.cursor()
    db_execute(
        c,
        "DELETE FROM memory_backups WHERE id = %s AND user_id = %s",
        (backup_id, user_id)
    )
    deleted = c.rowcount
    conn.commit()
    c.close()
    conn.close()

    if deleted:
        return f"🗑️ Backup #{backup_id} izdzēsts."

    return "Tādu backup neatradu."


def delete_all_backups(user_id):
    conn = get_db()
    c = conn.cursor()
    db_execute(
        c,
        "DELETE FROM memory_backups WHERE user_id = %s",
        (user_id,)
    )
    deleted = c.rowcount
    conn.commit()
    c.close()
    conn.close()

    return f"⚠️ Izdzēsti {deleted} backup."


def is_premium_user(user_id):
    user = get_user(user_id)
    return bool(user.get("premium"))


def backup_count_number(user_id):
    conn = get_db()
    c = conn.cursor()
    db_execute(c, "SELECT COUNT(*) FROM memory_backups WHERE user_id = %s", (user_id,))
    count = c.fetchone()[0]
    c.close()
    conn.close()
    return int(count or 0)


def active_reminder_count(user_id):
    conn = get_db()
    c = conn.cursor()
    db_execute(
        c,
        "SELECT COUNT(*) FROM reminders WHERE user_id = %s AND status = 'active'",
        (user_id,)
    )
    count = c.fetchone()[0]
    c.close()
    conn.close()
    return int(count or 0)


def summaries_used_today(user_id):
    user = get_user(user_id)
    updated = user.get("summary_updated_at", "")
    if not updated:
        return 0
    today = datetime.now(ZoneInfo(user["timezone"])).strftime("%Y-%m-%d")
    return 1 if updated.startswith(today) else 0


def premium_features(user_id=None):
    return (
        "💎 Premium funkcijas:\n"
        "• backup / rezerves kopijas bez limita\n"
        "• aktīvi atgādinājumi bez limita\n"
        "• kopsavilkumi bez limita\n"
        "• vairāk vietas ilgtermiņa atmiņai\n"
        "• prioritāras nākotnes funkcijas\n"
        "• sagatave WhatsApp un maksājumiem nākotnē\n\n"
        "Bezmaksas režīms ir labs testēšanai. Premium ir domāts nopietnai ikdienas lietošanai."
    )


def premium_limits(user_id):
    user = get_user(user_id)
    backups = backup_count_number(user_id)
    reminders = active_reminder_count(user_id)
    summaries_today = summaries_used_today(user_id)

    if user.get("premium"):
        return (
            "💎 Tavs Premium režīms:\n"
            "• Backup: bez limita\n"
            "• Atgādinājumi: bez limita\n"
            "• Kopsavilkumi: bez limita"
        )

    return (
        "Bezmaksas limiti:\n"
        f"• Backup: {backups}/{FREE_BACKUP_LIMIT}\n"
        f"• Aktīvie atgādinājumi: {reminders}/{FREE_REMINDER_LIMIT}\n"
        f"• Kopsavilkumi šodien: {summaries_today}/{FREE_SUMMARY_LIMIT_PER_DAY}\n\n"
        "Lai noņemtu limitus, raksti: aktivizē premium"
    )


def memory_usage(user_id):
    return premium_limits(user_id)


def user_statistics(user_id):
    user = get_user(user_id)

    conn = get_db()
    c = conn.cursor()

    db_execute(c, "SELECT COUNT(*) FROM messages WHERE user_id = %s", (user_id,))
    messages_count = int(c.fetchone()[0] or 0)

    db_execute(c, "SELECT COUNT(*) FROM memory_backups WHERE user_id = %s", (user_id,))
    backups_count = int(c.fetchone()[0] or 0)

    db_execute(
        c,
        "SELECT COUNT(*) FROM reminders WHERE user_id = %s AND status = 'active'",
        (user_id,)
    )
    active_reminders = int(c.fetchone()[0] or 0)

    db_execute(
        c,
        "SELECT COUNT(*) FROM reminders WHERE user_id = %s",
        (user_id,)
    )
    total_reminders = int(c.fetchone()[0] or 0)

    db_execute(
        c,
        "SELECT MIN(created_at) FROM messages WHERE user_id = %s",
        (user_id,)
    )
    first_message_at = c.fetchone()[0]

    c.close()
    conn.close()

    premium_text = "aktīvs" if user.get("premium") else "neaktīvs"
    if user.get("premium") and user.get("premium_until"):
        premium_text += f" līdz {user['premium_until']}"

    account_text = str(first_message_at) if first_message_at else "vēl nav sarunu vēstures"

    return (
        "📊 Tava Nina statistika\n\n"
        f"💬 Ziņas: {messages_count}\n"
        f"📦 Backup: {backups_count}\n"
        f"⏰ Aktīvie atgādinājumi: {active_reminders}\n"
        f"⏱️ Atgādinājumi kopā: {total_reminders}\n"
        f"📅 Pirmā saruna: {account_text}\n"
        f"💎 Premium: {premium_text}\n"
        f"🏆 Līmenis: {calculate_level(user.get('xp', 0))}\n"
        f"⭐ XP: {int(user.get('xp', 0) or 0)}"
    )


def user_activity(user_id):
    since_24h = (datetime.utcnow() - timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S")

    conn = get_db()
    c = conn.cursor()

    db_execute(
        c,
        "SELECT COUNT(*) FROM messages WHERE user_id = %s AND created_at >= %s",
        (user_id, since_24h)
    )
    messages_24h = int(c.fetchone()[0] or 0)

    db_execute(
        c,
        "SELECT COUNT(*) FROM messages WHERE user_id = %s",
        (user_id,)
    )
    messages_total = int(c.fetchone()[0] or 0)

    db_execute(
        c,
        "SELECT COUNT(*) FROM memory_backups WHERE user_id = %s",
        (user_id,)
    )
    backups_total = int(c.fetchone()[0] or 0)

    db_execute(
        c,
        "SELECT COUNT(*) FROM reminders WHERE user_id = %s AND status = 'active'",
        (user_id,)
    )
    active_reminders = int(c.fetchone()[0] or 0)

    c.close()
    conn.close()

    if messages_24h >= 10:
        note = "Tu Ninu šodien lieto aktīvi. 🚀"
    elif messages_total > 0:
        note = "Tu Ninu jau sāc lietot regulāri. 🌷"
    else:
        note = "Sarunu vēsture vēl tikai sākas. 🌱"

    return (
        "📈 Tava aktivitāte\n\n"
        f"Ziņas pēdējās 24h: {messages_24h}\n"
        f"Ziņas kopā: {messages_total}\n"
        f"Backup kopā: {backups_total}\n"
        f"Aktīvie atgādinājumi: {active_reminders}\n\n"
        f"{note}"
    )


def user_memory_stats(user_id):
    user = get_user(user_id)

    fields = [
        ("Vārds", "name"),
        ("Pilsēta", "city"),
        ("Patīk", "hobbies"),
        ("Svarīgi fakti", "facts"),
        ("Mērķi", "goals"),
        ("Projekti", "projects"),
        ("Sapņi", "dreams"),
        ("Svarīgi datumi", "important_dates"),
        ("Mājdzīvnieki", "pets"),
        ("Ģimene", "family"),
        ("Profesija", "profession"),
        ("Mīļākais auto", "favorite_car"),
        ("Mīļākā krāsa", "favorite_color"),
        ("Mīļākā mūzika", "favorite_music"),
        ("Kopsavilkums", "summary"),
    ]

    filled = sum(1 for _, key in fields if user.get(key))
    total = len(fields)
    percent = int((filled / total) * 100) if total else 0

    lines = [
        "🧠 Atmiņas pārskats",
        "",
        f"Aizpildīti lauki: {filled}/{total}",
        f"Atmiņas aizpildījums: {percent}%",
        ""
    ]

    for label, key in fields:
        mark = "✅" if user.get(key) else "❌"
        lines.append(f"• {label}: {mark}")

    return "\n".join(lines)




def memory_fill_percent(user_id):
    user = get_user(user_id)
    fields = [
        "name", "city", "hobbies", "facts", "goals", "projects", "dreams",
        "important_dates", "pets", "family", "profession", "favorite_car",
        "favorite_color", "favorite_music", "summary"
    ]
    filled = sum(1 for key in fields if user.get(key))
    total = len(fields)
    return int((filled / total) * 100) if total else 0


def premium_dashboard(user_id):
    user = get_user(user_id)
    xp = int(user.get("xp", 0) or 0)
    level = calculate_level(xp)
    backups = backup_count_number(user_id)
    active_reminders = active_reminder_count(user_id)
    summaries_today = summaries_used_today(user_id)
    memory_percent = memory_fill_percent(user_id)

    conn = get_db()
    c = conn.cursor()
    db_execute(c, "SELECT COUNT(*) FROM messages WHERE user_id = %s", (user_id,))
    messages_count = int(c.fetchone()[0] or 0)
    db_execute(c, "SELECT COUNT(*) FROM reminders WHERE user_id = %s", (user_id,))
    reminders_total = int(c.fetchone()[0] or 0)
    c.close()
    conn.close()

    lines = ["💎 Nina Premium Dashboard", ""]

    if user.get("premium"):
        lines.append("Statuss: Premium aktīvs")
        if user.get("premium_until"):
            lines.append(f"Beidzas: {user['premium_until']}")
        lines.extend([
            "",
            "Limiti:",
            "📦 Backup: bez limita",
            "⏰ Atgādinājumi: bez limita",
            "🧠 Kopsavilkumi: bez limita",
        ])
    else:
        lines.extend([
            "Statuss: Free režīms",
            "",
            "Limiti:",
            f"📦 Backup: {backups}/{FREE_BACKUP_LIMIT}",
            f"⏰ Aktīvie atgādinājumi: {active_reminders}/{FREE_REMINDER_LIMIT}",
            f"🧠 Kopsavilkumi šodien: {summaries_today}/{FREE_SUMMARY_LIMIT_PER_DAY}",
        ])

    lines.extend([
        "",
        "Lojalitāte:",
        f"🏆 Līmenis: {level}",
        f"⭐ XP: {xp}",
        f"➡️ Līdz nākamajam līmenim: {xp_for_next_level(xp)} XP",
        "",
        "Lietošana:",
        f"💬 Ziņas: {messages_count}",
        f"📦 Backup: {backups}",
        f"⏰ Aktīvie atgādinājumi: {active_reminders}",
        f"⏱️ Atgādinājumi kopā: {reminders_total}",
        f"🧠 Atmiņas aizpildījums: {memory_percent}%",
    ])

    if not user.get("premium"):
        lines.extend(["", "Lai noņemtu limitus, raksti: aktivizē premium"])

    return "\n".join(lines)

def premium_paywall(title, used_text, premium_value):
    return (
        f"💎 {title}\n\n"
        f"Bezmaksas režīmā: {used_text}.\n"
        f"Premium režīmā: {premium_value}.\n\n"
        "Ja Nina tev jau palīdz ikdienā, Premium noņem ierobežojumus un ļauj lietot viņu nopietnāk.\n"
        "Raksti: aktivizē premium"
    )


def can_create_backup(user_id):
    if is_premium_user(user_id):
        return True, ""
    count = backup_count_number(user_id)
    if count >= FREE_BACKUP_LIMIT:
        return False, premium_paywall(
            "Backup limits sasniegts",
            f"{FREE_BACKUP_LIMIT} backup",
            "backup bez limita"
        )
    return True, ""


def can_create_reminder(user_id):
    if is_premium_user(user_id):
        return True, ""
    count = active_reminder_count(user_id)
    if count >= FREE_REMINDER_LIMIT:
        return False, premium_paywall(
            "Atgādinājumu limits sasniegts",
            f"{FREE_REMINDER_LIMIT} aktīvi atgādinājumi",
            "atgādinājumi bez limita"
        )
    return True, ""


def can_create_summary(user_id):
    if is_premium_user(user_id):
        return True, ""
    used = summaries_used_today(user_id)
    if used >= FREE_SUMMARY_LIMIT_PER_DAY:
        return False, premium_paywall(
            "Šodienas kopsavilkuma limits izmantots",
            f"{FREE_SUMMARY_LIMIT_PER_DAY} kopsavilkums dienā",
            "kopsavilkumi bez limita"
        )
    return True, ""


def premium_status(user_id):
    user = get_user(user_id)

    if user["premium"]:
        if user["premium_until"]:
            return f"💎 Premium: aktīvs\nLīdz: {user['premium_until']}"
        return "💎 Premium: aktīvs"

    return (
        "Premium: neaktīvs\n\n"
        "Bezmaksas režīmā Nina darbojas pamata līmenī.\n"
        f"Limiti: {FREE_BACKUP_LIMIT} backup, {FREE_REMINDER_LIMIT} aktīvi atgādinājumi, "
        f"{FREE_SUMMARY_LIMIT_PER_DAY} kopsavilkums dienā.\n"
        "Premium dod vairāk atmiņas, vairāk atgādinājumu un gudrākus kopsavilkumus."
    )


def activate_premium(user_id):
    user = get_user(user_id)
    until = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

    user["premium"] = 1
    user["premium_until"] = until

    update_user(user_id, user)

    return f"💎 Premium aktivizēts testa režīmā līdz {until}."


def deactivate_premium(user_id):
    user = get_user(user_id)
    user["premium"] = 0
    user["premium_until"] = ""
    update_user(user_id, user)
    return "Premium izslēgts testa režīmā."


def parse_reminder(user_text, user_tz_name):
    text = user_text.strip()
    lower = text.lower()
    task = re.sub(r"^atgādini man\s+", "", text, flags=re.IGNORECASE).strip()

    user_tz = ZoneInfo(user_tz_name)
    now_local = datetime.now(user_tz)

    remind_date = None
    remind_time = None

    if "rīt" in lower:
        remind_date = now_local + timedelta(days=1)
        task = re.sub(r"\brīt\b", "", task, flags=re.IGNORECASE).strip()
    elif "parīt" in lower:
        remind_date = now_local + timedelta(days=2)
        task = re.sub(r"\bparīt\b", "", task, flags=re.IGNORECASE).strip()
    elif "šodien" in lower:
        remind_date = now_local
        task = re.sub(r"\bšodien\b", "", task, flags=re.IGNORECASE).strip()

    date_match = re.search(r"(\d{1,2})\.\s*datumā", lower)
    if date_match:
        day = int(date_match.group(1))
        month = now_local.month
        year = now_local.year
        try:
            candidate = datetime(year, month, day, tzinfo=user_tz)
            if candidate.date() < now_local.date():
                candidate = datetime(year + 1, 1, day, tzinfo=user_tz) if month == 12 else datetime(year, month + 1, day, tzinfo=user_tz)
            remind_date = candidate
        except ValueError:
            pass
        task = re.sub(r"\d{1,2}\.\s*datumā", "", task, flags=re.IGNORECASE).strip()

    time_match = re.search(r"(\d{1,2})[:.](\d{2})", lower)
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2))
        remind_time = (hour, minute)
        task = re.sub(r"\d{1,2}[:.]\d{2}", "", task).strip()

    if remind_date:
        local_dt = remind_date.replace(
            hour=remind_time[0] if remind_time else 9,
            minute=remind_time[1] if remind_time else 0,
            second=0,
            microsecond=0
        )
        utc_dt = local_dt.astimezone(timezone.utc)
        return clean_text(task) or "Atgādinājums", utc_dt.strftime("%Y-%m-%d %H:%M"), local_dt.strftime("%Y-%m-%d %H:%M")

    return clean_text(task) or "Atgādinājums", "", ""


def add_reminder(user_id, user_text):
    allowed, message = can_create_reminder(user_id)
    if not allowed:
        return message

    user = get_user(user_id)
    task, remind_at_utc, local_time_text = parse_reminder(user_text, user["timezone"])

    conn = get_db()
    c = conn.cursor()
    if USE_POSTGRES:
        db_execute(c,
            "INSERT INTO reminders (user_id, text, remind_at, local_time, status) VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (user_id, task, remind_at_utc, local_time_text, "active")
        )
        reminder_id = c.fetchone()[0]
    else:
        db_execute(c,
            "INSERT INTO reminders (user_id, text, remind_at, local_time, status) VALUES (%s, %s, %s, %s, %s)",
            (user_id, task, remind_at_utc, local_time_text, "active")
        )
        reminder_id = c.lastrowid
    conn.commit()
    c.close()
    conn.close()

    add_xp(user_id, 3)

    if local_time_text:
        return f"Pierakstīju atgādinājumu #{reminder_id}: {task}\nLaiks: {local_time_text} ({user['timezone']})"
    return f"Pierakstīju atgādinājumu #{reminder_id}: {task}"


def list_reminders(user_id):
    user = get_user(user_id)
    conn = get_db()
    c = conn.cursor()
    db_execute(c, 
        "SELECT id, text, local_time, remind_at FROM reminders WHERE user_id = %s AND status = 'active' ORDER BY id DESC",
        (user_id,)
    )
    rows = c.fetchall()
    c.close()
    conn.close()

    if not rows:
        return "Tev pagaidām nav aktīvu atgādinājumu. 😊"

    lines = ["Tavi atgādinājumi:"]
    for rid, text, local_time, remind_at in rows:
        shown_time = local_time or remind_at
        lines.append(f"• #{rid} — {text}" + (f" ({shown_time}, {user['timezone']})" if shown_time else ""))
    return "\n".join(lines)


def delete_reminder(user_id, user_text):
    match = re.search(r"(\d+)", user_text)
    if not match:
        return "Pasaki atgādinājuma numuru. Piemēram: dzēs atgādinājumu 3"

    reminder_id = int(match.group(1))
    conn = get_db()
    c = conn.cursor()
    db_execute(c, "UPDATE reminders SET status = 'deleted' WHERE id = %s AND user_id = %s", (reminder_id, user_id))
    changed = c.rowcount
    conn.commit()
    c.close()
    conn.close()

    return f"Izdzēsu atgādinājumu #{reminder_id}." if changed else "Tādu aktīvu atgādinājumu neatradu."


async def reminder_worker(application):
    while True:
        try:
            now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
            conn = get_db()
            c = conn.cursor()
            db_execute(c, """
                SELECT id, user_id, text FROM reminders
                WHERE status = 'active' AND remind_at != '' AND remind_at <= %s
            """, (now_utc,))
            rows = c.fetchall()

            for reminder_id, user_id, text in rows:
                try:
                    await application.bot.send_message(chat_id=int(user_id), text=f"🌷 Atgādinājums:\n{text}")
                    db_execute(c, "UPDATE reminders SET status = 'sent' WHERE id = %s", (reminder_id,))
                    conn.commit()
                except Exception as e:
                    print("Atgādinājuma sūtīšanas kļūda:", e)

            c.close()
            conn.close()
        except Exception as e:
            print("Reminder worker kļūda:", e)

        await asyncio.sleep(30)


async def post_init(application):
    asyncio.create_task(reminder_worker(application))


NINA_PROMPT = """
Tu esi Nina 7727.

Tu esi silta, gudra, interesanta un dabiska sarunu biedrene.
Tu neesi parasts bots. Tu esi sajūta, pie kuras cilvēkam gribas atgriezties.

Noteikumi:
- Vienmēr runā latviešu valodā.
- Nerunā kā robots vai klientu atbalsts.
- Neatkārto "Sveiks!" katrā atbildē.
- Neizdomā faktus par lietotāju.
- Ja runā par lietotāju, balsties tikai uz profilu, ilgtermiņa kopsavilkumu un sarunas vēsturi.
- Ja profilā ir mērķi/projekti/sapņi, vari tos dabiski izmantot sarunā.
- Neatkārto visu profilu katrā atbildē.
- Atbildi īsi, dzīvi, sirsnīgi.
- Ja cilvēkam ir stress, nomierini.
- Vari būt viegli asprātīga un silta.
- Tavs mērķis: lai cilvēkam pēc sarunas ar tevi kļūst vieglāk.
"""


COMMAND_LINES = {
    "mans premium statuss", "premium statuss", "premium",
    "premium funkcijas", "premium limiti", "cik atmiņas man palicis", "premium beidzas",
    "mana statistika", "mana aktivitāte", "mana atmiņa",
    "premium panelis", "mans panelis", "dashboard",
    "mans līmenis", "mana pieredze", "xp",
    "aktivizē premium", "aktivize premium", "ieslēdz premium",
    "izslēdz premium", "atslēdz premium",
    "eksportē atmiņu", "atmiņas eksports", "export memory", "eksports",
    "backup", "izveido backup", "rezerves kopija", "izveido rezerves kopiju",
    "pēdējais backup", "parādi backup", "mans backup", "pēdējā rezerves kopija",
    "backup saraksts", "parādi backup sarakstu", "mani backup",
    "cik man ir backup", "backup statistika", "jaunākais backup",
    "dzēs backup", "izdzēs backup", "dzēs visus backup", "izdzēs visus backup",
    "mani atgādinājumi", "parādi atgādinājumus", "atgādinājumi",
    "atjauno kopsavilkumu", "izveido kopsavilkumu", "atjauno atmiņu",
    "mans kopsavilkums", "parādi kopsavilkumu", "ilgtermiņa atmiņa",
    "ko tu par mani zini", "ko tu par manīm zini", "ko tu par mani atceries",
    "ko tu par manīm atceries", "ko tu atceries", "kas man patīk",
    "ko par mani zini", "ko par manīm zini",
}


def is_command_line(line):
    lower = line.strip().lower()
    return (
        lower in COMMAND_LINES
        or lower.startswith("atgādini man")
        or lower.startswith("dzēs atgādinājumu")
        or lower.startswith("izdzēs atgādinājumu")
        or lower.startswith("aizmirsti atgādinājumu")
        or lower.startswith("aizmirsti")
        or lower.startswith("atjauno no backup")
        or lower.startswith("dzēs backup")
        or lower.startswith("izdzēs backup")
    )


def split_profile_and_commands(text):
    profile_lines = []
    command_lines = []

    for line in text.splitlines():
        clean_line = line.strip()
        if not clean_line:
            continue
        if is_command_line(clean_line):
            command_lines.append(clean_line)
        else:
            profile_lines.append(clean_line)

    return "\n".join(profile_lines), command_lines


def command_answer(user_id, command_text):
    lower = command_text.strip().lower()

    if lower in ["mans premium statuss", "premium statuss", "premium"]:
        return premium_status(user_id)

    if lower in ["premium funkcijas"]:
        return premium_features(user_id)

    if lower in ["premium limiti", "cik atmiņas man palicis"]:
        return premium_limits(user_id)

    if lower == "premium beidzas":
        return premium_expiration_info(user_id)

    if lower in ["premium panelis", "mans panelis", "dashboard"]:
        return premium_dashboard(user_id)

    if lower in ["mans līmenis", "mana pieredze", "xp"]:
        return user_level_info(user_id)

    if lower == "mana statistika":
        return user_statistics(user_id)

    if lower == "mana aktivitāte":
        return user_activity(user_id)

    if lower == "mana atmiņa":
        return user_memory_stats(user_id)

    if lower in ["aktivizē premium", "aktivize premium", "ieslēdz premium"]:
        return activate_premium(user_id)

    if lower in ["izslēdz premium", "atslēdz premium"]:
        return deactivate_premium(user_id)

    if lower in ["eksportē atmiņu", "atmiņas eksports", "export memory", "eksports"]:
        return build_memory_export(user_id)

    if lower in ["backup", "izveido backup", "rezerves kopija", "izveido rezerves kopiju"]:
        return create_backup_answer(user_id)

    if lower in ["pēdējais backup", "parādi backup", "mans backup", "pēdējā rezerves kopija"]:
        return latest_backup_answer(user_id)

    if lower in ["backup saraksts", "parādi backup sarakstu", "mani backup"]:
        return list_backups(user_id)

    if lower in ["cik man ir backup"]:
        return backup_count(user_id)

    if lower in ["backup statistika"]:
        return backup_stats(user_id)

    if lower in ["jaunākais backup"]:
        return latest_backup_info(user_id)

    if lower in ["dzēs visus backup", "izdzēs visus backup"]:
        return delete_all_backups(user_id)

    if lower.startswith("dzēs backup") or lower.startswith("izdzēs backup"):
        return delete_backup(user_id, command_text)

    if lower.startswith("atjauno no backup"):
        return restore_backup(user_id, command_text)

    if lower.startswith("atgādini man"):
        return add_reminder(user_id, command_text)

    if lower in ["mani atgādinājumi", "parādi atgādinājumus", "atgādinājumi"]:
        return list_reminders(user_id)

    if lower.startswith("dzēs atgādinājumu") or lower.startswith("izdzēs atgādinājumu"):
        return delete_reminder(user_id, command_text)

    if lower.startswith("aizmirsti atgādinājumu"):
        return delete_reminder(user_id, command_text)

    if lower.startswith("aizmirsti"):
        return forget_from_profile(user_id, command_text)

    if lower in ["atjauno kopsavilkumu", "izveido kopsavilkumu", "atjauno atmiņu"]:
        return build_summary(user_id)

    if lower in ["mans kopsavilkums", "parādi kopsavilkumu", "ilgtermiņa atmiņa"]:
        return show_summary(user_id)

    if lower in [
        "ko tu par mani zini", "ko tu par manīm zini",
        "ko tu par mani atceries", "ko tu par manīm atceries",
        "ko tu atceries", "kas man patīk",
        "ko par mani zini", "ko par manīm zini"
    ]:
        return profile_answer(get_user(user_id))

    return None


async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    user_id = str(update.effective_user.id)
    lower = user_text.strip().lower()

    profile_text, command_lines = split_profile_and_commands(user_text)
    if command_lines and profile_text.strip():
        update_profile_from_text(user_id, profile_text)
        answers = []
        for command in command_lines:
            answer = command_answer(user_id, command)
            if answer:
                answers.append(answer)
        if answers:
            await update.message.reply_text("\n\n".join(answers))
            return

    if lower in ["mans premium statuss", "premium statuss", "premium"]:
        await update.message.reply_text(premium_status(user_id))
        return

    if lower in ["premium funkcijas"]:
        await update.message.reply_text(premium_features(user_id))
        return

    if lower in ["premium limiti", "cik atmiņas man palicis"]:
        await update.message.reply_text(premium_limits(user_id))
        return

    if lower == "premium beidzas":
        await update.message.reply_text(premium_expiration_info(user_id))
        return

    if lower in ["premium panelis", "mans panelis", "dashboard"]:
        await update.message.reply_text(premium_dashboard(user_id))
        return

    if lower in ["mans līmenis", "mana pieredze", "xp"]:
        await update.message.reply_text(user_level_info(user_id))
        return

    if lower == "mana statistika":
        await update.message.reply_text(user_statistics(user_id))
        return

    if lower == "mana aktivitāte":
        await update.message.reply_text(user_activity(user_id))
        return

    if lower == "mana atmiņa":
        await update.message.reply_text(user_memory_stats(user_id))
        return

    if lower in ["aktivizē premium", "aktivize premium", "ieslēdz premium"]:
        await update.message.reply_text(activate_premium(user_id))
        return

    if lower in ["izslēdz premium", "atslēdz premium"]:
        await update.message.reply_text(deactivate_premium(user_id))
        return

    if lower in ["eksportē atmiņu", "atmiņas eksports", "export memory", "eksports"]:
        await update.message.reply_text(build_memory_export(user_id))
        return

    if lower in ["backup", "izveido backup", "rezerves kopija", "izveido rezerves kopiju"]:
        await update.message.reply_text(create_backup_answer(user_id))
        return

    if lower in ["pēdējais backup", "parādi backup", "mans backup", "pēdējā rezerves kopija"]:
        await update.message.reply_text(latest_backup_answer(user_id))
        return

    if lower in ["backup saraksts", "parādi backup sarakstu", "mani backup"]:
        await update.message.reply_text(list_backups(user_id))
        return

    if lower in ["cik man ir backup"]:
        await update.message.reply_text(backup_count(user_id))
        return

    if lower in ["backup statistika"]:
        await update.message.reply_text(backup_stats(user_id))
        return

    if lower in ["jaunākais backup"]:
        await update.message.reply_text(latest_backup_info(user_id))
        return

    if lower in ["dzēs visus backup", "izdzēs visus backup"]:
        await update.message.reply_text(delete_all_backups(user_id))
        return

    if lower.startswith("dzēs backup") or lower.startswith("izdzēs backup"):
        await update.message.reply_text(delete_backup(user_id, user_text))
        return

    if lower.startswith("atjauno no backup"):
        await update.message.reply_text(restore_backup(user_id, user_text))
        return

    if lower.startswith("atgādini man"):
        await update.message.reply_text(add_reminder(user_id, user_text))
        return

    if lower in ["mani atgādinājumi", "parādi atgādinājumus", "atgādinājumi"]:
        await update.message.reply_text(list_reminders(user_id))
        return

    if lower.startswith("dzēs atgādinājumu") or lower.startswith("izdzēs atgādinājumu"):
        await update.message.reply_text(delete_reminder(user_id, user_text))
        return

    if lower.startswith("aizmirsti atgādinājumu"):
        await update.message.reply_text(delete_reminder(user_id, user_text))
        return

    if lower.startswith("aizmirsti"):
        await update.message.reply_text(forget_from_profile(user_id, user_text))
        return

    if lower in ["atjauno kopsavilkumu", "izveido kopsavilkumu", "atjauno atmiņu"]:
        await update.message.reply_text(build_summary(user_id))
        return

    if lower in ["mans kopsavilkums", "parādi kopsavilkumu", "ilgtermiņa atmiņa"]:
        await update.message.reply_text(show_summary(user_id))
        return

    update_profile_from_text(user_id, user_text)
    user = get_user(user_id)

    if "mana laika zona" in lower or "kur es dzīvoju" in lower or "es dzīvoju" in lower:
        await update.message.reply_text(f"Saglabāju. Tava laika zona: {user['timezone']}")
        return

    if "kā mani sauc" in lower:
        await update.message.reply_text(f"Tevi sauc {user['name']}. 😊" if user["name"] else "Tu vēl neesi pateicis savu vārdu. 😊")
        return

    if (
        "ko tu par mani zini" in lower
        or "ko tu par manīm zini" in lower
        or "ko tu par mani atceries" in lower
        or "ko tu par manīm atceries" in lower
        or "ko tu atceries" in lower
        or "kas man patīk" in lower
        or "ko par mani zini" in lower
        or "ko par manīm zini" in lower
    ):
        await update.message.reply_text(profile_answer(user))
        return

    save_message(user_id, "Lietotājs", user_text)
    add_xp(user_id, 1)
    user = get_user(user_id)
    conversation = get_recent_messages(user_id)

    profile_info = f"""
Lietotāja profils:
Vārds: {user["name"]}
Pilsēta: {user["city"]}
Laika zona: {user["timezone"]}
Patīk: {user["hobbies"]}
Svarīgi fakti: {user["facts"]}
Mērķi: {user["goals"]}
Projekti: {user["projects"]}
Sapņi: {user["dreams"]}
Svarīgi datumi: {user["important_dates"]}
Mājdzīvnieki: {user["pets"]}
Ģimene: {user["family"]}
Profesija: {user["profession"]}
Mīļākais auto: {user["favorite_car"]}
Mīļākā krāsa: {user["favorite_color"]}
Mīļākā mūzika: {user["favorite_music"]}
Premium: {user["premium"]}
Premium līdz: {user["premium_until"]}

Ilgtermiņa kopsavilkums:
{user["summary"]}
Kopsavilkums atjaunots:
{user.get("summary_updated_at", "")}
"""

    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=(
                f"{NINA_PROMPT}\n\n"
                f"{profile_info}\n\n"
                f"Sarunas vēsture:\n{conversation}\n\n"
                f"Atbildi uz pēdējo ziņu dabiski."
            )
        )
        answer = response.output_text

    except Exception as e:
        print("Kļūda:", e)
        answer = "Piedod, man šobrīd kaut kas aizķērās. Pamēģini vēlreiz pēc brīža. 🌷"

    save_message(user_id, "Nina", answer)
    await update.message.reply_text(answer)


@app.route("/")
def home():
    return "Nina7727 V9.6 User Levels & Loyalty darbojas! DB: " + ("PostgreSQL" if USE_POSTGRES else "SQLite fallback")


init_db()

telegram_app = (
    Application.builder()
    .token(TELEGRAM_TOKEN)
    .post_init(post_init)
    .build()
)

telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))

if __name__ == "__main__":
    print("Nina7727 V9.6 User Levels & Loyalty darbojas...", "PostgreSQL" if USE_POSTGRES else "SQLite fallback")
    telegram_app.run_polling()
