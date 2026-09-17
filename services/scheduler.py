from zoneinfo import ZoneInfo

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from database.database import Database
from services.export import send_export
from keyboards.keyboards import yes_no_kb
from lexicon.lexicon import LEXICON


async def send_reminder(bot: Bot, user_id: int):
    await bot.send_message(user_id, LEXICON["pills"])


async def send_ping(bot: Bot, db: Database, user_id: int):
    if db.open_episode():
        await bot.send_message(user_id, LEXICON["still"], reply_markup=yes_no_kb("still"))
    else:
        await bot.send_message(user_id, LEXICON["ping"], reply_markup=yes_no_kb("ping"))


def create_scheduler(bot: Bot, db: Database, user_id: int) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone=ZoneInfo("Europe/Moscow"))
    scheduler.add_job(send_ping, "cron", hour="9-23/2", args=[bot, db, user_id])
    scheduler.add_job(send_export, "cron", hour=23, args=[bot, db, user_id])
    scheduler.add_job(send_reminder, "cron", hour="11,15", minute=30, args=[bot, user_id])
    return scheduler
