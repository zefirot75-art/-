import os
import re
import logging
import requests
import psycopg2
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
YANDEX_FOLDER_ID = os.environ.get("YANDEX_FOLDER_ID")
YANDEX_API_KEY = os.environ.get("YANDEX_API_KEY")
OWNER_CHAT_ID = os.environ.get("OWNER_CHAT_ID")
DATABASE_URL = os.environ.get("DATABASE_URL")

PHONE_REGEX = re.compile(r'(\+7|8)[\s\-\(]*\d{3}[\s\-\)]*\d{3}[\s\-]*\d{2}[\s\-]*\d{2}')

STATUS_LABELS = {
    "new": "🆕 новая",
    "confirmed": "✅ подтверждена",
    "completed": "💰 выполнена",
    "cancelled": "❌ отменена",
    "no_show": "👻 неявка",
}

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
3. Не обещай точное свободное окно: обсуди желаемое время и скажи, что слот подтвердит администратор.
4. Отвечай по-русски, тепло и кратко (2–4 предложения), уместно 1–2 эмодзи.
5. Если клиент хочет записаться: в ПЕРВОМ же ответе подтверди услугу и желаемое время И обязательно попроси контактный телефон в этом же сообщении — без него запись не оформить. Не откладывай просьбу о телефоне на следующие ответы.
"""

SUMMARY_PROMPT = ("Ты — помощник администратора салона. По диалогу ниже опиши запрос клиента "
                  "ОДНОЙ строкой: услуга, мастер, желаемые дата и время. Пиши только суть, "
                  "без приветствий. Если чего-то не известно — просто пропусти.")

# ---------- БАЗА ДАННЫХ ----------

def db_connect():
    return psycopg2.connect(DATABASE_URL, sslmode="require")

def db_init():
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS salons (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            card TEXT NOT NULL,
            owner_chat_id BIGINT,
            bot_token TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id SERIAL PRIMARY KEY,
            salon_id INTEGER NOT NULL DEFAULT 1,
            client_name TEXT,
            phone TEXT,
            summary TEXT,
            status TEXT DEFAULT 'new',
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
    """)
    conn.commit()
    cur.close()
    conn.close()

def save_lead(client_name, phone, summary):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO leads (client_name, phone, summary) VALUES (%s, %s, %s) RETURNING id",
        (client_name, phone, summary),
    )
    lead_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return lead_id

def update_lead_status(lead_id, status):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("UPDATE leads SET status = %s WHERE id = %s", (status, lead_id))
    conn.commit()
    cur.close()
    conn.close()

def fetch_lead(lead_id):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute("SELECT client_name, phone, summary, status FROM leads WHERE id = %s", (lead_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row

def fetch_leads(limit=10):
    conn = db_connect()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, client_name, phone, summary, status, created_at "
        "FROM leads ORDER BY created_at DESC LIMIT %s",
        (limit,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

# ---------- AI ----------

def ask_yandex_gpt(user_text, history, system_text=None):
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
        "Content-Type": "application/json",
    }
    messages = (
        [{"role": "system", "text": system_text or SYSTEM_PROMPT}]
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

# ---------- ОБРАБОТЧИКИ ----------

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

async def leads_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if str(update.effective_user.id) != str(OWNER_CHAT_ID):
        await update.message.reply_text("⛔ Эта команда доступна только владельцу салона.")
        return
    try:
        rows = fetch_leads(10)
    except Exception as e:
        logging.error("DB fetch error: %s", e)
        await update.message.reply_text("Не смог достать данные из базы 😔")
        return
    if not rows:
        await update.message.reply_text("📭 Заявок пока нет.")
        return
    lines = ["📥 Последние 10 заявок:"]
    for lead_id, name, phone, summary, status, created_at in rows:
        lines.append(
            f"• #{lead_id} {created_at.strftime('%d.%m %H:%M')} | {name} | {phone}\n"
            f"  {STATUS_LABELS.get(status, status)}\n"
            f"  {summary}"
        )
    lines.append("\nСтатусы меняются кнопками прямо на 🔥-уведомлении.")
    await update.message.reply_text("\n".join(lines))

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # Кнопки владельца на 🔥-уведомлении
    if data.startswith("lead:"):
        if str(update.effective_user.id) != str(OWNER_CHAT_ID):
            return
        _, action, lead_id_s = data.split(":")
        lead_id = int(lead_id_s)
        try:
            update_lead_status(lead_id, action)
            lead = fetch_lead(lead_id)
        except Exception as e:
            logging.error("Lead status error: %s", e)
            return
        base_text = (query.message.text or "").split("\n\n— Статус")[0]
        await query.edit_message_text(base_text + f"\n\n— Статус изменён: {STATUS_LABELS[action]}")
        if action in ("cancelled", "no_show") and lead:
            await context.bot.send_message(
                chat_id=int(OWNER_CHAT_ID),
                text=(
                    f"🕳 Освободился слот: {lead[2]}.\n"
                    "Когда подключим расписание, бот сам предложит его листу ожидания. "
                    "Пока — напоминание для вас."
                ),
            )
        return

    # Клиентские кнопки
    if data == "book":
        await query.edit_message_text(
            "📝 Отлично! Напишите своими словами: какую услугу хотите, "
            "к кому и когда. Например: «Хочу к Алии на стрижку в субботу вечером»."
        )
    elif data == "my_bookings":
        await query.edit_message_text("📅 У вас пока нет активных записей.")
    elif data == "help":
        await query.edit_message_text("❓ Просто задайте любой вопрос о салоне — я отвечу!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    await update.effective_chat.send_action(ChatAction.TYPING)
    history = context.user_data.setdefault("history", [])

    phone_match = PHONE_REGEX.search(text)
    if phone_match:
        phone = phone_match.group(0)
        try:
            summary = ask_yandex_gpt("Опиши запрос клиента одной строкой.", history, system_text=SUMMARY_PROMPT)
        except Exception as e:
            logging.error("Summary error: %s", e)
            summary = " ; ".join(m["text"] for m in history if m["role"] == "user")[-300:]

        lead_id = None
        try:
            lead_id = save_lead(update.effective_user.full_name, phone, summary)
        except Exception as e:
            logging.error("DB save error: %s", e)

        if OWNER_CHAT_ID:
            keyboard = None
            if lead_id:
                keyboard = InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("✅ Подтверждена", callback_data=f"lead:confirmed:{lead_id}"),
                        InlineKeyboardButton("💰 Выполнена", callback_data=f"lead:completed:{lead_id}"),
                    ],
                    [
                        InlineKeyboardButton("❌ Отмена", callback_data=f"lead:cancelled:{lead_id}"),
                        InlineKeyboardButton("👻 Неявка", callback_data=f"lead:no_show:{lead_id}"),
                    ],
                ])
            await context.bot.send_message(
                chat_id=int(OWNER_CHAT_ID),
                text=(
                    "🔥 Новая заявка!\n"
                    f"📋 {summary}\n"
                    f"📞 Телефон: {phone}\n"
                    f"👤 Клиент: {update.effective_user.full_name}"
                ),
                reply_markup=keyboard,
            )
            await update.message.reply_text(
                "Спасибо! Я передал вашу заявку администратору — "
                "он свяжется с вами в ближайшее время для подтверждения времени 😊"
            )
        else:
            await update.message.reply_text(
                "Спасибо, я записал ваш номер! Администратор свяжется с вами для подтверждения времени 😊"
            )
        history.append({"role": "user", "text": text})
        history.append({"role": "assistant", "text": "Заявка принята, администратор свяжется с вами."})
        context.user_data["history"] = history[-6:]
        return

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
    db_init()
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("leads", leads_command))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ Бот со статусами заявок запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
