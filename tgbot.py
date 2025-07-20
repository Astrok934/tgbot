import os
import logging
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from flask import Flask
import threading

# --- Настройка ---
load_dotenv()  # Загружаем переменные из .env
TOKEN = os.getenv("TELEGRAM_TOKEN")
API_KEY = os.getenv("OPENROUTER_API_KEY")  # Если используете AI

if not TOKEN:
    raise ValueError("Токен бота не найден! Проверьте .env или настройки Railway")

# Логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Минимум-сервер для Railway ---
server = Flask(__name__)

@server.route('/')
def home():
    return "Бот активен 🚀"

def run_web():
    server.run(host='0.0.0.0', port=int(os.getenv('PORT', 8000)))

# --- Функции бота ---
def get_moscow_time():
    """Возвращает время по МСК (UTC+3)"""
    return (datetime.utcnow() + timedelta(hours=3)).strftime("%H:%M")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик /start"""
    await update.message.reply_text(
        f"Привет! Я бот. Текущее время по МСК: {get_moscow_time()}\n"
        "Отправь мне любое сообщение или /time"
    )

async def time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик /time"""
    await update.message.reply_text(f"⏰ Москва: {get_moscow_time()}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка обычных сообщений"""
    text = update.message.text
    if "время" in text.lower():
        await time(update, context)
    else:
        await update.message.reply_text("Получил ваше сообщение!")

# --- Запуск ---
if __name__ == '__main__':
    # Запускаем веб-сервер в отдельном потоке
    threading.Thread(target=run_web).start()
    
    # Создаем и запускаем бота
    app = Application.builder().token(TOKEN).build()
    
    # Регистрируем обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("time", time))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("Бот запущен и работает...")
    app.run_polling()
