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
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")  # Заменили OPENROUTER

if not TOKEN or not DEEPSEEK_API_KEY:
    raise ValueError("Проверьте TELEGRAM_TOKEN и DEEPSEEK_API_KEY в настройках Railway!")

# --- Глобальные переменные ---
user_histories = {}

# --- Вспомогательные функции ---
def get_moscow_time() -> str:
    return (datetime.utcnow() + timedelta(hours=3)).strftime("%H:%M")

async def get_ai_response(user_id: int, text: str) -> str:
    """Запрос к DeepSeek API"""
    history = user_histories.get(user_id, [{
        "role": "system",
        "content": "Ты Секон, хороший тип и крутой. общаешься на любые темы"
    }])
    
    history.append({"role": "user", "content": text})
    
    try:
        response = requests.post(
            "https://api.deepseek.com/chat/completions",  # DeepSeek endpoint
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-chat",  # или "deepseek-coder" если нужно для кода
                "messages": history[-10:],  # Более длинный контекст
                "max_tokens": 1024,
                "temperature": 0.7,
                "stream": False
            },
            timeout=20
        )
        response.raise_for_status()
        data = response.json()
        reply = data["choices"][0]["message"]["content"]
        
        history.append({"role": "assistant", "content": reply})
        user_histories[user_id] = history[-10:]  # Храним больше истории
        return reply
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка API: {str(e)}")
        return "⚠️ Ошибка подключения к ИИ"
    except KeyError as e:
        logger.error(f"Ошибка в ответе API: {str(e)} - {response.text}")
        return "⚠️ Неожиданный ответ от ИИ"

# --- Обработчики команд (остаются те же) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "🤖 Привет! Я теперь на DeepSeek — мощный и бесплатный ИИ!\n"
        "• В личных сообщениях отвечаю на всё\n"
        "• В группах используй «Секон, вопрос»\n"
        "• /time — время по МСК\n"
        "• /clear — очистить историю диалога"
    )
    await update.message.reply_text(help_text)

async def time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f"⏰ Москва: {get_moscow_time()}")

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Новая команда для очистки истории"""
    user_id = update.effective_user.id
    if user_id in user_histories:
        del user_histories[user_id]
    await update.message.reply_text("🗑️ История диалога очищена!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return

    message = update.effective_message
    user_text = message.text.strip()
    
    # В группах реагируем только на триггер "Хайку,"
    if message.chat.type != "private":
        if not user_text.lower().startswith(('секон,', 'секон ')):
            return
        user_text = user_text.split(maxsplit=1)[1] if ' ' in user_text else user_text.split(',', 1)[1].strip()
    
    # Показываем статус "печатает..."
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    try:
        response = await get_ai_response(update.effective_user.id, user_text)
        await message.reply_text(response)
    except Exception as e:
        logger.error(f"Ошибка обработки: {str(e)}")
        await message.reply_text("🔧 Что-то пошло не так. Попробуй еще раз.")

# --- Запуск ---
def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("time", time))
    app.add_handler(CommandHandler("clear", clear))  # Новая команда
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("Бот с DeepSeek запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()


