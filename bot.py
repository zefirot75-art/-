import os
import re
import logging
import requests
import psycopg2
from datetime import datetime, timedelta
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

# Таблица соответствия услуг → service_id в DIKIDI
DIKIDI_COMPANY_ID = "2207697"
SERVICE_MAPPING = {
    "стрижка": "24052063",
    "подстричься": "24052063",
    "постричься": "24052063",
    "стрижки": "24052063",
}

STATUS_LABELS = {
    "new": "🆕 новая",
    "confirmed": "✅ подтверждена",
    "completed": "💰 выполнена",
    "cancelled": "❌ отменена",
    "no_show": "👻 неявка",
}

SERVICES_LIST = ("• Женская стрижка — 2500₽\n"
                 "• Окрашивание в один тон — 7900₽\n"
                 "• Маникюр + гель-лак — 2700₽")

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
6. Если клиент просит услугу, которой НЕТ в карточке салона — честно скажи, что салон её не делает, перечисли все услуги из карточки с ценами и предложи записаться на одну из них. Не обещай "уточнить" такую услугу у администратора.
"""

SUMMARY_PROMPT = ("Ты — помощник администратора салона. По диалогу ниже опиши запрос клиента "
                  "ОДНОЙ строкой: услуга, мастер, желаемые дата и время. Пиши только суть, "
                  "без приветствий. Если чего-то не известно — НЕ пиши 'не указан', просто опусти эту часть.")

PRICE_CHECK_PROMPT = ("Ты — строгий классификатор. Услуги салона красоты \"Моя\": "
                      "женская стрижка; окрашивание в один тон; маникюр с гель-лаком. "
                      "По диалогу определи, соответствует ли запрашиваемая клиентом услуга этим услугам "
                      "(учитывай синонимы: \"подстричься\", \"гель-лак\", \"покрасить корни\", \"ноготочки\" и т.п.). "
                      "Ответь строго одним словом: ДА или НЕТ.")

# ---------- БАЗА ДАННЫХ ----------

def db_connect():
    return psycopg2.connect(DATABASE_URL, sslmode="prefer")

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

# ---------- DIKIDI ИНТЕГРАЦИЯ ----------

def get_free_slots(service_name):
    """Получает свободные слоты из DIKIDI для услуги"""
    service_id = None
    for keyword, sid in SERVICE_MAPPING.items():
        if keyword in service_name.lower():
            service_id = sid
            break
    
    if not service_id:
        return None, None, "Услуга не найдена в DIKIDI"
    
    try:
        url = "https://dikidi.net/ru/mobile/ajax/newrecord/get_datetimes/"
        params = {
            "company_id": DIKIDI_COMPANY_ID,
            "service_id[]": service_id,
            "with_first": "1",
            "day_month": ""
        }
        headers = {
            "User-Agent": "Mozilla/5.0",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"https://dikidi.net/{DIKIDI_COMPANY_ID}"
        }
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Извлекаем мастеров и слоты
        masters = data.get("masters", {})
        times = data.get("times", {})
        
        # Собираем все слоты от всех мастеров
        all_slots = []
        for master_id, slots in times.items():
            master_name = masters.get(master_id, {}).get("username", "Мастер")
            for slot in slots:
                dt = datetime.strptime(slot, "%Y-%m-%d %H:%M:%S")
                all_slots.append({"datetime": dt, "master": master_name, "master_id": master_id})
        
        # Сортируем по дате/времени
        all_slots.sort(key=lambda x: x["datetime"])
        
        return all_slots, masters, None
    except Exception as e:
        logging.error("DIKIDI error: %s", e)
        return None, None, str(e)

def filter_slots_by_request(slots, user_request):
    """Фильтрует слоты по запросу клиента (сегодня/завтра/утро/вечер)"""
    if not slots:
        return []
    
    now = datetime.now()
    filtered = []
    
    # Простая эвристика: если упомянуто "завтра" — берём только завтра
    if "завтра" in user_request.lower():
        tomorrow = now + timedelta(days=1)
        filtered = [s for s in slots if s["datetime"].date() == tomorrow.date()]
    # Если "сегодня" — только сегодня
    elif "сегодня" in user_request.lower():
        filtered = [s for s in slots if s["datetime"].date() == now.date()]
    # Если "утро" — до 12:00
    elif "утро" in user_request.lower() or "утром" in user_request.lower():
        filtered = [s for s in slots if s["datetime"].hour < 12]
    # Если "вечер" — после 18:00
    elif "вечер" in user_request.lower() or "вечером" in user_request.lower():
        filtered = [s for s in slots if s["datetime"].hour >= 18]
    # Иначе — все ближайшие 5 слотов
    else:
        filtered = slots[:5]
    
    return filtered[:5]  # Не более 5 вариантов

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

def check_in_price(history):
    user_msgs = [m for m in history if m["role"] == "user"]
    if not user_msgs:
        return True
    try:
        answer = ask_yandex_gpt(
            "Соответствует ли запрашиваемая клиентом услуга прайсу салона?",
            history,
            system_text=PRICE_CHECK_PROMPT,
        )
        return answer.strip().upper().startswith("ДА")
    except Exception as e:
        logging.error("Price check error: %s", e)
        return True

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

    if data == "book":
        await query.edit_message_text(
            "📝 Отлично! Напишите своими словами: какую услугу хотите, "
            "к кому и когда. Например: «Хочу к Алии на стрижку завтра после обеда»."
        )
    elif data == "my_bookings":
        await query.edit_message_text("📅 У вас пока нет активных записей.")
    elif data == "help":
        await query.edit_message_text("❓ Просто задайте любой вопрос о салоне — я отвечу!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    await update.effective_chat.send_action(ChatAction.TYPING)
    history = context.user_data.setdefault("history", [])

    # Проверяем, есть ли в сообщении упоминание услуги для записи
    booking_keywords = ["записаться", "запись", "хочу", "нужно", "можно"]
    is_booking_request = any(kw in text.lower() for kw in booking_keywords)
    
    # Пытаемся определить услугу из запроса
    detected_service = None
    for service_key in SERVICE_MAPPING.keys():
        if service_key in text.lower():
            detected_service = service_key
            break
    
    # Если это запрос на запись и мы нашли услугу — показываем реальные слоты
    if is_booking_request and detected_service:
        slots, masters, error = get_free_slots(detected_service)
        if slots:
            filtered = filter_slots_by_request(slots, text)
            if filtered:
                slots_text = "🗓 **Свободные окна:**\n\n"
                for i, slot in enumerate(filtered[:5], 1):
                    dt_str = slot["datetime"].strftime("%d.%m %H:%M")
                    slots_text += f"{i}. {dt_str} — {slot['master']}\n"
                slots_text += "\nКакое время удобно? Напишите номер или точное время."
                
                await update.message.reply_text(slots_text)
                
                # Сохраняем в историю, что показали слоты
                history.append({"role": "user", "text": text})
                history.append({"role": "assistant", "text": slots_text})
                context.user_data["history"] = history[-6:]
                return
            else:
                await update.message.reply_text(
                    "😔 К сожалению, на выбранные даты нет свободных окон. "
                    "Попробуйте другой день или напишите «покажи все окна»."
                )
                return

    phone_match = PHONE_REGEX.search(text)
    if phone_match:
        phone = phone_match.group(0)
        try:
            summary = ask_yandex_gpt("Опиши запрос клиента одной строкой.", history, system_text=SUMMARY_PROMPT)
        except Exception as e:
            logging.error("Summary error: %s", e)
            summary = " ; ".join(m["text"] for m in history if m["role"] == "user")[-300:]

        in_price = check_in_price(history)

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
            notify = (
                "🔥 Новая заявка!\n"
                f"📋 {summary}\n"
                f"📞 Телефон: {phone}\n"
                f"👤 Клиент: {update.effective_user.full_name}"
            )
            if not in_price:
                notify += "\n⚠️ Услуги нет в прайсе"
            await context.bot.send_message(
                chat_id=int(OWNER_CHAT_ID),
                text=notify,
                reply_markup=keyboard,
            )
            if in_price:
                client_reply = (
                    "Спасибо! Я передал вашу заявку администратору — "
                    "он свяжется с вами в ближайшее время для подтверждения времени 😊"
                )
            else:
                client_reply = (
                    "Спасибо, ваш вопрос передан администратору 😊\n"
                    "Небольшое уточнение: наш салон не оказывает такую услугу. "
                    "Но мы отлично делаем:\n"
                    f"{SERVICES_LIST}\n"
                    "Если что-то из этого подходит — просто напишите, и я запишу вас сразу! 💫"
                )
            await update.message.reply_text(client_reply)
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
    print("✅ Бот с DIKIDI-зрением запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
