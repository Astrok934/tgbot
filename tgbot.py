import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- Настройка ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получаем токен из переменных окружения
TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TOKEN:
    raise ValueError("Токен не найден! Проверьте настройки Railway.")

# --- Команды бота ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик /start"""
    user = update.effective_user
    await update.message.reply_text(
        f"Привет, {user.first_name}! Я работаю ✅\n"
        "Команды:\n"
        "/start - информация\n"
        "/time - текущее время"
    )

async def time_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик /time"""
    from datetime import datetime
    await update.message.reply_text(f"⏰ Время: {datetime.now().strftime('%H:%M:%S')}")

# --- Запуск ---
def main():
    app = Application.builder().token(TOKEN).build()
    
    # Регистрация обработчиков
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("time", time_command))
    
    # Фильтр для обычных сообщений (отвечает только на команды)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, lambda u, c: None))
    
    logger.info("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()
