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

# Railway переменные
TOKEN = os.environ.get("TELEGRAM_TOKEN")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")

logger.info("=" * 50)
logger.info(f"TELEGRAM_TOKEN: {'✅' if TOKEN else '❌'}")
logger.info(f"DEEPSEEK_API_KEY: {'✅' if DEEPSEEK_API_KEY else '❌'}")
logger.info("=" * 50)

if not TOKEN:
    logger.error("❌ TELEGRAM_TOKEN не найден!")
    exit(1)

# --- Глобальные переменные ---
user_histories = {}
GROUP_TRIGGERS = ["секон", "бот", "ии", "нейросеть", "ai", "chatgpt"]
bot_username = None  # Будет установлено после запуска

async def get_ai_response(user_id: int, text: str) -> str:
    """Запрос к DeepSeek"""
    if not DEEPSEEK_API_KEY:
        return "🤖 API ключ не настроен. Добавь DEEPSEEK_API_KEY в Railway Variables"
    
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
                "Content-Type": "application/json"
            },
            json={
                "model": "deepseek-chat",
                "messages": history[-6:],
                "max_tokens": 800,
                "temperature": 0.7
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if "choices" in data and len(data["choices"]) > 0:
                reply = data["choices"][0]["message"]["content"]
                history.append({"role": "assistant", "content": reply})
                user_histories[user_id] = history[-6:]
                return reply
        
        logger.error(f"API ошибка: {response.status_code} - {response.text}")
        return f"⚠️ Ошибка {response.status_code}"
            
    except Exception as e:
        logger.error(f"Ошибка подключения: {str(e)}")
        return "🔌 Проблемы с подключением"

def should_respond(text: str, username: str = "") -> bool:
    """Определяем, нужно ли отвечать на сообщение"""
    if not text:
        return False
    
    text_lower = text.lower().strip()
    
    # Если упоминание бота
    if username and f"@{username}" in text_lower:
        return True
    
    # Проверяем триггерные слова
    for trigger in GROUP_TRIGGERS:
        # Проверяем начало сообщения
        patterns = [
            f"{trigger}, ",
            f"{trigger} ",
            f"{trigger}\n",
            f"{trigger}:"
        ]
        
        for pattern in patterns:
            if text_lower.startswith(pattern):
                return True
        
        # Если слово просто где-то в тексте
        if trigger in text_lower:
            return True
    
    return False

def clean_message_text(text: str, username: str = "") -> str:
    """Очищаем текст от триггеров и упоминаний"""
    if username:
        text = text.replace(f"@{username}", "")
    
    # Убираем триггеры в начале
    text_lower = text.lower()
    for trigger in GROUP_TRIGGERS:
        patterns = [
            f"{trigger}, ",
            f"{trigger.capitalize()}, ",
            f"{trigger} ",
            f"{trigger.capitalize()} ",
        ]
        
        for pattern in patterns:
            if text_lower.startswith(pattern.lower()):
                text = text[len(pattern):]
                break
    
    return text.strip()

# --- Обработчики команд ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Я Секон, крутой ИИ-помощник!\n\n"
        "💬 В личке: просто пиши\n"
        "👥 В группе: 'секон, вопрос' или 'бот, скажи'\n\n"
        "🛠 /help - помощь\n"
        "📊 /status - статус\n"
        "⏰ /time - время МСК\n"
        "🗑️ /clear - очистить историю"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📌 Как общаться:\n\n"
        "💬 В ЛИЧКЕ:\n"
        "• Просто пиши что угодно\n\n"
        "👥 В ГРУППЕ:\n"
        "• 'секон, привет' или 'Секон, как дела?'\n"
        "• 'бот, помоги' или 'ии, объясни'\n"
        "• Ответь на моё сообщение\n"
        "• Упомяни через @бот_username\n\n"
        "🔧 /status - проверка работы\n"
        "❓ /help - это сообщение"
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_text = (
        f"✅ Бот Секон работает\n"
        f"🤖 DeepSeek: {'✅' if DEEPSEEK_API_KEY else '❌'}\n"
        f"👤 Пользователей: {len(user_histories)}\n"
        f"📝 Username: @{context.bot.username if context.bot.username else 'неизвестен'}\n"
        f"🕐 Время МСК: {(datetime.utcnow() + timedelta(hours=3)).strftime('%H:%M')}"
    )
    await update.message.reply_text(status_text)

async def time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    moscow_time = (datetime.utcnow() + timedelta(hours=3)).strftime('%H:%M')
    await update.message.reply_text(f"⏰ Москва: {moscow_time}")

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_histories:
        del user_histories[user_id]
    await update.message.reply_text("🗑️ История очищена!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка всех сообщений"""
    if not update.message or not update.message.text:
        return
    
    message = update.effective_message
    user_id = update.effective_user.id
    chat_type = message.chat.type
    original_text = message.text.strip()
    
    # Получаем username бота из контекста
    username = context.bot.username if context.bot.username else ""
    
    # Определяем, нужно ли отвечать
    should_reply = False
    
    if chat_type == "private":
        # В личке всегда отвечаем
        should_reply = True
        cleaned_text = original_text
    else:
        # В группе проверяем условия
        if should_respond(original_text, username):
            should_reply = True
        elif message.reply_to_message and message.reply_to_message.from_user.id == context.bot.id:
            # Ответ на сообщение бота
            should_reply = True
        
        # Очищаем текст от триггеров
        cleaned_text = clean_message_text(original_text, username)
    
    if not should_reply or not cleaned_text:
        return
    
    # Показываем "печатает..."
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )
    
    logger.info(f"Отвечаю user_id {user_id} ({chat_type}): {original_text[:50]}...")
    
    try:
        response = await get_ai_response(user_id, cleaned_text)
        
        await message.reply_text(
            response,
            reply_to_message_id=message.message_id if chat_type != "private" else None
        )
        
    except Exception as e:
        logger.error(f"Ошибка обработки: {str(e)}", exc_info=True)
        await message.reply_text(
            "😕 Что-то пошло не так. Попробуй еще раз.",
            reply_to_message_id=message.message_id if chat_type != "private" else None
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Глобальный обработчик ошибок"""
    logger.error(f"Ошибка в боте: {context.error}", exc_info=True)
    
    if update and update.effective_message:
        try:
            await update.effective_message.reply_text("❌ Ошибка обработки сообщения")
        except:
            pass

async def post_init(application: Application):
    """Функция, вызываемая после инициализации бота"""
    global bot_username
    bot_username = application.bot.username
    logger.info(f"✅ Бот инициализирован. Username: @{bot_username}")

# --- Запуск ---
def main():
    # Создаем приложение
    app = Application.builder().token(TOKEN).build()
    
    # Устанавливаем обработчик post_init
    app.post_init = post_init
    
    # Команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("time", time))
    app.add_handler(CommandHandler("clear", clear))
    
    # Текстовые сообщения
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Обработчик ошибок
    app.add_error_handler(error_handler)
    
    logger.info("🚀 Запускаю бота Секон...")
    
    # Запускаем
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )

if __name__ == "__main__":
    main()
