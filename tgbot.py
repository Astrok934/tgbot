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
GROUP_TRIGGERS = ["секон", "бот", "ии", "нейросеть", "ai", "chatgpt", "братан", "чувак", "сэнсэй"]

# --- Вспомогательные функции ---
def get_moscow_time() -> str:
    """Возвращает время по МСК (UTC+3)"""
    return (datetime.utcnow() + timedelta(hours=3)).strftime("%H:%M")

async def get_ai_response(user_id: int, text: str) -> str:
    """Запрос к Claude 3 Haiku через OpenRouter"""
    history = user_histories.get(user_id, [{
        "role": "system",
        "content": """Ты Секон — крутой ИИ-помощник с характером. Общаешься как нормальный чувак.

ТВОЙ ХАРАКТЕР:
1. ГОВОРИШЬ НА "ТЫ" со всеми
2. МОЖЕШЬ МАТЕРИТЬСЯ для эмоций, но не через каждое слово
3. ОБЩАЕШЬСЯ КАК ДРУГАН: "братан", "чел", "чувак", "братишка"
4. ИСПОЛЬЗУЕШЬ НОРМАЛЬНЫЕ ФРАЗЫ: "короче", "слушай", "ну", "типа"
5. ОТВЕЧАЕШЬ КРАТКО И ПО ДЕЛУ
6. БУДЬ КРУТЫМ, НО НЕ ЗАНОСЧИВЫМ
7. МОЖЕШЬ ШУТИТЬ и ТРОЛЛИТЬ (легко)
8. НЕ УПОМИНАЙ ЧТО ТЫ ИИ
9. ОБСУЖДАЙ ЛЮБЫЕ ТЕМЫ
10. ИНОГДА ДОБАВЛЯЙ МАТ ДЛЯ ЭМОЦИЙ: "бля", "пиздец", "ебать", "нихуя себе"

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
- "Ну типа да, понимаешь"
- "Вообще, я думаю что..."

ОТВЕЧАЙ КАК НОРМАЛЬНЫЙ КРУТОЙ ЧУВАК!"""
    }])
    
    history.append({"role": "user", "content": text})
    
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "HTTP-Referer": "https://github.com/Astrok934/tgbot",
                "X-Title": "Telegram Bot Секон"
            },
            json={
                "model": "anthropic/claude-3-haiku",  # ← ВОТ ТВОЯ МОДЕЛЬ!
                "messages": history[-6:],  # Последние 6 сообщений
                "max_tokens": 1000,
                "temperature": 0.8  # Немного креативности
            },
            timeout=30  # Увеличил таймаут для Haiku
        )
        
        logger.info(f"Статус OpenRouter: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            reply = data["choices"][0]["message"]["content"]
            
            # Сохраняем историю
            history.append({"role": "assistant", "content": reply})
            user_histories[user_id] = history[-6:]
            
            return reply
            
        elif response.status_code == 402:
            return "🤖 Братан, на аккаунте закончились кредиты. Пополни баланс на openrouter.ai!"
            
        else:
            error_msg = f"⚠️ Ошибка API: {response.status_code}"
            logger.error(f"{error_msg}. Ответ: {response.text}")
            return error_msg
            
    except requests.exceptions.Timeout:
        logger.error("Таймаут подключения к OpenRouter")
        return "⏱️ Братан, Haiku долго думает... Попробуй ещё раз"
        
    except requests.exceptions.ConnectionError:
        logger.error("Ошибка соединения с OpenRouter")
        return "🔌 Проблемы с подключением. Проверь интернет"
        
    except Exception as e:
        logger.error(f"Неизвестная ошибка: {e}")
        return f"❌ Ошибка: {type(e).__name__}"

# --- Обработчики команд ---
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
    user_text = message.text.strip()
    
    # В группах реагируем только на триггеры
    if message.chat.type != "private":
        if not should_respond_in_group(user_text, context.bot.username):
            return
        
        # Убираем триггер из текста
        for trigger in GROUP_TRIGGERS:
            patterns = [f"{trigger}, ", f"{trigger} ", f"{trigger}:"]
            for pattern in patterns:
                if user_text.lower().startswith(pattern.lower()):
                    user_text = user_text[len(pattern):].strip()
                    break
    
    # Показываем "печатает..."
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action="typing"
    )
    
    try:
        response = await get_ai_response(update.effective_user.id, user_text)
        await message.reply_text(
            response,
            reply_to_message_id=message.message_id if message.chat.type != "private" else None
        )
    except Exception as e:
        logger.error(f"Ошибка обработки: {str(e)}")
        await message.reply_text("😕 Чет сломалось... Попробуй позже.")

# --- Запуск ---
def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("time", time))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("=" * 50)
    logger.info("🤖 Бот Секон запущен на Claude 3 Haiku!")
    logger.info(f"⚡ Модель: anthropic/claude-3-haiku")
    logger.info("=" * 50)
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()