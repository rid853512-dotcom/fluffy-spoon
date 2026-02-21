import asyncio
import random
import logging
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from google import genai

# --- [КОНФИГУРАЦИЯ] ---
TG_TOKEN = "8373543507:AAEjXwmnYGcyzbgUrFnv7iMTz9KBp-l6d6c"
GEMINI_KEY = "AIzaSyDSycStAhR3mMXjl-JqsHEe08u1uWeFxZk"
BOT_NAME = "RID3 AI"
BOT_USERNAME = "@rid3_ai_bot"

logging.basicConfig(level=logging.INFO)

client = genai.Client(api_key=GEMINI_KEY)
bot = Bot(token=TG_TOKEN, default=DefaultBotProperties(parse_mode='Markdown'))
dp = Dispatcher()

user_limits = {}

def check_limit(user_id):
    now = datetime.now()
    if user_id not in user_limits: user_limits[user_id] = []
    user_limits[user_id] = [t for t in user_limits[user_id] if now - t < timedelta(hours=1)]
    if len(user_limits[user_id]) >= 5:
        wait_sec = int((user_limits[user_id][0] + timedelta(hours=1) - now).total_seconds())
        return False, max(1, wait_sec // 60)
    user_limits[user_id].append(now)
    return True, 0

@dp.message(Command("start"))
async def cmd_start(m: types.Message):
    await m.answer(f"👋 Привет! Я — **{BOT_NAME}** на Render! Напиши /help.")

@dp.message(Command("help"))
async def cmd_help(m: types.Message):
    await m.answer(f"❓ **Команды:** /dill, /support, /s\nИли просто: `{BOT_NAME}: [вопрос]`")

@dp.message(Command("dill"))
async def cmd_dill(m: types.Message):
    await m.answer(f"🤖 **Инструкция:**\n1. Обращение: `{BOT_NAME}: ...`\n2. Лимит: 5 запросов в час.")

@dp.message(Command("support"))
async def cmd_support(m: types.Message):
    await m.answer("🛠 Поддержка: @artyom228091")

@dp.message(Command("s"))
async def cmd_settings(m: types.Message):
    await m.answer(f"⚙️ Статус: Online\nПлатформа: Render.com")

@dp.message(F.text)
async def handle_ai(m: types.Message):
    if not m.text: return
    user_id = m.from_user.id
    triggers = [f"{BOT_NAME}:", f"{BOT_NAME} ПОИСК:", BOT_NAME, BOT_USERNAME]
    is_addressed = any(m.text.startswith(t) for t in triggers) or \
                   (m.reply_to_message and m.reply_to_message.from_user.id == bot.id)

    if not is_addressed: return

    ok, wait = check_limit(user_id)
    if not ok:
        await m.reply(f"⏳ Лимит! Подожди {wait} мин.")
        return

    prompt = m.text
    for t in triggers: prompt = prompt.replace(t, "")
    
    try:
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        await m.reply(response.text)
    except Exception as e:
        await m.reply("🔧 Ошибка ИИ.")

async def main():
    print("--- БОТ ЗАПУЩЕН НА RENDER ---")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
