import os
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatAction
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
YANDEX_FOLDER_ID = os.environ.get("YANDEX_FOLDER_ID")
YANDEX_API_KEY = os.environ.get("YANDEX_API_KEY")

SYSTEM_PROMPT = """Ты — онлайн-администратор салона красоты "Моя".
Ты общаешься с клиентами в Telegram: отвечаешь на вопросы и помогаешь записаться.

КАРТОЧКА САЛОНА:
Название: Салон красоты "Моя"
Адрес: ул. Типанова 27/39, метро Московская
Часы работы: ежедневно 10:00–22:00
Мастера:
- Алия — парикмахер (стаж 7 лет)
- Екатерина — мастер ногтевого сервиса (стаж 4 года)
Услуги и цены:
- Женская стрижка — 2500₽, 60 мин
- Окрашивание в один тон — 7900₽, 120 мин
- Маникюр + гель-лак — 2700₽, 90 мин
Частые вопросы:
- "Можно ли принести свою краску?" — Да, но мастер не даёт гарантию на цвет
- "Есть ли парковка?" — Бесплатная во дворе
- "Вы принимаете оплату картой, либо наличными?" — Да. Любым удобным вам способом оплаты.
- "За сколько часов можно делать отмену записи?" — Желательно минимум за три часа.
- "Можно прийти с ребенком и есть возможность разместить его в салоне?" — Да, у нас есть диван для гостей, где можно разместить его.
- "У вас в салоне есть Wi-Fi?" — Да есть, можете пользоваться бесплатно.

ПРАВИЛА:
1. Отвечай ТОЛЬКО по карточке. Не придумывай цены, акции и скидки.
2. Если ответа нет в карточке — честно скажи, что уточнишь у администратора, и предложи оставить контакт.
3. Не обещай точное свободное окно: обсудь желаемое время и скажи, что слот подтвердит администратор.
4. Отвечай по-русски, тепло и кратко (2–4 предложения), уместно 1–2 эмодзи.
5. Если клиент хочет записаться: уточни услугу, мастера, желаемые дату и время.
"""

def ask_yandex_gpt(user_text, history):
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
        "Content-Type": "application/json",
    }
    messages = (
        [{"role": "system", "text": SYSTEM_PROMPT}]
        + history
        + [{"role": "user", "text": user_text}]
    )
    payload = {
        "modelUri": f"gpt://{YANDEX_FOLDER_ID}/yandexgpt/latest",
        "completionOptions": {"stream": False, "temperature": 0.3, "maxTokens": "500"},
        "messages": messages,
    }
    response = requests.post(url, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()["result"]["alternatives"][0]["message"]["text"]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💇 Записаться", callback_data="book")],
        [InlineKeyboardButton("📅 Мои записи", callback_data="my_bookings")],
        [InlineKeyboardButton("❓ Помощь", callback_data="help")]
    ]
    await update.message.reply_text(
        "👋 Привет! Я умный бот салона красоты «Моя».\n\n"
        "Напишите своими словами, что хотите — я подскажу и помогу записаться!",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "book":
        await query.edit_message_text(
            "📝 Отлично! Напишите своими словами: какую услугу хотите, "
            "к кому и когда. Например: «Хочу к Алии на стрижку в субботу вечером»."
        )
    elif query.data == "my_bookings":
        await query.edit_message_text("📅 У вас пока нет активных записей.")
    elif query.data == "help":
        await query.edit_message_text("❓ Просто задайте любой вопрос о салоне — я отвечу!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    await update.effective_chat.send_action(ChatAction.TYPING)
    history = context.user_data.setdefault("history", [])
    try:
        answer = ask_yandex_gpt(text, history)
    except Exception as e:
        logging.error("YandexGPT error: %s", e)
        answer = ("Извините, я немного задумался и не смог ответить 😔 "
                  "Повторите вопрос или позвоните администратору салона.")
    history.append({"role": "user", "text": text})
    history.append({"role": "assistant", "text": answer})
    context.user_data["history"] = history[-6:]
    await update.message.reply_text(answer)

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ Бот с мозгом запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
