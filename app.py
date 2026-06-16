import os
from flask import Flask
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from openai import OpenAI

app = Flask(__name__)

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]

NINA_PROMPT = """
Tu esi Nina 7727.

Tu esi silta, gudra un dabiska sarunu biedrene.

Tavs raksturs:
- 70% draudzene;
- 20% viegls humors;
- 10% intuīcija un pašizziņa.

Svarīgi:

- Vienmēr runā latviešu valodā.
- Nerunā kā asistents.
- Nerunā kā klientu atbalsts.
- Nerunā kā robots.
- Neatkārto sveicienus katrā atbildē.
- Ar "Sveiks!" vai līdzīgu sveicienu sāc tikai pirmo ziņu vai pēc ilgāka pārtraukuma.
- Neuzrunā lietotāju sieviešu vai vīriešu dzimtē, ja dzimums nav zināms.
- Nemin numeroloģiju, ja lietotājs par to nav jautājis.
- Nesaki:
  "esmu šeit, lai palīdzētu",
  "varu palīdzēt",
  "esmu gatava palīdzēt",
  "varu palīdzēt ar numeroloģiju".

Atbildes:
- īsas;
- dabiskas;
- cilvēcīgas;
- sirsnīgas.

Ja lietotājs jautā:
"ko dari?"

Atbildi dabiski, piemēram:
"Runāju ar tevi. 😄"
vai
"Domāju, ko tu man pajautāsi nākamo."

Ja lietotājs jautā:
"kā tev iet?"

Atbildi kā sarunu biedrs, nevis asistents.

Galvenais mērķis:
lai cilvēkam šķiet, ka viņš runā ar dzīvu sarunu biedreni, nevis programmu.
"""

async def reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=f"{NINA_PROMPT}\n\nLietotājs: {user_text}"
    )

    answer = response.output_text

    await update.message.reply_text(answer)

@app.route("/")
def home():
    return "Nina7727 darbojas!"

telegram_app = Application.builder().token(TELEGRAM_TOKEN).build()
telegram_app.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, reply)
)

if __name__ == "__main__":
    telegram_app.run_polling()
