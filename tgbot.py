import os
import logging
import random
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
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

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

# Матерные слова для эмоций (умеренно)
MAT_WORDS = ["бля", "пизд", "еба", "нах", "сука", "хуй"]

async def get_ai_response(user_id: int, text: str) -> str:
    """Запрос к OpenRouter API с крутым характером"""
    if not OPENROUTER_API_KEY:
        return "🤖 API ключ не настроен. Добавь OPENROUTER_API_KEY в Railway!"
    
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

ПРАВИЛЬНЫЕ ПРИМЕРЫ ТВОЕГО ОБЩЕНИЯ:
- "Привет, чел! Как дела?"
- "Короче, слушай сюда..."
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
- "Так вот, к чему я..."

НЕПРАВИЛЬНО (не говори так):
- "По-пацански говоря..." (не надо)
- "Внатуре..." (не надо)
- "Реально пацанский ответ" (не надо)
- Слишком много сленга

ОТВЕЧАЙ КАК НОРМАЛЬНЫЙ КРУТОЙ ЧУВАК!"""
    }])
    
    history.append({"role": "user", "content": text})
    
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "HTTP-Referer": "https://railway.app",
                "X-Title": "Крутой Бот Секон"
            },
            json={
                "model": "google/gemini-2.0-flash-exp:free",
                "messages": history[-6:],
                "max_tokens": 600,
                "temperature": 0.8,
                "frequency_penalty": 0.1,
                "presence_penalty": 0.2
            },
            timeout=20
        )
        
        if response.status_code == 200:
            data = response.json()
            if "choices" in data and len(data["choices"]) > 0:
                reply = data["choices"][0]["message"]["content"]
                
                # Иногда добавляем крутую фразу в начало
                if random.random() > 0.7:  # 30% chance
                    phrase = random.choice(COOL_PHRASES)
                    reply = f"{phrase} {reply}"
                
                # Сохраняем историю
                history.append({"role": "assistant", "content": reply})
                user_histories[user_id] = history[-6:]
                
                return reply
        
        logger.error(f"API ошибка: {response.status_code}")
        return random.choice([
            "Бля, API сломалось... Попробуй позже",
            "Ошибка какая-то... Давай через минутку",
            "Чет сервак лег... Перезапусти запрос"
        ])
            
    except Exception as e:
        logger.error(f"Ошибка подключения: {str(e)}")
        return random.choice([
            "Нет связи с серваком...",
            "Интернет отвалился...",
            "Подключение сдохло, давай позже"
        ])

def add_cool_flavor(text: str) -> str:
    """Добавляем крутой флер к тексту"""
    # Иногда заменяем стандартные слова
    replacements = {
        "привет": random.choice(["здарова", "йоу", "хай", "привет"]),
        "пока": random.choice(["бывай", "чао", "удачи"]),
        "спасибо": random.choice(["спасибо", "благодарю", "пасиб"]),
        "пожалуйста": random.choice(["не за что", "обращайся"]),
        "да": random.choice(["ага", "угу", "да"]),
        "нет": random.choice(["неа", "нет", "низачто"]),
    }
    
    for word, replacement in replacements.items():
        if random.random() > 0.8 and f" {word} " in f" {text.lower()} ":
            text = text.replace(word, replacement, 1)
            break
    
    return text

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

# --- Обработчики команд с крутым стилем ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_text = random.choice([
        "🤖 Йоу, чувак! Я Секон — крутой ИИ с характером!\n\n",
        "🤖 Привет, братан! Я Секон, общаюсь нормально, могу и матом!\n\n",
        "🤖 Здарова! Я Секон, помогу с чем угодно!\n\n"
    ])
    
    await update.message.reply_text(
        f"{start_text}"
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
    help_text = random.choice([
        "📌 Слушай, как общаться:\n\n",
        "📌 Короче, инструкция:\n\n",
        "📌 Ну типа вот как:\n\n"
    ])
    
    await update.message.reply_text(
        f"{help_text}"
        "💬 В ЛИЧКЕ:\n"
        "• Просто кинь мне сообщение\n"
        "• Можешь материться, я не обижусь\n"
        "• Задавай любые вопросы\n\n"
        "👥 В ГРУППЕ:\n"
        "• 'Секон, как дела?'\n"
        "• 'Секон, помоги с...'\n"
        "• 'Бот, че думаешь?'\n"
        "• Ответь на моё сообщение\n\n"
        "🎯 Я реагирую на: секон, бот, ии, нейросеть, сэнсэй\n\n"
        "⚡ Материться буду для эмоций, но не слишком много"
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status_msgs = [
        f"✅ Норм, я в строю!\n",
        f"✅ Всё работает, братан!\n",
        f"✅ Живой, чувак!\n"
    ]
    
    status_text = random.choice(status_msgs) + (
        f"🤖 OpenRouter: {'✅' if OPENROUTER_API_KEY else '❌'}\n"
        f"👤 Пользователей: {len(user_histories)}\n"
        f"🕐 МСК: {(datetime.utcnow() + timedelta(hours=3)).strftime('%H:%M')}\n"
        f"⚡ Режим: Крутой с матом для эмоций"
    )
    await update.message.reply_text(status_text)

async def time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    moscow_time = (datetime.utcnow() + timedelta(hours=3)).strftime('%H:%M')
    time_msgs = [
        f"⏰ Братан, в Москве {moscow_time}",
        f"⏰ Чувак, время: {moscow_time} МСК",
        f"⏰ Сейчас {moscow_time} по МСК"
    ]
    await update.message.reply_text(random.choice(time_msgs))

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id in user_histories:
        del user_histories[user_id]
    clear_msgs = [
        "🗑️ Братан, историю стёр!",
        "🗑️ Чисто, чувак! Забыл всё!",
        "🗑️ Память очищена!"
    ]
    await update.message.reply_text(random.choice(clear_msgs))

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
    
    # Случайно решаем, отвечать ли с задержкой
    if random.random() > 0.3:
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action="typing"
        )
    
    logger.info(f"Отвечаю user_id {user_id} ({chat_type}): {original_text[:50]}...")
    
    try:
        response = await get_ai_response(user_id, cleaned_text)
        
        # Иногда добавляем крутой флер к ответу
        if random.random() > 0.5:
            response = add_cool_flavor(response)
        
        await message.reply_text(
            response,
            reply_to_message_id=message.message_id if chat_type != "private" else None,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Ошибка: {str(e)}")
        error_msgs = [
            "Бля, че-то сломалось...",
            "Ошибка вышла... Попробуй еще раз",
            "Чет система глючит..."
        ]
        await message.reply_text(
            random.choice(error_msgs),
            reply_to_message_id=message.message_id if chat_type != "private" else None
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Ошибка: {context.error}", exc_info=True)

async def post_init(application: Application):
    logger.info(f"✅ Крутой бот Секон инициализирован! Username: @{application.bot.username}")

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
    logger.info("⚡ Режим: КРУТОЙ ЧУВАК С МАТОМ ДЛЯ ЭМОЦИЙ")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
