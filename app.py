import os
import re
import json
import sqlite3
from datetime import datetime
from flask import Flask
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from openai import OpenAI

app = Flask(__name__)

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]

DB_PATH = "nina_memory.db"

def db():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            name TEXT,
            city TEXT,
            hobbies TEXT,
            facts TEXT,
            updated_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            role TEXT,
            text TEXT,
            created_at TEXT
        )
    """)

    conn.commit()
    conn.close()

def get_user(user_id):
    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT name, city, hobbies, facts FROM users WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()

    if not row:
        return {
            "name": None,
            "city": None,
            "hobbies": [],
            "facts": []
        }

    return {
        "name": row[0],
        "city": row[1],
        "hobbies": json.loads(row[2] or "[]"),
        "facts": json.loads(row[3] or "[]")
    }

def save_user(user_id, profile):
    conn = db()
    cur = conn.cursor()
    cur.execute("""
        INSERT OR REPLACE INTO users (user_id, name, city, hobbies, facts, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        profile.get("name"),
        profile.get("city"),
        json.dumps(profile.get("hobbies", []), ensure_ascii=False),
        json.dumps(profile.get("facts", []), ensure_ascii=False),
        datetime.utcnow().isoformat()
    ))
    conn.commit()
    conn.close()

def save_message(user_id, role, text):
    conn = db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO messages (user_id, role, text, created_at)
        VALUES (?, ?, ?, ?)
    """, (
        user_id,
        role,
        text,
        datetime.utcnow().isoformat()
    ))
    conn.commit()
    conn.close()

def get_recent_messages(user_id, limit=16):
    conn = db()
    cur = conn.cursor()
    cur.execute("""
        SELECT role, text FROM messages
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT ?
    """, (user_id, limit))
    rows = cur.fetchall()
    conn.close()

    rows.reverse()
    return "\n".join([f"{role}: {text}" for role, text in rows])

def add_unique(items, item):
    if item and item not in items:
        items.append(item)
    return items

def update_profile_from_text(profile, text):
    lower = text.lower()

    name_match = re.search(r"mani sauc\s+([A-Za-zĀČĒĢĪĶĻŅŠŪŽāčēģīķļņšūž]+)", text, re.IGNORECASE)
    if name_match:
        profile["name"] = name_match.group(1)

    city_match = re.search(r"(?:dzīvoju|es dzīvoju|esmu no)\s+([A-Za-zĀČĒĢĪĶĻŅŠŪŽāčēģīķļņšūž]+)", text, re.IGNORECASE)
    if city_match:
        profile["city"] = city_match.group(1)

    hobby_match = re.search(r"man patīk\s+(.+)", lower)
    if hobby_match:
        hobby = hobby_match.group(1).strip().replace(".", "")
        profile["hobbies"] = add_unique(profile.get("hobbies", []), hobby)

    if any(x in lower for x in ["atceries", "svarīgi", "neaizmirsti"]):
        fact = text.strip()
        profile["facts"] = add_unique(profile.get("facts", []), fact)

    return profile

NINA_PROMPT = """
Tu esi Nina 7727.

Tu esi silta, gudra un dabiska sarunu biedrene.

Raksturs:
- 70% draudzene
- 20% viegls humors
- 10% intuīcija un pašizziņa

Noteikumi:
- Vienmēr runā latviešu valodā.
- Nerunā kā asistents.
- Nerunā kā robots.
- Neatkārto "Sveiks!" katrā atbildē.
- Sveicienu lieto tikai sarunas sākumā.
- Neuzrunā lietotāju sieviešu vai vīriešu dzimtē, ja dzimums nav zināms.
- Nemin numeroloģiju, ja lietotājs to neprasa.
- Ja lietotājs saka "vēl", "jā", "turpini", izmanto sarunas vēsturi.
- Ja zini lietotāja vārdu, vari viņu reizēm uzrunāt vārdā.
- Atbildi īsi, silti, dzīvi un cilvēciski.
- Galvenais: lai cilvēkam ir sajūta, ka viņš runā ar dzīvu sarunu biedreni.
"""

async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    user_id = str(update.effective_user.id)

    profile = get_user(user_id)
    profile = update_profile_from_text(profile, user_text)
    save_user(user_id, profile)

    save_message(user_id, "Lietotājs", user_text)

    recent = get_recent_messages(user_id)

    profile_info = f"""
Lietotāja profils:
Vārds: {profile.get("name")}
Pilsēta: {profile.get("city")}
Hobiji: {profile.get("hobbies")}
Svarīgi fakti: {profile.get("facts")}
"""

    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=(
                f"{NINA_PROMPT}\n\n"
                f"{profile_info}\n\n"
                f"Sarunas vēsture:\n{recent}\n\n"
                f"Atbildi uz pēdējo lietotāja ziņu, ņemot vērā profilu un sarunas vēsturi."
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
    return "Nina7727 Memory darbojas!"

init_db()

telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()

telegram_app.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, reply)
)

if __name__ == "__main__":
    print("Nina7727 Memory SQLite darbojas...")
    telegram_app.run_polling()
