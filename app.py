import os
from flask import Flask
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from openai import OpenAI

app = Flask(__name__)

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]

memory = {}

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
- Atbildi īsi, silti, dzīvi un cilvēciski.
- Galvenais: lai cilvēkam ir sajūta, ka viņš runā ar dzīvu sarunu biedreni.
"""

async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    user_id = str(update.effective_user.id)

    if user_id not in memory:
        memory[user_id] = []

    memory[user_id].append(f"Lietotājs: {user_text}")
    memory[user_id] = memory[user_id][-12:]

    conversation = "\n".join(memory[user_id])

    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=(
                f"{NINA_PROMPT}\n\n"
                f"Sarunas vēsture:\n{conversation}\n\n"
                f"Atbildi uz pēdējo lietotāja ziņu, ņemot vērā sarunas vēsturi."
            )
        )

        answer = response.output_text

    except Exception as e:
        print("Kļūda:", e)
        answer = "Piedod, man šobrīd kaut kas aizķērās. Pamēģini vēlreiz pēc brīža. 🌷"

    memory[user_id].append(f"Nina: {answer}")
    memory[user_id] = memory[user_id][-12:]

    await update.message.reply_text(answer)

@app.route("/")
def home():
    return "Nina7727 darbojas!"

telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()

telegram_app.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, reply)
)

if __name__ == "__main__":
    print("Nina7727 Memory v1 darbojas...")
    telegram_app.run_polling()
