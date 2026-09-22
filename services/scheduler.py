from datetime import date
from zoneinfo import ZoneInfo

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from database.database import Database
from keyboards.keyboards import yes_no_kb
from lexicon.lexicon import EVENING, LEXICON
from services.export import send_export
from services.stats import fmt_day


async def send_pills(bot: Bot, db: Database, user_id: int):
    pill_id = db.add_pill()
    await bot.send_message(user_id, LEXICON["pills"], reply_markup=yes_no_kb(f"pill:{pill_id}", "Выпила", "Не выпила"))


async def repeat_pills(bot: Bot, db: Database, user_id: int):
    """Через час после напоминания повторяет его, если ответа не было."""
    pill_id = db.pending_pill()
    if pill_id:
        await bot.send_message(
            user_id, LEXICON["pills"], reply_markup=yes_no_kb(f"pill:{pill_id}", "Выпила", "Не выпила")
        )


async def send_ping(bot: Bot, db: Database, user_id: int):
    episode = db.open_episode()
    # Эпизод с прошлого дня остался незакрытым — считаем, что болело до вечера
    if episode and episode["day"] != date.today().isoformat():
        db.close_episode(EVENING)
        await bot.send_message(user_id, LEXICON["auto_closed"].format(day=fmt_day(episode["day"]), evening=EVENING))
        episode = None

    if episode:
        await bot.send_message(user_id, LEXICON["still"], reply_markup=yes_no_kb("still"))
    else:
        await bot.send_message(user_id, LEXICON["ping"], reply_markup=yes_no_kb("ping"))


def create_scheduler(bot: Bot, db: Database, user_id: int) -> AsyncIOScheduler:
    # Если компьютер спал в момент отправки — отправить при пробуждении (не позже часа), пропуски не копить
    scheduler = AsyncIOScheduler(
        timezone=ZoneInfo("Europe/Moscow"),
        job_defaults={"misfire_grace_time": 3600, "coalesce": True},
    )
    scheduler.add_job(send_ping, "cron", hour="9-23/2", args=[bot, db, user_id])
    scheduler.add_job(send_pills, "cron", hour="11,15", minute=30, args=[bot, db, user_id])
    scheduler.add_job(repeat_pills, "cron", hour="12,16", minute=30, args=[bot, db, user_id])
    scheduler.add_job(send_export, "cron", hour=23, args=[bot, db, user_id])
    return scheduler
