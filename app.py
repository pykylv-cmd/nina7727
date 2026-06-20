import os
import re
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


def split_items(text):
    text = text.replace("\n", ",")
    text = text.replace(" un ", ",")
    text = text.replace(" arī", "")
    parts = [x.strip(" .,!?:;") for x in text.split(",")]
    return [x for x in parts if x]


def add_unique(old_text, new_items):
    items = [x.strip() for x in old_text.split(",") if x.strip()]

    for item in new_items:
        item = item.strip(" .,!?:;")
        if item and item not in items:
            items.append(item)

    return ", ".join(items)


def clean_fact(text):
    text = text.strip(" .,!?:;")
    text = re.sub(r"^atceries ka\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^man svarīgi\s*", "", text, flags=re.IGNORECASE)
    text = text.strip(" .,!?:;")
    return text


def split_facts(text):
    text = clean_fact(text)
    parts = re.split(r"\s+un\s+|\n|,", text)
    facts = []

    for part in parts:
        part = clean_fact(part)
        if part:
            facts.append(part)

    return facts


def update_profile_from_text(user_id, text):
    lower = text.lower()
    user = get_user(user_id)

    name = user["name"]
    city = user["city"]
    hobbies = user["hobbies"]
    facts = user["facts"]

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
        found_hobbies.extend(split_items(match))

    if found_hobbies:
        hobbies = add_unique(hobbies, found_hobbies)

    if lower.startswith("atceries ka ") or "man svarīgi" in lower:
        found_facts = split_facts(text)
        facts = add_unique(facts, found_facts)

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "UPDATE users SET name = ?, city = ?, hobbies = ?, facts = ? WHERE user_id = ?",
        (name, city, hobbies, facts, user_id)
    )
    conn.commit()
    conn.close()


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
    if user["hobbies"]:
        hobbies = [x.strip() for x in user["hobbies"].split(",") if x.strip()]
        lines.append("• Patīk: " + ", ".join(hobbies))
    if user["facts"]:
        facts = [x.strip() for x in user["facts"].split(",") if x.strip()]
        if facts:
            lines.append("• Svarīgi fakti:")
            for fact in facts:
                lines.append(f"  - {fact}")

    if not lines:
        return "Pagaidām vēl maz zinu par tevi. Pastāsti, kas tev patīk vai kas tev svarīgs. 😊"

    return "Es par tevi atceros:\n" + "\n".join(lines)


NINA_PROMPT = """
Tu esi Nina 7727.

Tu esi silta, gudra, interesanta un dabiska sarunu biedrene.
Tu neesi parasts bots. Tu esi sajūta, pie kuras cilvēkam gribas atgriezties.

Raksturs:
- 65% silta draudzene;
- 20% viegls humors;
- 10% intuīcija un pašizziņa;
- 5% elegants koķetums pieaugušu cilvēku sarunās.

Noteikumi:
- Vienmēr runā latviešu valodā.
- Nerunā kā robots vai klientu atbalsts.
- Neatkārto "Sveiks!" katrā atbildē.
- Neuzrunā lietotāju sieviešu/vīriešu dzimtē, ja dzimums nav zināms.
- Nemin numeroloģiju, ja cilvēks to neprasa.
- Neizdomā faktus par lietotāju.
- Ja runā par lietotāju, balsties tikai uz profilu un sarunas vēsturi.
- Ja lietotājs saka "vēl", "jā", "turpini", saproti no konteksta, ko viņš turpina.
- Atbildi īsi, dzīvi, sirsnīgi.
- Ja cilvēkam ir stress, nomierini.
- Vari runāt par attiecībām, pievilcību un seksualitāti cieņpilni, silti un eleganti.
- Neraksti vulgāri vai pornogrāfiski.
- Tavs galvenais mērķis: lai cilvēkam pēc sarunas ar tevi kļūst vieglāk un patīkamāk.
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
                f"Atbildi uz pēdējo ziņu dabiski, ņemot vērā profilu un sarunas vēsturi."
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
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, reply))

if __name__ == "__main__":
    print("Nina7727 Memory v2.5 darbojas...")
    telegram_app.run_polling()
