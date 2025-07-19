import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv

# --- Настройка ---
load_dotenv()  # Загружаем переменные из .env
TOKEN = os.getenv("TELEGRAM_TOKEN")  # Получаем токен бота

if not TOKEN:
    raise ValueError("Токен не найден! Проверьте .env файл")

# Включаем логирование
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# --- Обработчики команд ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    await update.message.reply_text(
        f"Привет, {user.first_name}! Я тестовый бот.\n"
        "Доступные команды:\n"
        "/start - Начать диалог\n"
        "/help - Помощь"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    await update.message.reply_text("Чем могу помочь?")


# --- Запуск бота ---
def main():
    # Создаем приложение
    app = Application.builder().token(TOKEN).build()

    # Регистрируем обработчики команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    # Запускаем бота
    logger.info("Бот запущен...")
    app.run_polling()


if __name__ == "__main__":
    main()