from aiogram import Router
from aiogram.types import Message

from lexicon.lexicon import LEXICON

other_router = Router()


@other_router.message()
async def process_unknown(message: Message):
    await message.answer(LEXICON["unknown"])
