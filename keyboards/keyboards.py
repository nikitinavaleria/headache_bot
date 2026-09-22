from aiogram.types import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from lexicon.lexicon import LABELS, QUESTIONS


def options_kb(options: list[str]) -> InlineKeyboardMarkup | None:
    if not options:
        return None
    builder = InlineKeyboardBuilder()
    for option in options:
        builder.button(text=option, callback_data=f"ans:{option}")
    return builder.adjust(3).as_markup()


def yes_no_kb(prefix: str, yes: str = "Да", no: str = "Нет") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=yes, callback_data=f"{prefix}:yes"),
        InlineKeyboardButton(text=no, callback_data=f"{prefix}:no"),
    ]])


def end_how_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Прямо сейчас", callback_data="end:now"),
        InlineKeyboardButton(text="Указать время", callback_data="end:manual"),
    ]])


def episodes_kb(episodes) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for e in episodes:
        builder.button(text=f"{e['day'][8:10]}.{e['day'][5:7]} {e['start']}", callback_data=f"ep:{e['id']}")
    builder.adjust(3)
    builder.row(InlineKeyboardButton(text="＋ Добавить пропущенный", callback_data="add"))
    return builder.as_markup()


def day_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for text, days in (("Сегодня", 0), ("Вчера", 1), ("Позавчера", 2)):
        builder.button(text=text, callback_data=f"day:{days}")
    return builder.adjust(3).as_markup()


def episode_kb(episode_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for key, _, _ in QUESTIONS:
        builder.button(text=LABELS[key], callback_data=f"fld:{episode_id}:{key}")
    builder.adjust(2)
    builder.row(
        InlineKeyboardButton(text="🗑 Удалить", callback_data=f"del:{episode_id}"),
        InlineKeyboardButton(text="← К списку", callback_data="eps"),
    )
    return builder.as_markup()


async def set_main_menu(bot):
    await bot.set_my_commands([
        BotCommand(command="pain", description="Записать эпизод головной боли"),
        BotCommand(command="end", description="Проставить время окончания"),
        BotCommand(command="episodes", description="Посмотреть и поправить записи"),
        BotCommand(command="stats", description="Статистика"),
        BotCommand(command="export", description="Выгрузить данные в CSV"),
        BotCommand(command="cancel", description="Прервать опрос"),
    ])
