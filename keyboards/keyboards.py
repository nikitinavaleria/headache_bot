from aiogram.types import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def options_kb(options: list[str]) -> InlineKeyboardMarkup | None:
    if not options:
        return None
    builder = InlineKeyboardBuilder()
    for option in options:
        builder.button(text=option, callback_data=f"ans:{option}")
    return builder.adjust(3).as_markup()


def yes_no_kb(prefix: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Да", callback_data=f"{prefix}:yes"),
        InlineKeyboardButton(text="Нет", callback_data=f"{prefix}:no"),
    ]])


async def set_main_menu(bot):
    await bot.set_my_commands([
        BotCommand(command="pain", description="Записать эпизод головной боли"),
        BotCommand(command="end", description="Проставить время окончания"),
        BotCommand(command="stats", description="Статистика"),
        BotCommand(command="export", description="Выгрузить данные в CSV"),
        BotCommand(command="cancel", description="Прервать опрос"),
    ])
