import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import settings
from db.connection import DatabaseManager
from middlewares.logging import LoggingMiddleware
from middlewares.database import DatabaseMiddleware
from middlewares.i18n import I18nMiddleware
from handlers import start, menu, vps

# Setup basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("bot.main")


async def main() -> None:
    logger.info("Initializing HostVDS Telegram Bot...")

    # Instantiate Bot and Dispatcher with MemoryStorage
    bot = Bot(token=settings.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # Instantiate DatabaseManager
    db_manager = DatabaseManager(settings.DB_PATH)

    # Establish db connection and initialize schemas
    logger.info("Connecting to SQLite database...")
    await db_manager.connect()
    logger.info("Running database initializations / migrations...")
    await db_manager.init_db()

    # Register Middlewares (Order of execution: Logging -> Database -> I18n)
    dp.update.outer_middleware(LoggingMiddleware())
    dp.update.outer_middleware(DatabaseMiddleware(db_manager))
    dp.update.outer_middleware(I18nMiddleware(locales_dir="locales", default_locale=settings.DEFAULT_LOCALE))

    # Register Handler Routers
    dp.include_router(start.router)
    dp.include_router(menu.router)
    dp.include_router(vps.router)

    # Clean shutdown hook to close SQLite connection
    async def on_shutdown() -> None:
        logger.info("Closing database connections...")
        await db_manager.disconnect()
        logger.info("Connections closed. Bot stopped.")

    dp.shutdown.register(on_shutdown)

    # Start Polling
    try:
        logger.info("Starting polling loop...")
        # Skip pending updates on start
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except asyncio.CancelledError:
        logger.info("Polling task cancelled.")
    except Exception as e:
        logger.exception(f"Unexpected bot runner crash: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot execution interrupted manually.")
