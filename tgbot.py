import os
import logging
import sys
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import requests

# --- ФИКС КОДИРОВКИ ДЛЯ RAILWAY ---
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None
sys.stderr.reconfigure(encoding='utf-8') if hasattr(sys.stderr, 'reconfigure') else None

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# --- ПЕРЕМЕННЫЕ ---
TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

# Проверка
logger.info("=== НАЧАЛО ИНИЦИАЛИЗАЦИИ ===")
logger.info(f"TOKEN есть: {bool(TOKEN)}")
logger.info(f"OPENROUTER_KEY есть: {bool(OPENROUTER_API_KEY)}")

if not TOKEN:
    logger.error("НЕТ ТОКЕНА TELEGRAM!")
    sys.exit(1)

if not OPENROUTER_API_KEY:
    logger.warning("НЕТ КЛЮЧА OPENROUTER! Будет эхо-режим")

# --- ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ---
user_histories = {}
GROUP_TRIGGERS = ["секон", "бот", "ии", "нейросеть"]

# --- ФУНКЦИИ ---
def get_moscow_time():
    return (datetime.utcnow() + timedelta(hours=3)).strftime("%H:%M")

async def get_ai_response(user_id: int, text: str) -> str:
    """Основная функция запроса к Haiku"""
    logger.info(f"Запрос от user_id {user_id}: {text[:50]}...")
    
    # Инициализируем историю
    if user_id not in user_histories:
        user_histories[user_id] = [{
            "role": "system",
            "content": "Ты Секон, крутой помощник. Можешь материться для эмоций, но не слишком. Общаешься как друг: 'братан', 'чел'. Примеры: 'Ничосе ты даешь!', 'Еба, легенда!', 'Бля, ну ты крутой!'"
        }]
    
    # Добавляем сообщение пользователя
    user_histories[user_id].append({"role": "user", "content": text})
    
    # Если нет API ключа - эхо
    if not OPENROUTER_API_KEY:
        return f"Эхо: {text} (API ключ не настроен)"
    
    try:
        logger.info("Отправляю запрос к OpenRouter...")
        
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "anthropic/claude-3-haiku",
                "messages": user_histories[user_id][-5:],  # Последние 5 сообщений
                "max_tokens": 500
            },
            timeout=25
        )
        
        logger.info(f"Ответ OpenRouter: статус {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            reply = data["choices"][0]["message"]["content"]
            
            # Сохраняем ответ в историю
            user_histories[user_id].append({"role": "assistant", "content": reply})
            
            # Ограничиваем историю
            if len(user_histories[user_id]) > 10:
                user_histories[user_id] = user_histories[user_id][-10:]
            
            logger.info("Успешно получил ответ от AI")
            return reply
            
        elif response.status_code == 402:
            return "🤖 Братан, нужны кредиты на openrouter.ai"
            
        else:
            error_text = response.text[:200] if response.text else "нет текста"
            logger.error(f"OpenRouter error {response.status_code}: {error_text}")
            return f"⚠️ Ошибка {response.status_code}"
            
    except requests.exceptions.Timeout:
        logger.error("Таймаут запроса")
        return "⏱️ Долго думает..."
    except requests.exceptions.ConnectionError:
        logger.error("Ошибка соединения")
        return "🔌 Нет связи с сервером"
    except Exception as e:
        logger.error(f"Неизвестная ошибка в get_ai_response: {str(e)}")
        return f"❌ Ошибка: {type(e).__name__}"

# --- ОБРАБОТЧИКИ КОМАНД ---
async def start(update: Update, context):
    await update.message.reply_text(
        "🤖 Привет! Я Секон\n"
        "Пиши в личке или в группе: 'секон, вопрос'\n"
        "/time - время\n"
        "/clear - очистить память"
    )

async def time(update: Update, context):
    await update.message.reply_text(f"⏰ МСК: {get_moscow_time()}")

async def clear(update: Update, context):
    user_id = update.effective_user.id
    if user_id in user_histories:
        del user_histories[user_id]
    await update.message.reply_text("🗑️ Очищено!")

# --- ОБРАБОТЧИК СООБЩЕНИЙ ---
async def handle_message(update: Update, context):
    """ОСНОВНОЙ ОБРАБОТЧИК"""
    logger.info("=== НАЧАЛО ОБРАБОТКИ СООБЩЕНИЯ ===")
    
    try:
        # 1. Получаем данные
        message = update.effective_message
        if not message or not message.text:
            logger.info("Нет текста в сообщении")
            return
            
        user_id = update.effective_user.id
        chat_type = message.chat.type
        text = message.text.strip()
        
        logger.info(f"Сообщение: user_id={user_id}, chat_type={chat_type}, text={text[:50]}...")
        
        # 2. Проверяем, нужно ли отвечать в группе
        if chat_type in ["group", "supergroup"]:
            text_lower = text.lower()
            should_respond = False
            
            # Проверяем триггеры
            for trigger in GROUP_TRIGGERS:
                if text_lower.startswith(f"{trigger}, ") or text_lower.startswith(f"{trigger} "):
                    should_respond = True
                    # Убираем триггер
                    text = text[len(trigger):].lstrip(", ").strip()
                    break
            
            # Проверяем ответ на сообщение бота
            if not should_respond and message.reply_to_message:
                if message.reply_to_message.from_user.id == context.bot.id:
                    should_respond = True
            
            if not should_respond:
                logger.info("Не нужно отвечать в группе")
                return
        
        # 3. Отправляем действие "печатает"
        try:
            await context.bot.send_chat_action(
                chat_id=update.effective_chat.id,
                action="typing"
            )
        except Exception as e:
            logger.warning(f"Не удалось отправить chat_action: {e}")
        
        # 4. Получаем ответ от AI
        logger.info("Получаю ответ от AI...")
        ai_response = await get_ai_response(user_id, text)
        logger.info(f"Ответ AI готов: {ai_response[:50]}...")
        
        # 5. Отправляем ответ
        reply_to_id = None if chat_type == "private" else message.message_id
        await message.reply_text(ai_response, reply_to_message_id=reply_to_id)
        
        logger.info("=== УСПЕШНО ОБРАБОТАНО ===")
        
    except Exception as e:
        logger.error(f"!!! КРИТИЧЕСКАЯ ОШИБКА В handle_message: {str(e)}", exc_info=True)
        
        # Пытаемся отправить сообщение об ошибке
        try:
            if update and update.effective_message:
                await update.effective_message.reply_text(
                    "😕 Ошибка обработки. Попробуй еще раз.",
                    reply_to_message_id=update.effective_message.message_id
                )
        except:
            logger.error("Не удалось отправить сообщение об ошибке")

# --- ЗАПУСК ---
def main():
    logger.info("=== ЗАПУСК БОТА ===")
    
    try:
        # Создаем приложение
        app = Application.builder().token(TOKEN).build()
        
        # Добавляем обработчики
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("time", time))
        app.add_handler(CommandHandler("clear", clear))
        
        # Обработчик текстовых сообщений
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        # Запускаем
        logger.info("Бот запускается...")
        app.run_polling(
            drop_pending_updates=True,
            allowed_updates=Update.ALL_TYPES,
            poll_interval=1.0,
            timeout=20
        )
        
    except Exception as e:
        logger.error(f"!!! ОШИБКА ПРИ ЗАПУСКЕ БОТА: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()