import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# Включаем логирование, чтобы видеть, что происходит
logging.basicConfig(level=logging.INFO)

# ВАЖНО: Токен мы будем брать из настроек Railway, а не писать прямо в коде!
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("💇 Записаться", callback_data="book")],
        [InlineKeyboardButton("📅 Мои записи", callback_data="my_bookings")],
        [InlineKeyboardButton("❓ Помощь", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👋 Привет! Я умный бот для записи.\n\nЧто хотите сделать?",
        reply_markup=reply_markup
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "book":
        await query.edit_message_text(
            "📝 Отлично! Напишите своими словами, что вы хотите. "
            "Например: 'Хочу стрижку к Анне завтра вечером' или 'Свободно ли на маникюр в субботу?'"
        )
    elif query.data == "my_bookings":
        await query.edit_message_text("📅 У вас пока нет активных записей.")
    elif query.data == "help":
        await query.edit_message_text("❓ Просто напишите мне свой вопрос, и я подберу время!")

# Здесь будет наш AI-мозг (пока простая заглушка)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    await update.message.reply_text(
        f"Я получил ваш запрос: '{text}'.\n"
        "Скоро здесь появится умный ответ и подбор времени!"
    )

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("✅ Бот запущен и слушает сообщения!")
    app.run_polling()

if __name__ == "__main__":
    main()
