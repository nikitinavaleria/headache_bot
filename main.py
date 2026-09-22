import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config.config import load_config
from database.database import Database
from handlers.episodes import episodes_router
from handlers.other import other_router
from handlers.user import user_router
from keyboards.keyboards import set_main_menu
from services.scheduler import create_scheduler

logger = logging.getLogger(__name__)


async def main():
    config = load_config()
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(name)s - %(message)s")
    logger.info("Starting bot")

    bot = Bot(token=config.token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    db = Database(config.db_path)
    dp.workflow_data.update(db=db)

    # Бот отвечает только одному пользователю
    dp.message.filter(F.from_user.id == config.user_id)
    dp.callback_query.filter(F.from_user.id == config.user_id)

    dp.include_router(user_router)
    dp.include_router(episodes_router)
    dp.include_router(other_router)

    await set_main_menu(bot)
    create_scheduler(bot, db, config.user_id).start()

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
