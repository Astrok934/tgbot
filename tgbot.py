import os
import logging
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests

# --- Настройка ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токены (берутся из переменных окружения Railway)
TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

if not TOKEN or not OPENROUTER_API_KEY:
    raise ValueError("Проверьте TELEGRAM_TOKEN и OPENROUTER_API_KEY в настройках Railway!")

# --- Глобальные переменные ---
user_histories = {}  # Хранилище истории диалогов

# --- Вспомогательные функции ---
def get_moscow_time() -> str:
    """Возвращает время по МСК (UTC+3)"""
    return (datetime.utcnow() + timedelta(hours=3)).strftime("%H:%M")

async def get_ai_response(user_id: int, text: str) -> str:
    """Запрос к ИИ через OpenRouter с историей диалога"""
    history = user_histories.get(user_id, [{
        "role": "system",
        "content": "Ты Хайку — дружелюбный ИИ-помощник. Отвечай кратко с эмодзи 🦊."
    }])
    
    history.append({"role": "user", "content": text})
    
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "HTTP-Referer": "https://github.com/Astrok934/tgbot",  # Укажите ваш репозиторий
                "X-Title": "Telegram Bot"
            },
            json={
                "model": "anthropic/claude-3-haiku",
                "messages": history[-6:]  # Последние 6 сообщений
            },
            timeout=10
        )
        response.raise_for_status()
        reply = response.json()["choices"][0]["message"]["content"]
        history.append({"role": "assistant", "content": reply})
        user_histories[user_id] = history[-6:]  # Ограничиваем историю
        return reply
    except Exception as e:
        logger.error(f"Ошибка OpenRouter: {str(e)}")
        return "⚠️ Ошибка генерации ответа"

# --- Обработчики команд ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик /start"""
    help_text = (
        "🦊 Привет! Я Хайку — твой ИИ-помощник.\n"
        "• В личных сообщениях отвечаю на всё\n"
        "• В группах используй «Хайку, вопрос»\n"
        "• /time — время по МСК"
    )
    await update.message.reply_text(help_text)

async def time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик /time"""
    await update.message.reply_text(f"⏰ Москва: {get_moscow_time()}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка текстовых сообщений"""
    if not update.message or not update.message.text:
        return

    message = update.effective_message
    user_text = message.text.strip()
    
    # В группах реагируем только на триггер "Хайку,"
    if message.chat.type != "private":
        if not user_text.lower().startswith(('хайку,', 'хайку ')):
            return
        user_text = user_text.split(maxsplit=1)[1] if ' ' in user_text else user_text.split(',', 1)[1].strip()
    
    try:
        response = await get_ai_response(update.effective_user.id, user_text)
        await message.reply_text(response)
    except Exception as e:
        logger.error(f"Ошибка обработки: {str(e)}")
        await message.reply_text("🔧 Произошла ошибка. Попробуйте позже.")

# --- Запуск ---
def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("time", time))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("Бот запущен и готов к работе!")
    app.run_polling()

if __name__ == "__main__":
    main()
