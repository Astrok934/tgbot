import os
import logging
import json
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

# Токены
TOKEN = os.getenv("TELEGRAM_TOKEN")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# Проверка переменных
if not TOKEN:
    logger.error("TELEGRAM_TOKEN не установлен!")
    exit(1)
if not DEEPSEEK_API_KEY:
    logger.warning("DEEPSEEK_API_KEY не установлен! Бот будет работать в режиме эхо.")

# --- Глобальные переменные ---
user_histories = {}
GROUP_TRIGGERS = ["секон", "бот", "ии", "нейросеть", "ai", "chatgpt", "секон,"]

# --- Вспомогательные функции ---
def get_moscow_time() -> str:
    return (datetime.utcnow() + timedelta(hours=3)).strftime("%H:%M")

def should_respond_in_group(text: str, bot_username: str = "") -> bool:
    """Определяем, нужно ли отвечать в группе"""
    text_lower = text.lower()
    
    # Если бота упомянули через @
    if bot_username and f"@{bot_username.lower()}" in text_lower:
        return True
    
    # Если есть триггерные слова
    for trigger in GROUP_TRIGGERS:
        if trigger in text_lower:
            return True
    
    # Если сообщение является ответом на сообщение бота
    return False

async def get_ai_response(user_id: int, text: str) -> str:
    """Запрос к DeepSeek API"""
    if not DEEPSEEK_API_KEY:
        return "🤖 Режим эхо: " + text
    
    history = user_histories.get(user_id, [{
        "role": "system",
        "content": "Ты Секон, хороший тип и крутой. общаешься на любые темы"
    }])
    
    history.append({"role": "user", "content": text})
    
    try:
        response = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "deepseek-chat",
                "messages": history[-8:],
                "max_tokens": 1000,
                "temperature": 0.8,
                "stream": False
            },
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            reply = data["choices"][0]["message"]["content"]
            
            history.append({"role": "assistant", "content": reply})
            user_histories[user_id] = history[-8:]
            
            return reply
        else:
            logger.error(f"Ошибка API: {response.status_code} - {response.text}")
            return f"⚠️ Ошибка {response.status_code}. Попробуй позже."
            
    except Exception as e:
        logger.error(f"Ошибка подключения: {e}")
        return "🤖 Сорян, проблемы с подключением. Давай попробуем еще раз?"

# --- Обработчики команд ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик /start"""
    help_text = (
        "🤖 Привет! Я Секон — твой ИИ-помощник\n\n"
        "📌 В личных сообщениях:\n"
        "• Просто пиши мне что угодно\n\n"
        "📌 В группах:\n"
        "• Упомяни меня через @бот (после запуска)\n"
        "• Используй слова: секон, бот, ии, нейросеть\n"
        "• Ответь на моё сообщение\n\n"
        "🛠 Команды:\n"
        "/start - это сообщение\n"
        "/time - время по МСК\n"
        "/clear - очистить историю\n"
        "/help - помощь"
    )
    await update.message.reply_text(help_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик /help"""
    help_text = (
        "📋 Как общаться со мной:\n\n"
        "💬 В ЛИЧКЕ: просто пиши мне\n\n"
        "👥 В ГРУППАХ:\n"
        "1. Напиши: 'Секон, как дела?'\n"
        "2. Или: 'Бот, скажи что-нибудь'\n"
        "3. Или: 'ИИ, помоги с...'\n"
        "4. Или ответь на моё сообщение\n"
        "5. Или упомяни через @бот_username\n\n"
        "🎯 Я реагирую на слова: секон, бот, ии, нейросеть, ai, chatgpt"
    )
    await update.message.reply_text(help_text)

async def time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик /time"""
    await update.message.reply_text(f"⏰ Москва: {get_moscow_time()}")

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик /clear"""
    user_id = update.effective_user.id
    if user_id in user_histories:
        del user_histories[user_id]
    await update.message.reply_text("🗑️ История диалога очищена!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка всех текстовых сообщений"""
    if not update.message or not update.message.text:
        return
    
    message = update.effective_message
    user_id = update.effective_user.id
    chat_type = message.chat.type
    text = message.text.strip()
    
    bot_username = context.bot.username if context.bot.username else ""
    
    should_reply = False
    reply_reason = ""
    
    if chat_type == "private":
        should_reply = True
        reply_reason = "личное сообщение"
    elif chat_type in ["group", "supergroup"]:
        if bot_username and f"@{bot_username}" in text.lower():
            should_reply = True
            reply_reason = "упоминание"
            text = text.replace(f"@{bot_username}", "").strip()
        elif should_respond_in_group(text, bot_username):
            should_reply = True
            reply_reason = "триггерное слово"
        elif message.reply_to_message and message.reply_to_message.from_user.id == context.bot.id:
            should_reply = True
            reply_reason = "ответ на бота"
    
    if not should_reply:
        return
    
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, 
        action="typing"
    )
    
    logger.info(f"Отвечаю user_id {user_id} в {chat_type} ({reply_reason}): {text[:50]}...")
    
    try:
        response = await get_ai_response(user_id, text)
        
        await message.reply_text(
            response,
            parse_mode="Markdown",
            reply_to_message_id=message.message_id if chat_type != "private" else None
        )
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await message.reply_text(
            "😕 Что-то пошло не так. Попробуй еще раз через минуту.",
            reply_to_message_id=message.message_id if chat_type != "private" else None
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик ошибок"""
    logger.error(f"Ошибка: {context.error}")
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ Произошла ошибка. Попробуй позже."
        )

# --- Запуск ---
def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("time", time))
    app.add_handler(CommandHandler("clear", clear))
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    app.add_error_handler(error_handler)
    
    logger.info("=" * 50)
    logger.info(f"Бот Секон запущен! Username: @{app.bot.username}")
    logger.info(f"Режим DeepSeek: {'АКТИВЕН' if DEEPSEEK_API_KEY else 'ЭХО'}")
    logger.info("=" * 50)
    logger.info("Триггеры для групп: " + ", ".join(GROUP_TRIGGERS))
    logger.info("=" * 50)
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
