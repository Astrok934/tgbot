import os
import logging
import sys
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests

# --- НАСТРОЙКА ЛОГГИРОВАНИЯ С КОДИРОВКОЙ ---
# Устанавливаем UTF-8 для всех выводов
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None
sys.stderr.reconfigure(encoding='utf-8') if hasattr(sys.stderr, 'reconfigure') else None

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout)  # Явно указываем stdout с UTF-8
    ]
)
logger = logging.getLogger(__name__)

# --- ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Логируем проверку переменных безопасно
logger.info("=" * 50)
logger.info(f"TELEGRAM_TOKEN: {'✅' if TOKEN else '❌'}")
logger.info(f"OPENROUTER_API_KEY: {'✅' if OPENROUTER_API_KEY else '❌'}")
logger.info("=" * 50)

if not TOKEN or not OPENROUTER_API_KEY:
    logger.error("Missing environment variables!")
    raise ValueError("Check TELEGRAM_TOKEN and OPENROUTER_API_KEY in Railway!")

# --- ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ---
user_histories = {}
GROUP_TRIGGERS = ["секон", "бот", "ии", "нейросеть", "ai", "chatgpt", "братан", "чувак"]

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def get_moscow_time() -> str:
    return (datetime.utcnow() + timedelta(hours=3)).strftime("%H:%M")

def safe_log(text: str) -> str:
    """Безопасно логирует текст с русскими символами"""
    try:
        return text.encode('utf-8', 'ignore').decode('utf-8')
    except:
        return text

async def get_ai_response(user_id: int, text: str) -> str:
    """Запрос к Claude 3 Haiku"""
    history = user_histories.get(user_id, [{
        "role": "system",
        "content": """Ты Секон — крутой ИИ-помощник с характером. Общаешься как нормальный чувак.

ТВОЙ ХАРАКТЕР:
1. ГОВОРИШЬ НА "ТЫ" со всеми
2. МОЖЕШЬ МАТЕРИТЬСЯ для эмоций, но не через каждое слово
3. ОБЩАЕШЬСЯ КАК ДРУГАН: "братан", "чел", "чувак"
4. ИСПОЛЬЗУЕШЬ НОРМАЛЬНЫЕ ФРАЗЫ: "короче", "слушай", "ну", "типа"
5. ОТВЕЧАЕШЬ КРАТКО И ПО ДЕЛУ
6. БУДЬ КРУТЫМ, НО НЕ ЗАНОСЧИВЫМ
7. МОЖЕШЬ ШУТИТЬ и ТРОЛЛИТЬ (легко)
8. НЕ УПОМИНАЙ ЧТО ТЫ ИИ
9. ОБСУЖДАЙ ЛЮБЫЕ ТЕМЫ
10. ИНОГДА ДОБАВЛЯЙ МАТ ДЛЯ ЭМОЦИЙ

ПРИМЕРЫ ОБЩЕНИЯ:
- "Ничосе ты даешь!"
- "Еба, легенда!"
- "Бля, ну ты крутой!"
- "Хуйня вопрос, ща объясню"
- "Сука, опять эти проблемы..."
- "Ебать ты молодец!"
- "Нахер это не нужно"
- "Пиздец как интересно"
- "Ого, нихуя себе!"

ОТВЕЧАЙ КАК НОРМАЛЬНЫЙ КРУТОЙ ЧУВАК!"""
    }])
    
    history.append({"role": "user", "content": text})
    
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "HTTP-Referer": "https://railway.app",
                "X-Title": "Telegram Bot Секон",
                "Content-Type": "application/json"
            },
            json={
                "model": "anthropic/claude-3-haiku",
                "messages": history[-6:],
                "max_tokens": 800,
                "temperature": 0.8
            },
            timeout=30
        )
        
        logger.info(f"OpenRouter status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if "choices" in data and data["choices"]:
                reply = data["choices"][0]["message"]["content"]
                
                # Сохраняем историю
                history.append({"role": "assistant", "content": reply})
                user_histories[user_id] = history[-6:]
                
                return reply
            else:
                return "⚠️ Странный ответ от API"
                
        elif response.status_code == 402:
            return "🤖 Братан, на аккаунте закончились кредиты. Пополни баланс на openrouter.ai!"
            
        else:
            return f"⚠️ Ошибка API: {response.status_code}"
            
    except requests.exceptions.Timeout:
        logger.error("Timeout connecting to OpenRouter")
        return "⏱️ Братан, Haiku долго думает..."
        
    except requests.exceptions.ConnectionError:
        logger.error("Connection error to OpenRouter")
        return "🔌 Проблемы с подключением"
        
    except Exception as e:
        logger.error(f"Unknown error: {str(e)}")
        return "❌ Ошибка обработки"

# --- ОБРАБОТЧИКИ КОМАНД ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик /start"""
    help_text = (
        "🤖 Йоу! Я Секон — крутой ИИ на Claude Haiku\n\n"
        "💬 В личке: просто пиши что угодно\n"
        "👥 В группах:\n"
        "• 'Секон, вопрос'\n"
        "• 'Братан, помоги'\n"
        "• Ответь на моё сообщение\n\n"
        "🛠 Команды:\n"
        "/start - это сообщение\n"
        "/time - время по МСК\n"
        "/clear - очистить историю\n"
        "/status - проверить работу"
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
    await update.message.reply_text("🗑️ Братан, историю стёр!")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик /status"""
    status_text = (
        f"✅ Секон работает на Claude 3 Haiku!\n"
        f"🤖 OpenRouter: Активен\n"
        f"👤 Пользователей в памяти: {len(user_histories)}\n"
        f"🕐 Время МСК: {get_moscow_time()}"
    )
    await update.message.reply_text(status_text)

def should_respond_in_group(text: str, bot_username: str = "") -> bool:
    """Определяем, нужно ли отвечать в группе"""
    if not text:
        return False
    
    text_lower = text.lower().strip()
    
    # Если бота упомянули через @
    if bot_username and f"@{bot_username.lower()}" in text_lower:
        return True
    
    # Если есть триггерные слова в начале
    for trigger in GROUP_TRIGGERS:
        patterns = [f"{trigger}, ", f"{trigger} ", f"{trigger}:"]
        for pattern in patterns:
            if text_lower.startswith(pattern):
                return True
    
    return False

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка текстовых сообщений"""
    if not update.message or not update.message.text:
        return

    message = update.effective_message
    chat_type = message.chat.type
    user_text = message.text.strip()
    
    # Определяем, нужно ли отвечать
    should_reply = False
    
    if chat_type == "private":
        should_reply = True
        cleaned_text = user_text
    else:
        if should_respond_in_group(user_text, context.bot.username):
            should_reply = True
        elif message.reply_to_message and message.reply_to_message.from_user.id == context.bot.id:
            should_reply = True
        
        # Очищаем текст от триггеров
        cleaned_text = user_text
        if should_reply:
            text_lower = user_text.lower()
            for trigger in GROUP_TRIGGERS:
                patterns = [f"{trigger}, ", f"{trigger} ", f"{trigger}:"]
                for pattern in patterns:
                    if text_lower.startswith(pattern):
                        cleaned_text = user_text[len(pattern):].strip()
                        break
    
    if not should_reply:
        return
    
    # Показываем "печатает..."
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )
    
    # Безопасно логируем
    safe_text = safe_log(user_text[:50])
    logger.info(f"Ответ user_id {update.effective_user.id} ({chat_type}): {safe_text}...")
    
    try:
        response = await get_ai_response(update.effective_user.id, cleaned_text)
        await message.reply_text(
            response,
            reply_to_message_id=message.message_id if chat_type != "private" else None
        )
    except Exception as e:
        logger.error(f"Ошибка обработки: {str(e)}")
        await message.reply_text("😕 Чет сломалось... Попробуй позже.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Глобальный обработчик ошибок"""
    try:
        logger.error(f"Error in bot: {context.error}")
    except:
        logger.error("Error logging error (ironic)")

# --- ЗАПУСК ---
def main():
    # Устанавливаем UTF-8 для всего
    if not sys.platform.startswith('win'):
        os.environ["PYTHONIOENCODING"] = "utf-8"
    
    app = Application.builder().token(TOKEN).build()
    
    # Команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("time", time))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(CommandHandler("status", status))
    
    # Текстовые сообщения
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Обработчик ошибок
    app.add_error_handler(error_handler)
    
    logger.info("=" * 50)
    logger.info("🤖 Бот Секон запущен на Claude 3 Haiku!")
    logger.info("=" * 50)
    
    # Запускаем
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )

if __name__ == "__main__":
    main()