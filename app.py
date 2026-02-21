import asyncio
import random
import logging
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from google import genai

# --- [КОНФИГУРАЦИЯ] ---
TG_TOKEN = "8373543507:AAE1t-rrq76Q87vfWTM0DneXjMB4kRyKIPU"
GEMINI_KEY = "AIzaSyDORp2NgBtbud0j0ITDT694pkbF4wR4igQ"
BOT_NAME = "RID3 AI"
BOT_USERNAME = "@rid3_ai_bot"

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация клиентов
client = genai.Client(api_key=GEMINI_KEY)
bot = Bot(token=TG_TOKEN, default=DefaultBotProperties(parse_mode='Markdown'))
dp = Dispatcher()

# Хранилище лимитов {user_id: [timestamps]}
user_limits = {}

def check_limit(user_id):
    now = datetime.now()
    if user_id not in user_limits:
        user_limits[user_id] = []
    
    # Очистка старых записей (старше 1 часа)
    user_limits[user_id] = [t for t in user_limits[user_id] if now - t < timedelta(hours=1)]
    
    if len(user_limits[user_id]) >= 5:
        wait_sec = int((user_limits[user_id][0] + timedelta(hours=1) - now).total_seconds())
        return False, max(1, wait_sec // 60)
    
    user_limits[user_id].append(now)
    return True, 0

# --- [ОБРАБОТЧИКИ КОМАНД] ---

@dp.message(Command("start"))
async def cmd_start(m: types.Message):
    await m.answer(f"👋 Привет! Я — **{BOT_NAME}**, запущен на Render!\nИспользуй /help для списка команд.")

@dp.message(Command("help"))
async def cmd_help(m: types.Message):
    await m.answer(
        f"❓ **Команды {BOT_NAME}:**\n"
        f"• /dill — Инструкция\n"
        f"• /support — Поддержка\n"
        f"• /s — Статус системы\n\n"
        f"Чтобы поговорить со мной, пиши: `{BOT_NAME}: [вопрос]`"
    )

@dp.message(Command("dill"))
async def cmd_dill(m: types.Message):
    await m.answer(
        f"🤖 **Инструкция {BOT_NAME}:**\n"
        f"1. Я отвечаю на `{BOT_NAME}: ...` или тег {BOT_USERNAME}.\n"
        f"2. Поиск: `{BOT_NAME} ПОИСК: [тема]`.\n"
        f"3. Контекст: отвечай на мои сообщения через 'Reply'.\n"
        f"4. Лимит: 5 запросов в час."
    )

@dp.message(Command("support"))
async def cmd_support(m: types.Message):
    await m.answer("🛠 **Поддержка:** @artyom228091")

@dp.message(Command("s"))
async def cmd_settings(m: types.Message):
    await m.answer(f"⚙️ **Статус:** 🟢 Online\n**Платформа:** Render.com\n**Ядро:** Gemini 2.0 Flash")

# --- [ОСНОВНАЯ ЛОГИКА ИИ] ---

@dp.message(F.text)
async def handle_ai(m: types.Message):
    if not m.text: return
    user_id = m.from_user.id
    
    # Проверка триггеров обращения
    triggers = [f"{BOT_NAME}:", f"{BOT_NAME} ПОИСК:", BOT_NAME, BOT_USERNAME]
    is_addressed = any(m.text.startswith(t) for t in triggers) or \
                   (m.reply_to_message and m.reply_to_message.from_user.id == bot.id)

    if not is_addressed:
        if random.random() < 0.01:
            await m.answer("Я рядом! Будут вопросы — пиши. 😉")
        return

    # Проверка лимита (5/час)
    ok, wait = check_limit(user_id)
    if not ok:
        await m.reply(f"⏳ **Лимит!**\nЯ смогу ответить тебе через **{wait} мин.**")
        return

    # Подготовка текста для ИИ
    is_search = "ПОИСК:" in m.text
    prompt = m.text
    for t in triggers:
        prompt = prompt.replace(t, "")
    prompt = prompt.strip()

    try:
        # Системная инструкция
        sys_msg = f"Ты — {BOT_NAME}, мощный ИИ-помощник. Отвечай кратко, грамотно и по делу."
        if is_search: sys_msg += " Твоя цель — поиск актуальной информации."

        # Запрос к Gemini
        response = client.models.generate_content(
            model="gemini-2.0-flash", 
            contents=f"{sys_msg}\n\nПользователь: {prompt}"
        )
        
        if response and response.text:
            await m.reply(response.text)
        else:
            await m.reply("🤖 Google AI не прислал текст. Попробуй еще раз.")

    except Exception as e:
        if "429" in str(e):
            logging.warning("Gemini Rate Limit Hit (429)")
            await m.reply("⚠️ **Ошибка лимита ИИ.**\nGoogle временно ограничил запросы. Подожди 1-2 минуты.")
        else:
            logging.error(f"AI ERROR: {e}")
            await m.reply("🔧 Произошла ошибка в ядре ИИ. Попробуй позже.")

# --- [ЗАПУСК] ---

async def main():
    print(f"--- {BOT_NAME} ЗАПУСКАЕТСЯ НА RENDER ---")
    
    # 1. Удаляем вебхук и ОЧИЩАЕМ очередь сообщений (drop_pending_updates)
    # Это нужно, чтобы бот не спамил ответами на старые сообщения при старте
    await bot.delete_webhook(drop_pending_updates=True)
    
    # 2. Запуск опроса серверов Telegram
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
