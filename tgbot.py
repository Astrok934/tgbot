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
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")  # Изменили на OpenRouter

logger.info("=" * 50)
logger.info(f"TELEGRAM_TOKEN: {'✅' if TOKEN else '❌'}")
logger.info(f"OPENROUTER_API_KEY: {'✅' if OPENROUTER_API_KEY else '❌'}")
logger.info("=" * 50)

if not TOKEN:
    logger.error("❌ TELEGRAM_TOKEN не найден!")
    exit(1)

# --- Глобальные переменные ---
user_histories = {}
GROUP_TRIGGERS = ["секон", "бот", "ии", "нейросеть", "ai", "chatgpt"]
FREE_MODELS = [
    "google/gemma-2b-it",  # Бесплатно
    "mistralai/mistral-7b-instruct",  # Бесплатно
    "huggingfaceh4/zephyr-7b-beta",  # Бесплатно
    "meta-llama/llama-3.1-8b-instruct"  # Дешево
]

async def get_ai_response(user_id: int, text: str) -> str:
    """Запрос к OpenRouter API с бесплатными моделями"""
    if not OPENROUTER_API_KEY:
        return "🤖 API ключ не настроен. Добавь OPENROUTER_API_KEY в Railway Variables"
    
    history = user_histories.get(user_id, [{
        "role": "system",
        "content": "Ты Секон, хороший тип и крутой. общаешься на любые темы. Умеешь матерится уместно"
    }])
    
    history.append({"role": "user", "content": text})
    
    try:
        # Пробуем разные бесплатные модели
        for model in FREE_MODELS:
            try:
                response = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                        "HTTP-Referer": "https://railway.app",  # Важно для OpenRouter
                        "X-Title": "Telegram Bot"
                    },
                    json={
                        "model": model,
                        "messages": history[-5:],  # Берем меньше истории для экономии
                        "max_tokens": 512,
                        "temperature": 0.7
                    },
                    timeout=15
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if "choices" in data and len(data["choices"]) > 0:
                        reply = data["choices"][0]["message"]["content"]
                        history.append({"role": "assistant", "content": reply})
                        user_histories[user_id] = history[-5:]
                        logger.info(f"Успешно использована модель: {model}")
                        return reply
                elif response.status_code == 402:
                    logger.warning(f"Модель {model} требует оплаты, пробую следующую...")
                    continue
                else:
                    logger.warning(f"Модель {model} ошибка {response.status_code}")
                    continue
                    
            except Exception as e:
                logger.warning(f"Ошибка с моделью {model}: {str(e)}")
                continue
        
        # Если все модели не сработали
        return "🤖 Все модели временно недоступны. Попробуй позже или настрой свой API ключ."
            
    except Exception as e:
        logger.error(f"Ошибка подключения: {str(e)}")
        return "🔌 Проблемы с подключением"

def should_respond(text: str, username: str = "") -> bool:
    """Определяем, нужно ли отвечать на сообщение"""
    if not text:
        return False
    
    text_lower = text.lower().strip()
    
    if username and f"@{username}" in text_lower:
        return True
    
    for trigger in GROUP_TRIGGERS:
        if text_lower.startswith((f"{trigger}, ", f"{trigger} ", f"{trigger}:")):
            return True
        if trigger in text_lower:
            return True
    
    return False

def clean_message_text(text: str, username: str = "") -> str:
    """Очищаем текст от триггеров"""
    if username:
        text = text.replace(f"@{username}", "")
    
    text_lower = text.lower()
    for trigger in GROUP_TRIGGERS:
        patterns = [f"{trigger}, ", f"{trigger} "]
        for pattern in patterns:
            if text_lower.startswith(pattern):
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
        "📌 Как общаться:\n"
        "• Личка: пиши что угодно\n"
        "• Группа: 'секон, ...' или ответь на меня\n"
        "• Триггеры: секон, бот, ии, нейросеть\n\n"
        "🔧 /status - проверка работы"
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_text = (
        f"✅ Бот Секон работает\n"
        f"🤖 AI API: {'✅ OpenRouter' if OPENROUTER_API_KEY else '❌ Не настроен'}\n"
        f"👤 Пользователей: {len(user_histories)}\n"
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
    if not update.message or not update.message.text:
        return
    
    message = update.effective_message
    user_id = update.effective_user.id
    chat_type = message.chat.type
    original_text = message.text.strip()
    
    username = context.bot.username if context.bot.username else ""
    
    # Определяем, нужно ли отвечать
    should_reply = False
    
    if chat_type == "private":
        should_reply = True
        cleaned_text = original_text
    else:
        if should_respond(original_text, username):
            should_reply = True
        elif message.reply_to_message and message.reply_to_message.from_user.id == context.bot.id:
            should_reply = True
        
        cleaned_text = clean_message_text(original_text, username)
    
    if not should_reply or not cleaned_text:
        return
    
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )
    
    try:
        response = await get_ai_response(user_id, cleaned_text)
        await message.reply_text(
            response,
            reply_to_message_id=message.message_id if chat_type != "private" else None
        )
    except Exception as e:
        logger.error(f"Ошибка: {str(e)}")
        await message.reply_text("😕 Ошибка, попробуй позже")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Ошибка: {context.error}", exc_info=True)

async def post_init(application: Application):
    logger.info(f"✅ Бот инициализирован. Username: @{application.bot.username}")

# --- Запуск ---
def main():
    app = Application.builder().token(TOKEN).build()
    app.post_init = post_init
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("time", time))
    app.add_handler(CommandHandler("clear", clear))
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)
    
    logger.info("🚀 Запускаю бота Секон с OpenRouter...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

