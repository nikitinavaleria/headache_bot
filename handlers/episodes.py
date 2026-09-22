from datetime import date, datetime, timedelta

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from database.database import Database
from handlers.user import start_survey
from keyboards.keyboards import day_kb, episode_kb, episodes_kb, options_kb
from lexicon.lexicon import FREE_TEXT, LABELS, LEXICON, QUESTION_BY_KEY, STILL_HURTS, TIME_RE
from services.stats import fmt_day

episodes_router = Router()


class Edit(StatesGroup):
    value = State()  # ждём новое значение поля, в data — id эпизода и ключ поля


class Add(StatesGroup):
    day = State()    # ждём дату пропущенного эпизода


def parse_day(text: str) -> date | None:
    """Разбирает дату вида 15.09 или 15.09.2026. Дата без года не может быть в будущем."""
    for fmt in ("%d.%m.%Y", "%d.%m"):
        try:
            parsed = datetime.strptime(text.strip(), fmt).date()
        except ValueError:
            continue
        if fmt == "%d.%m":
            parsed = parsed.replace(year=date.today().year)
            if parsed > date.today():
                parsed = parsed.replace(year=parsed.year - 1)
        return parsed
    return None


def fmt_card(episode) -> str:
    lines = [f"<b>Эпизод от {fmt_day(episode['day'])}</b>"]
    for key, label in LABELS.items():
        blank = STILL_HURTS.lower() if key == "end" else "—"
        lines.append(f"{label}: {episode[key] or blank}")
    return "\n".join(lines)


async def show_list(message: Message, db: Database):
    episodes = db.last_episodes()
    if not episodes:
        await message.answer(LEXICON["no_episodes"])
    else:
        await message.answer(LEXICON["episodes"], reply_markup=episodes_kb(episodes))


async def show_card(message: Message, db: Database, episode_id: int):
    episode = db.episode(episode_id)
    if not episode:
        await show_list(message, db)
        return
    await message.answer(fmt_card(episode), reply_markup=episode_kb(episode_id))


@episodes_router.message(Command("episodes"))
async def process_episodes(message: Message, db: Database):
    await show_list(message, db)


@episodes_router.callback_query(F.data == "eps")
async def back_to_list(callback: CallbackQuery, db: Database):
    await callback.message.delete()
    await show_list(callback.message, db)


@episodes_router.callback_query(F.data.startswith("ep:"))
async def open_episode(callback: CallbackQuery, db: Database):
    await callback.message.delete()
    await show_card(callback.message, db, int(callback.data.removeprefix("ep:")))


# ---------- правка поля ----------

@episodes_router.callback_query(F.data.startswith("fld:"))
async def pick_field(callback: CallbackQuery, state: FSMContext):
    _, episode_id, key = callback.data.split(":")
    await callback.message.edit_reply_markup()
    await state.set_state(Edit.value)
    await state.update_data(episode_id=int(episode_id), key=key)
    text, options = QUESTION_BY_KEY[key]
    await callback.message.answer(text, reply_markup=options_kb(options))


async def save_field(message: Message, state: FSMContext, db: Database, value: str | None):
    data = await state.get_data()
    await state.clear()
    db.update_episode(data["episode_id"], data["key"], value)
    await message.answer(LEXICON["updated"])
    await show_card(message, db, data["episode_id"])


@episodes_router.callback_query(Edit.value, F.data.startswith("ans:"))
async def edit_button(callback: CallbackQuery, state: FSMContext, db: Database):
    value = callback.data.removeprefix("ans:")
    await callback.message.edit_text(f"{callback.message.text}\n→ {value}")
    await save_field(callback.message, state, db, None if value == STILL_HURTS else value)


@episodes_router.message(Edit.value, F.text)
async def edit_text(message: Message, state: FSMContext, db: Database):
    key = (await state.get_data())["key"]
    if key not in FREE_TEXT:
        await message.answer(LEXICON["use_buttons"])
    elif key in ("start", "end") and not TIME_RE.match(message.text):
        await message.answer(LEXICON["bad_time"])
    else:
        await save_field(message, state, db, message.text)


# ---------- удаление ----------

@episodes_router.callback_query(F.data.startswith("del:"))
async def confirm_delete(callback: CallbackQuery):
    episode_id = callback.data.removeprefix("del:")
    await callback.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Да, удалить", callback_data=f"delok:{episode_id}"),
        InlineKeyboardButton(text="Отмена", callback_data=f"ep:{episode_id}"),
    ]]))
    await callback.answer(LEXICON["confirm_delete"], show_alert=True)


@episodes_router.callback_query(F.data.startswith("delok:"))
async def do_delete(callback: CallbackQuery, db: Database):
    db.delete_episode(int(callback.data.removeprefix("delok:")))
    await callback.message.delete()
    await callback.message.answer(LEXICON["deleted"])
    await show_list(callback.message, db)


# ---------- пропущенный эпизод ----------

@episodes_router.callback_query(F.data == "add")
async def add_missed(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup()
    await state.set_state(Add.day)
    await callback.message.answer(LEXICON["add_day"], reply_markup=day_kb())


@episodes_router.callback_query(Add.day, F.data.startswith("day:"))
async def add_day_button(callback: CallbackQuery, state: FSMContext, db: Database):
    day = date.today() - timedelta(days=int(callback.data.removeprefix("day:")))
    await callback.message.edit_text(f"{callback.message.text}\n→ {day.strftime('%d.%m')}")
    await start_survey(callback.message, state, db, day)


@episodes_router.message(Add.day, F.text)
async def add_day_text(message: Message, state: FSMContext, db: Database):
    day = parse_day(message.text)
    if day:
        await start_survey(message, state, db, day)
    else:
        await message.answer(LEXICON["bad_date"])
