import os
import sqlite3
from flask import Flask
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from openai import OpenAI

app = Flask(__name__)

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]

DB_FILE = "nina_memory.db"

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

    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("SELECT name, city, hobbies, facts FROM users WHERE user_id = ?", (user_id,))
    row = c.fetchone()

    if not row:
        c.execute(
            "INSERT INTO users (user_id, name, city, hobbies, facts) VALUES (?, ?, ?, ?, ?)",
            (user_id, "", "", "", "")
        )
        conn.commit()
        row = ("", "", "", "")

    conn.close()

    return {
        "name": row[0] or "",
        "city": row[1] or "",
        "hobbies": row[2] or "",
        "facts": row[3] or ""
    }

def save_message(user_id, role, text):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "INSERT INTO messages (user_id, role, text) VALUES (?, ?, ?)",
        (user_id, role, text)
    )
    conn.commit()
    conn.close()

def get_recent_messages(user_id, limit=14):
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

def update_profile_from_text(user_id, text):
    lower = text.lower()
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    user = get_user(user_id)

    name = user["name"]
    city = user["city"]
    hobbies = user["hobbies"]
    facts = user["facts"]

    if "mani sauc " in lower:
        name = text.split("mani sauc", 1)[1].strip().split()[0]

    if "es dzīvoju " in lower:
        city = text.split("es dzīvoju", 1)[1].strip().split()[0]

    if "man patīk " in lower:
        hobby = text.split("man patīk", 1)[1].strip()
        if hobby and hobby not in hobbies:
            hobbies = (hobbies + ", " + hobby).strip(", ")

    if any(word in lower for word in ["atceries", "man svarīgi", "svarīgi"]):
        if text not in facts:
            facts = (facts + " | " + text).strip(" | ")

    c.execute(
        "UPDATE users SET name = ?, city = ?, hobbies = ?, facts = ? WHERE user_id = ?",
        (name, city, hobbies, facts, user_id)
    )

    conn.commit()
    conn.close()

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
- Ja zini lietotāja vārdu, vari to reizēm izmantot dabiski.
- Atbildi īsi, silti, dzīvi un cilvēciski.
- Galvenais: lai cilvēkam ir sajūta, ka viņš runā ar dzīvu sarunu biedreni.
"""

async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    user_id = str(update.effective_user.id)

lower = user_text.lower()

if "ko tu par mani zini" in lower or "ko tu atceries" in lower:

    atbilde = "Es par tevi atceros:\n"

    if user["name"]:
        atbilde += f"• Vārds: {user['name']}\n"

    if user["city"]:
        atbilde += f"• Pilsēta: {user['city']}\n"

    if user["hobbies"]:
        atbilde += f"• Hobiji: {user['hobbies']}\n"

    if user["facts"]:
        atbilde += f"• Svarīgi fakti: {user['facts']}\n"

    if atbilde == "Es par tevi atceros:\n":
        atbilde += "Pagaidām vēl neko neesmu saglabājusi."

    await update.message.reply_text(atbilde)
    return
    save_message(user_id, "Lietotājs", user_text)

    conversation = get_recent_messages(user_id)

    profile_info = f"""
Lietotāja profils:
Vārds: {user["name"]}
Pilsēta: {user["city"]}
Hobiji: {user["hobbies"]}
Svarīgi fakti: {user["facts"]}
"""

    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=(
                f"{NINA_PROMPT}\n\n"
                f"{profile_info}\n\n"
                f"Sarunas vēsture:\n{conversation}\n\n"
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
    return "Nina7727 darbojas!"

init_db()

telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()

telegram_app.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, reply)
)

if __name__ == "__main__":
    print("Nina7727 SQLite Memory darbojas...")
    telegram_app.run_polling()
