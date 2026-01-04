import os
import logging
import random
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

# Railway переменные
TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")

logger.info("=" * 50)
logger.info(f"TELEGRAM_TOKEN: {'✅' if TOKEN else '❌'}")
logger.info(f"OPENROUTER_API_KEY: {'✅' if OPENROUTER_API_KEY else '❌'}")
logger.info("=" * 50)

if not TOKEN:
    logger.error("❌ TELEGRAM_TOKEN не найден!")
    exit(1)

# --- Глобальные переменные ---
user_histories = {}
GROUP_TRIGGERS = ["секон", "бот", "ии", "нейросеть", "ai", "chatgpt", "сэнсэй"]

# Крутые фразы для добавления характера
COOL_PHRASES = [
    "Короче...", "Слушай...", "Так вот...", "Ну...", "Значит так...",
    "Кстати...", "Вообще...", "Типа...", "Понимаешь...", "В общем..."
]

async def get_ai_response_fallback(user_id: int, text: str) -> str:
    """Фолбэк ответы если API не работает"""
    fallback_responses = [
        "Чел, API временно не отвечает. Но в целом, ты прав!",
        "Братан, сервак лег. Но я с тобой согласен!",
        "Короче, API сломалось, но ты молодец что спросил!",
        "Слушай, техработы идут. Давай позже поговорим!",
        "Ну типа API не работает, но вопрос хороший!",
    ]
    
    # Простой локальный интеллект для базовых ответов
    text_lower = text.lower()
    
    if any(word in text_lower for word in ["привет", "здравствуй", "хай", "йоу"]):
        return random.choice(["Привет, братан!", "Йоу, чел!", "Здарова!", "Приветствую!"])
    
    elif any(word in text_lower for word in ["как дела", "как ты", "че как"]):
        return random.choice(["Нормально, братан! А у тебя?", "Всё чики-пуки!", "Пока не жалуюсь!", "Да вроде норм!"])
    
    elif any(word in text_lower for word in ["спасибо", "благодарю", "пасиб"]):
        return random.choice(["Не за что, братан!", "Всегда рад помочь!", "Обращайся!", "Да не вопрос!"])
    
    elif "время" in text_lower:
        moscow_time = (datetime.utcnow() + timedelta(hours=3)).strftime('%H:%M')
        return f"Братан, в Москве сейчас {moscow_time}"
    
    else:
        return random.choice(fallback_responses)

async def get_ai_response(user_id: int, text: str) -> str:
    """Основной запрос к API с несколькими провайдерами"""
    if not OPENROUTER_API_KEY:
        return await get_ai_response_fallback(user_id, text)
    
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
    
    # Пробуем разные модели OpenRouter
    models_to_try = [
        "google/gemini-2.0-flash-exp:free",
        "google/gemma-2-9b-it:free",
        "mistralai/mistral-7b-instruct:free",
        "huggingfaceh4/zephyr-7b-beta:free"
    ]
    
    for model in models_to_try:
        try:
            logger.info(f"Пробую модель: {model}")
            
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "HTTP-Referer": "https://railway.app",
                    "X-Title": "Крутой Бот Секон",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": history[-4:],  # Меньше истории для надежности
                    "max_tokens": 400,
                    "temperature": 0.8,
                },
                timeout=15  # Уменьшил таймаут
            )
            
            if response.status_code == 200:
                data = response.json()
                if "choices" in data and len(data["choices"]) > 0:
                    reply = data["choices"][0]["message"]["content"]
                    
                    # Иногда добавляем крутую фразу в начало
                    if random.random() > 0.7:
                        phrase = random.choice(COOL_PHRASES)
                        reply = f"{phrase} {reply}"
                    
                    # Сохраняем историю
                    history.append({"role": "assistant", "content": reply})
                    user_histories[user_id] = history[-6:]
                    
                    logger.info(f"Успешно использована модель: {model}")
                    return reply
            else:
                logger.warning(f"Модель {model} ошибка {response.status_code}")
                continue
                
        except requests.exceptions.Timeout:
            logger.warning(f"Таймаут на модели {model}")
            continue
        except requests.exceptions.ConnectionError:
            logger.warning(f"Ошибка соединения на модели {model}")
            continue
        except Exception as e:
            logger.warning(f"Ошибка на модели {model}: {str(e)}")
            continue
    
    # Если все модели не сработали, пробуем публичный ChatGPT API
    try:
        logger.info("Пробую публичный ChatGPT API...")
        
        response = requests.post(
            "https://chatgpt-api.shn.hk/v1/",
            json={
                "model": "gpt-3.5-turbo",
                "messages": history[-4:],
                "temperature": 0.7,
                "max_tokens": 300
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if "choices" in data and len(data["choices"]) > 0:
                reply = data["choices"][0]["message"]["content"]
                history.append({"role": "assistant", "content": reply})
                user_histories[user_id] = history[-6:]
                logger.info("Успешно использован публичный ChatGPT API")
                return reply
    except:
        pass
    
    # Если всё упало, возвращаем фолбэк
    logger.warning("Все API упали, возвращаю фолбэк")
    return await get_ai_response_fallback(user_id, text)

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
        if trigger in text_lower and len(text_lower.split()) < 10:
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
        "🤖 Йоу, братан! Я Секон — крутой ИИ с характером!\n\n"
        "💬 В личке: просто пиши что угодно\n"
        "👥 В группе: 'секон, вопрос' или ответь на меня\n\n"
        "🛠 Команды:\n"
        "/start - это сообщение\n"
        "/help - как общаться\n"
        "/status - что работает\n"
        "/time - время по МСК\n"
        "/clear - сбросить историю"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📌 Как общаться:\n\n"
        "💬 В ЛИЧКЕ:\n"
        "• Просто кинь мне сообщение\n\n"
        "👥 В ГРУППЕ:\n"
        "• 'Секон, как дела?'\n"
        "• 'Секон, помоги с...'\n"
        "• 'Бот, че думаешь?'\n"
        "• Ответь на моё сообщение\n\n"
        "🎯 Я реагирую на: секон, бот, ии, нейросеть, сэнсэй"
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_text = (
        f"✅ Всё работает, братан!\n"
        f"🤖 API: {'✅' if OPENROUTER_API_KEY else '❌'}\n"
        f"👤 Пользователей: {len(user_histories)}\n"
        f"🕐 МСК: {(datetime.utcnow() + timedelta(hours=3)).strftime('%H:%M')}\n"
        f"⚡ Режим: Крутой чувак"
    )
    await update.message.reply_text(status_text)

async def time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    moscow_time = (datetime.utcnow() + timedelta(hours=3)).strftime('%H:%M')
    await update.message.reply_text(f"⏰ Братан, в Москве {moscow_time}")

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_histories:
        del user_histories[user_id]
    await update.message.reply_text("🗑️ Братан, историю стёр!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка всех сообщений"""
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
        logger.error(f"Ошибка: {str(e)}")
        await message.reply_text(
            "Братан, чет накрылось... Давай позже!",
            reply_to_message_id=message.message_id if chat_type != "private" else None
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Ошибка: {context.error}", exc_info=True)

async def post_init(application: Application):
    logger.info(f"✅ Бот Секон запущен! Username: @{application.bot.username}")

# --- Запуск ---
def main():
    app = Application.builder().token(TOKEN).build()
    app.post_init = post_init
    
    # Команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("time", time))
    app.add_handler(CommandHandler("clear", clear))
    
    # Текстовые сообщения
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)
    
    logger.info("🚀 Запускаю крутого бота Секон...")
    app.run_polling(drop_pending_updates=True, poll_interval=1.0)

if __name__ == "__main__":
    main()