import csv
import io

from aiogram import Bot
from aiogram.types import BufferedInputFile

from database.database import Database

TABLES = ("episodes", "pings")


def csv_file(db: Database, table: str) -> BufferedInputFile:
    header, rows = db.dump(table)
    buf = io.StringIO()
    csv.writer(buf).writerows([header, *rows])
    return BufferedInputFile(buf.getvalue().encode(), filename=f"{table}.csv")


async def send_export(bot: Bot, db: Database, user_id: int):
    for table in TABLES:
        await bot.send_document(user_id, csv_file(db, table))
