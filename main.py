import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from config import BOT_TOKEN
from handlers import main_router
from services.monitor import run_health_monitor

# Configure logging
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

async def main():
    if not BOT_TOKEN:
        logging.error("BOT_TOKEN is not set in .env file!")
        return

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    dp.include_router(main_router)

    # Cookie health monitor: independent of polling lifetime.
    monitor_task = asyncio.create_task(run_health_monitor(bot))

    logging.info("Starting bot...")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Error: {e}")
    finally:
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
