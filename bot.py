import asyncio
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.stdout.reconfigure(encoding='utf-8')

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.enums import ParseMode
from config import TELEGRAM_BOT_TOKEN
from engine import engine


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

dp = Dispatcher()

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    welcome_uz = (
        "👋 **Assalomu alaykum!**\n\n"
        "Men **UZEX AI Hackathon 2026** saralash bosqichi uchun yaratilgan tahliliy AI-agentman.\n\n"
        "Men Oʻzbekiston respublika tovar-xom ashyo birjasining 2022–2026 yillardagi **500 000 ta birja bitimi**, "
        "shartnomalar, savdo ishtirokchilari, brokerlar va dollar kurslari boʻyicha aniq maʼlumotlar asosida javob beraman.\n\n"
        "🇺🇿 Savolingizni oʻzbek yoki rus tilida yozing.\n"
        "🇷🇺 Задайте ваш вопрос на узбекском или русском языке.\n\n"
        "**Misol savollar:**\n"
        "• *2025-yilda eng koʻp sement sotgan kompaniya va qancha summaga?*\n"
        "• *Какая компания продала больше всего пшеницы в 2024 году?*\n"
        "• *2024-yil avgust oyidagi eksport bitimlarining soʻmdagi umumiy hajmi qancha?*\n"
        "• *BK001 broker orqali qancha bitim tuzilgan?*"
    )
    await message.answer(welcome_uz, parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = (
        "ℹ️ **Qoʻllanma:**\n"
        "Men birja bitimlari reyestri asosida ishlayman. Barcha javoblar faqat va faqat "
        "haqiqiy maʼlumotlarga asoslanadi (gallyutsinatsiyalarga yoʻl qoʻyilmaydi).\n\n"
        "Agar soʻralgan maʼlumot bazada mavjud boʻlmasa, men buni ochiq aytaman."
    )
    await message.answer(help_text, parse_mode=ParseMode.MARKDOWN)

@dp.message(F.text)
async def handle_query(message: types.Message):
    query_text = message.text.strip()
    if not query_text:
        return

    # Show typing action while processing
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

    res = await engine.process_query(query_text)
    answer = res["answer"]
    sql = res.get("sql")
    elapsed = res.get("elapsed_seconds", 0)

    # Format reply: For casual conversation, just send the natural text
    if res.get("status") in ["conversation", "greeting"]:
        reply = answer
    else:
        reply = f"{answer}\n\n"
        if sql:
            clean_sql_one_line = " ".join(sql.replace("`", "'").split())
            reply += f"🔍 *SQL:* `{clean_sql_one_line}`\n"
        if res.get("language") == "ru":
            reply += f"⏱ *Время:* {elapsed} сек."
        else:
            reply += f"⏱ *Vaqt:* {elapsed} soniya"


    # Telegram limit is 4096 chars
    if len(reply) > 4000:
        reply = reply[:3990] + "\n..."

    try:
        await message.answer(reply, parse_mode=ParseMode.MARKDOWN)
    except Exception:
        # Fallback without markdown if special chars cause formatting error
        await message.answer(reply)

async def start_bot_polling():
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN is not set. Bot will not run.")
        return
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    logger.info("Starting Telegram Bot with long polling...")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    import time
    if not TELEGRAM_BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN is not set. Please set it in .env or environment.")
    else:
        print("Starting UZEX Telegram Bot (@SmartMarketPricesBot)...")
        while True:
            try:
                asyncio.run(start_bot_polling())
            except (KeyboardInterrupt, SystemExit):
                print("Bot stopped by user.")
                break
            except Exception as e:
                logger.error(f"Bot connection error: {e}. Reconnecting in 3 seconds...")
                time.sleep(3)

