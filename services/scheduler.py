from datetime import date, datetime
from zoneinfo import ZoneInfo

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from database.database import Database
from keyboards.keyboards import yes_no_kb
from lexicon.lexicon import EVENING, LEXICON
from services.export import send_export
from services.stats import fmt_day


async def send_pills(bot: Bot, db: Database, user_id: int, pill_id: int | None = None):
    pill_id = pill_id or db.add_pill()
    sent = await bot.send_message(
        user_id, LEXICON["pills"], reply_markup=yes_no_kb(f"pill:{pill_id}", "Выпила", "Не выпила")
    )
    db.add_pending("pill", sent.message_id)


async def repeat_pills(bot: Bot, db: Database, user_id: int):
    """Через час после напоминания повторяет его, если ответа не было."""
    pill_id = db.pending_pill()
    if pill_id:
        await send_pills(bot, db, user_id, pill_id)


MSK = ZoneInfo("Europe/Moscow")


def hours_since(time_str: str) -> float:
    """Сколько часов прошло с указанного времени (в пределах суток)."""
    now = datetime.now(MSK)
    taken = datetime.strptime(time_str, "%H:%M").replace(year=now.year, month=now.month, day=now.day, tzinfo=MSK)
    hours = (now - taken).total_seconds() / 3600
    return hours + 24 if hours < 0 else hours


async def relief_check(bot: Bot, db: Database, user_id: int):
    """Через час после таблетки спрашивает, прошла ли боль, и повторяет раз в час, пока не ответят."""
    episode = db.open_episode()
    if not episode or not episode["meds_time"] or episode["relief"]:
        return
    if hours_since(episode["meds_time"]) < 1:
        return
    sent = await bot.send_message(user_id, LEXICON["relief_check"], reply_markup=yes_no_kb("relief"))
    db.add_pending("relief", sent.message_id)


async def send_ping(bot: Bot, db: Database, user_id: int):
    episode = db.open_episode()
    # Эпизод с прошлого дня остался незакрытым — считаем, что болело до вечера
    if episode and episode["day"] != date.today().isoformat():
        db.close_episode(EVENING)
        await bot.send_message(user_id, LEXICON["auto_closed"].format(day=fmt_day(episode["day"]), evening=EVENING))
        episode = None

    # Про боль после таблетки спрашивает relief_check — дублировать не нужно
    if episode and episode["meds_time"] and not episode["relief"]:
        return

    text, prefix = (LEXICON["still"], "still") if episode else (LEXICON["ping"], "ping")
    sent = await bot.send_message(user_id, text, reply_markup=yes_no_kb(prefix))
    db.add_pending("ping", sent.message_id)


def create_scheduler(bot: Bot, db: Database, user_id: int) -> AsyncIOScheduler:
    # Если компьютер спал в момент отправки — отправить при пробуждении (не позже часа), пропуски не копить
    scheduler = AsyncIOScheduler(
        timezone=ZoneInfo("Europe/Moscow"),
        job_defaults={"misfire_grace_time": 3600, "coalesce": True},
    )
    scheduler.add_job(send_ping, "cron", hour="9-23/2", args=[bot, db, user_id])
    scheduler.add_job(send_pills, "cron", hour="11,15", minute=30, args=[bot, db, user_id])
    scheduler.add_job(repeat_pills, "cron", hour="12,16", minute=30, args=[bot, db, user_id])
    scheduler.add_job(relief_check, "cron", hour="9-23", minute=40, args=[bot, db, user_id])
    scheduler.add_job(send_export, "cron", hour=23, args=[bot, db, user_id])
    return scheduler
