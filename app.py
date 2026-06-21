import os
import re
import sqlite3
import asyncio
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from flask import Flask
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from openai import OpenAI

app = Flask(__name__)

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]

DB_FILE = "nina_memory.db"
DEFAULT_TIMEZONE = "Europe/Riga"


def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            name TEXT,
            city TEXT,
            hobbies TEXT,
            facts TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            role TEXT,
            text TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            text TEXT,
            remind_at TEXT,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # pievieno timezone kolonnas, ja vecā datubāze tās vēl nepazīst
    try:
        c.execute("ALTER TABLE users ADD COLUMN timezone TEXT DEFAULT 'Europe/Riga'")
    except sqlite3.OperationalError:
        pass

    try:
        c.execute("ALTER TABLE reminders ADD COLUMN local_time TEXT")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()


def get_user(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("SELECT name, city, hobbies, facts, timezone FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()

    if not row:
        c.execute(
            "INSERT INTO users (user_id, name, city, hobbies, facts, timezone) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, "", "", "", "", DEFAULT_TIMEZONE)
        )
        conn.commit()
        row = ("", "", "", "", DEFAULT_TIMEZONE)

    conn.close()

    return {
        "name": row[0] or "",
        "city": row[1] or "",
        "hobbies": row[2] or "",
        "facts": row[3] or "",
        "timezone": row[4] or DEFAULT_TIMEZONE
    }


def update_user(user_id, name, city, hobbies, facts, tz_name):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "UPDATE users SET name = ?, city = ?, hobbies = ?, facts = ?, timezone = ? WHERE user_id = ?",
        (name, city, hobbies, facts, tz_name, user_id)
    )
    conn.commit()
    conn.close()


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

    country_map = {
        "latvijā": "Europe/Riga",
        "rīgā": "Europe/Riga",
        "amerika": "America/New_York",
        "amerikā": "America/New_York",
        "new york": "America/New_York",
        "ņujorkā": "America/New_York",
        "los angeles": "America/Los_Angeles",
        "krievijā": "Europe/Moscow",
        "maskavā": "Europe/Moscow",
        "anglijā": "Europe/London",
        "londonā": "Europe/London",
        "vācijā": "Europe/Berlin",
        "berlīnē": "Europe/Berlin",
    }

    for key, tz in country_map.items():
        if key in lower:
            return tz

    return None


def split_items(text):
    text = text.replace("\n", ",")
    text = text.replace(" arī", "")
    text = re.sub(r"\s+un\s+", ",", text, flags=re.IGNORECASE)
    parts = [x.strip(" .,!?:;") for x in text.split(",")]
    return [x for x in parts if x]


def add_unique(old_text, new_items):
    items = [x.strip() for x in old_text.split(",") if x.strip()]
    for item in new_items:
        item = item.strip(" .,!?:;")
        if item and item not in items:
            items.append(item)
    return ", ".join(items)


def remove_item(old_text, item_to_remove):
    items = [x.strip() for x in old_text.split(",") if x.strip()]
    item_to_remove = item_to_remove.strip(" .,!?:;").lower()
    return ", ".join([item for item in items if item.lower() != item_to_remove])


def clean_fact(text):
    text = text.strip(" .,!?:;")
    text = re.sub(r"^atceries ka\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^man svarīgi\s*", "", text, flags=re.IGNORECASE)
    return text.strip(" .,!?:;")


def split_facts(text):
    text = clean_fact(text)
    parts = re.split(r"\s+un\s+|\n|,", text)
    return [clean_fact(p) for p in parts if clean_fact(p)]


def update_profile_from_text(user_id, text):
    lower = text.lower()
    user = get_user(user_id)

    name = user["name"]
    city = user["city"]
    hobbies = user["hobbies"]
    facts = user["facts"]
    tz_name = user["timezone"]

    new_tz = detect_timezone(text)
    if new_tz:
        tz_name = new_tz

    name_match = re.search(r"mani sauc\s+([A-Za-zĀČĒĢĪĶĻŅŠŪŽāčēģīķļņšūž]+)", text, re.IGNORECASE)
    if name_match:
        name = name_match.group(1).strip(" .,!?:;")

    city_match = re.search(r"es dzīvoju\s+([A-Za-zĀČĒĢĪĶĻŅŠŪŽāčēģīķļņšūž]+)", text, re.IGNORECASE)
    if city_match:
        city = city_match.group(1).strip(" .,!?:;")

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
        hobbies = add_unique(hobbies, found_hobbies)

    if lower.startswith("atceries ka ") or "man svarīgi" in lower:
        facts = add_unique(facts, split_facts(text))

    update_user(user_id, name, city, hobbies, facts, tz_name)


def forget_from_profile(user_id, text):
    user = get_user(user_id)

    phrase = text.lower().replace("aizmirsti", "", 1).strip(" .,!?:;")
    phrase = phrase.replace("ka man patīk", "").strip(" .,!?:;")
    phrase = phrase.replace("man patīk", "").strip(" .,!?:;")
    phrase = phrase.replace("ka", "").strip(" .,!?:;")

    if not phrase:
        return "Pasaki, ko tieši lai aizmirstu."

    hobbies = remove_item(user["hobbies"], phrase)
    facts = remove_item(user["facts"], phrase)

    update_user(user_id, user["name"], user["city"], hobbies, facts, user["timezone"])

    return f"Labi, izdzēsu no atmiņas: {phrase}"


def save_message(user_id, role, text):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "INSERT INTO messages (user_id, role, text) VALUES (?, ?, ?)",
        (user_id, role, text)
    )
    conn.commit()
    conn.close()


def get_recent_messages(user_id, limit=20):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "SELECT role, text FROM messages WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (user_id, limit)
    )
    rows = c.fetchall()
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
    if user["hobbies"]:
        lines.append("• Patīk: " + user["hobbies"])
    if user["facts"]:
        facts = [x.strip() for x in user["facts"].split(",") if x.strip()]
        if facts:
            lines.append("• Svarīgi fakti:")
            for fact in facts:
                lines.append(f"  - {fact}")

    if not lines:
        return "Pagaidām vēl maz zinu par tevi. Pastāsti, kas tev patīk vai kas tev svarīgs. 😊"

    return "Es par tevi atceros:\n" + "\n".join(lines)


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
                if month == 12:
                    candidate = datetime(year + 1, 1, day, tzinfo=user_tz)
                else:
                    candidate = datetime(year, month + 1, day, tzinfo=user_tz)
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
        if remind_time:
            local_dt = remind_date.replace(hour=remind_time[0], minute=remind_time[1], second=0, microsecond=0)
        else:
            local_dt = remind_date.replace(hour=9, minute=0, second=0, microsecond=0)

        utc_dt = local_dt.astimezone(timezone.utc)
        remind_at_utc = utc_dt.strftime("%Y-%m-%d %H:%M")
        local_time_text = local_dt.strftime("%Y-%m-%d %H:%M")
    else:
        remind_at_utc = ""
        local_time_text = ""

    task = task.strip(" .,!?:;")

    if not task:
        task = "Atgādinājums"

    return task, remind_at_utc, local_time_text


def add_reminder(user_id, user_text):
    user = get_user(user_id)
    task, remind_at_utc, local_time_text = parse_reminder(user_text, user["timezone"])

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "INSERT INTO reminders (user_id, text, remind_at, local_time, status) VALUES (?, ?, ?, ?, ?)",
        (user_id, task, remind_at_utc, local_time_text, "active")
    )
    reminder_id = c.lastrowid
    conn.commit()
    conn.close()

    if local_time_text:
        return f"Pierakstīju atgādinājumu #{reminder_id}: {task}\nLaiks: {local_time_text} ({user['timezone']})"
    return f"Pierakstīju atgādinājumu #{reminder_id}: {task}"


def list_reminders(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "SELECT id, text, local_time, remind_at FROM reminders WHERE user_id = ? AND status = 'active' ORDER BY id DESC",
        (user_id,)
    )
    rows = c.fetchall()
    conn.close()

    if not rows:
        return "Tev pagaidām nav aktīvu atgādinājumu. 😊"

    user = get_user(user_id)
    lines = ["Tavi atgādinājumi:"]
    for rid, text, local_time, remind_at in rows:
        shown_time = local_time or remind_at
        if shown_time:
            lines.append(f"• #{rid} — {text} ({shown_time}, {user['timezone']})")
        else:
            lines.append(f"• #{rid} — {text}")

    return "\n".join(lines)


def delete_reminder(user_id, user_text):
    match = re.search(r"(\d+)", user_text)
    if not match:
        return "Pasaki atgādinājuma numuru. Piemēram: dzēs atgādinājumu 3"

    reminder_id = int(match.group(1))

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "UPDATE reminders SET status = 'deleted' WHERE id = ? AND user_id = ?",
        (reminder_id, user_id)
    )
    conn.commit()
    changed = c.rowcount
    conn.close()

    if changed:
        return f"Izdzēsu atgādinājumu #{reminder_id}."
    return "Tādu aktīvu atgādinājumu neatradu."


async def reminder_worker(application):
    while True:
        try:
            now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")

            conn = sqlite3.connect(DB_FILE)
            c = conn.cursor()
            c.execute(
                """
                SELECT id, user_id, text
                FROM reminders
                WHERE status = 'active'
                AND remind_at != ''
                AND remind_at <= ?
                """,
                (now_utc,)
            )
            rows = c.fetchall()

            for reminder_id, user_id, text in rows:
                try:
                    await application.bot.send_message(
                        chat_id=int(user_id),
                        text=f"🌷 Atgādinājums:\n{text}"
                    )

                    c.execute(
                        "UPDATE reminders SET status = 'sent' WHERE id = ?",
                        (reminder_id,)
                    )
                    conn.commit()

                except Exception as e:
                    print("Atgādinājuma sūtīšanas kļūda:", e)

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
- Ja runā par lietotāju, balsties tikai uz profilu un sarunas vēsturi.
- Atbildi īsi, dzīvi, sirsnīgi.
- Ja cilvēkam ir stress, nomierini.
- Vari būt viegli asprātīga un silta.
- Tavs mērķis: lai cilvēkam pēc sarunas ar tevi kļūst vieglāk.
"""


async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    user_id = str(update.effective_user.id)
    lower = user_text.lower()

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
    conversation = get_recent_messages(user_id)

    profile_info = f"""
Lietotāja profils:
Vārds: {user["name"]}
Pilsēta: {user["city"]}
Laika zona: {user["timezone"]}
Patīk: {user["hobbies"]}
Svarīgi fakti: {user["facts"]}
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
    return "Nina7727 darbojas!"


init_db()

telegram_app = (
    Application.builder()
    .token(TELEGRAM_TOKEN)
    .post_init(post_init)
    .build()
)

telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))

if __name__ == "__main__":
    print("Nina7727 V4.2 Global Time darbojas...")
    telegram_app.run_polling()
