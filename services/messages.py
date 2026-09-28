from contextlib import suppress

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest

from database.database import Database


async def drop_pending(bot: Bot, db: Database, chat_id: int, kind: str, keep: int | None = None):
    """Убирает из чата неотвеченные сообщения этого типа — кроме того, на которое только что ответили."""
    for message_id in db.take_pending(kind):
        if message_id != keep:
            with suppress(TelegramBadRequest):  # старше 48 часов Telegram удалить не даёт
                await bot.delete_message(chat_id, message_id)
