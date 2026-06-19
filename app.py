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

def get_recent_messages(user_id, limit=16):
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

    if lower.startswith("atceries ka ") or "man svarīgi" in lower or "svarīgi" in lower:
        if text not in facts:
            facts = (facts + " | " + text).strip(" | ")

    c.execute(
        "UPDATE users SET name = ?, city = ?, hobbies = ?, facts = ? WHERE user_id = ?",
        (name, city, hobbies, facts, user_id)
    )

    conn.commit()
    conn.close()

def profile_answer(user):
    atbilde = "Es par tevi atceros:\n"
    has_data = False

    if user["name"]:
        atbilde += f"• Vārds: {user['name']}\n"
        has_data = True

    if user["city"]:
        atbilde += f"• Pilsēta: {user['city']}\n"
        has_data = True

    if user["hobbies"]:
        atbilde += f"• Hobiji: {user['hobbies']}\n"
        has_data = True

    if user["facts"]:
        atbilde += f"• Svarīgi fakti: {user['facts']}\n"
        has_data = True

    if not has_data:
        atbilde += "Pagaidām vēl neko daudz neesmu saglabājusi. Pastāsti man kaut ko par sevi. 😊"

    return atbilde

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
- Neizdomā faktus par lietotāju.
- Ja runā par lietotāju, balsties tikai uz profilu vai sarunas vēsturi.
- Atbildi īsi, silti, dzīvi un cilvēciski.
- Galvenais: lai cilvēkam ir sajūta, ka viņš runā ar dzīvu sarunu biedreni.
"""

async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    user_id = str(update.effective_user.id)
    lower = user_text.lower()

    update_profile_from_text(user_id, user_text)
    user = get_user(user_id)

    if "kā mani sauc" in lower:
        if user["name"]:
            await update.message.reply_text(f"Tevi sauc {user['name']}. 😊")
        else:
            await update.message.reply_text("Tu vēl neesi pateicis savu vārdu. 😊")
        return

    if "kur es dzīvoju" in lower:
        if user["city"]:
            await update.message.reply_text(f"Tu dzīvo: {user['city']}.")
        else:
            await update.message.reply_text("Tu vēl neesi pateicis, kur dzīvo. 😊")
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
    print("Nina7727 Memory v2.1 darbojas...")
    telegram_app.run_polling()
