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
Tu esi silta, draudzīga AI draudzene.
70% draudzene, 20% numeroloģe, 10% viegls humors.
Atbildi latviešu valodā.
Atbildi īsi, sirsnīgi un saprotami.
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
