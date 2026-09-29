from datetime import date, datetime
from zoneinfo import ZoneInfo

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from database.database import Database
from keyboards.keyboards import end_how_kb, options_kb
from lexicon.lexicon import DEPENDS, FREE_TEXT, LEXICON, NOW, QUESTIONS, STILL_HURTS, TIME_FIELDS, TIME_RE
from services.export import send_export
from services.messages import drop_pending
from services.stats import build_stats

user_router = Router()


class Survey(StatesGroup):
    answering = State()  # проходим опросник, номер вопроса в data["i"]
    ending = State()     # ждём время окончания открытого эпизода


def now_time() -> str:
    return datetime.now(ZoneInfo("Europe/Moscow")).strftime("%H:%M")


def skip(key: str, answers: dict) -> bool:
    """Условные вопросы про препарат не задаём, если препарат не принимался."""
    depends_on = DEPENDS.get(key)
    return bool(depends_on) and answers.get(depends_on) in (None, "Нет")


async def ask(message: Message, state: FSMContext, db: Database, i: int):
    """Задаёт i-й вопрос или сохраняет эпизод, если вопросы кончились."""
    answers = (await state.get_data())["answers"]
    while i < len(QUESTIONS) and skip(QUESTIONS[i][0], answers):
        i += 1
    if i == len(QUESTIONS):
        data = await state.get_data()
        await state.clear()
        day = date.fromisoformat(data["day"]) if data.get("day") else None
        db.add_episode(data["answers"], day)
        await message.answer(LEXICON["saved"])
        return
    _, text, options = QUESTIONS[i]
    await state.update_data(i=i)
    await message.answer(text, reply_markup=options_kb(options))


async def save_answer(message: Message, state: FSMContext, db: Database, value: str | None):
    data = await state.get_data()
    key = QUESTIONS[data["i"]][0]
    data["answers"][key] = value
    await state.update_data(answers=data["answers"])
    await ask(message, state, db, data["i"] + 1)


async def start_survey(message: Message, state: FSMContext, db: Database, day: date | None = None):
    await state.set_state(Survey.answering)
    await state.update_data(answers={}, day=day.isoformat() if day else None)
    await ask(message, state, db, 0)


# ---------- команды ----------

@user_router.message(CommandStart())
async def process_start(message: Message):
    await message.answer(LEXICON["/start"])


@user_router.message(Command("pain"))
async def process_pain(message: Message, state: FSMContext, db: Database):
    await start_survey(message, state, db)


@user_router.message(Command("end"))
async def process_end(message: Message, db: Database):
    if not db.open_episode():
        await message.answer(LEXICON["no_open"])
        return
    await message.answer(LEXICON["end_how"], reply_markup=end_how_kb())


@user_router.message(Command("stats"))
async def process_stats(message: Message, command: CommandObject, db: Database):
    await message.answer(build_stats(db, command.args or "week"))


@user_router.message(Command("export"))
async def process_export(message: Message, db: Database):
    await send_export(message.bot, db, message.from_user.id)


@user_router.message(Command("cancel"))
async def process_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(LEXICON["cancelled"])


# ---------- напоминание про таблетки ----------

@user_router.callback_query(F.data.startswith("pill:"))
async def process_pill(callback: CallbackQuery, db: Database):
    _, pill_id, answer = callback.data.split(":")
    await callback.message.edit_reply_markup()
    await drop_pending(callback.bot, db, callback.message.chat.id, "pill", keep=callback.message.message_id)
    db.set_pill(int(pill_id), taken=answer == "yes")
    await callback.message.answer(LEXICON["pills_ok" if answer == "yes" else "pills_skip"])


# ---------- ответы на пинг ----------

@user_router.callback_query(F.data == "ping:yes")
async def ping_yes(callback: CallbackQuery, state: FSMContext, db: Database):
    await callback.message.edit_reply_markup()
    await drop_pending(callback.bot, db, callback.message.chat.id, "ping", keep=callback.message.message_id)
    db.add_ping(pain=True)
    await start_survey(callback.message, state, db)


@user_router.callback_query(F.data == "ping:no")
async def ping_no(callback: CallbackQuery, db: Database):
    await callback.message.edit_reply_markup()
    await drop_pending(callback.bot, db, callback.message.chat.id, "ping", keep=callback.message.message_id)
    db.add_ping(pain=False)
    await callback.answer(LEXICON["noted"])


@user_router.callback_query(F.data == "still:yes")
async def still_yes(callback: CallbackQuery, db: Database):
    await callback.message.edit_reply_markup()
    await drop_pending(callback.bot, db, callback.message.chat.id, "ping", keep=callback.message.message_id)
    db.add_ping(pain=True)
    await callback.answer(LEXICON["noted"])


@user_router.callback_query(F.data == "still:no")
async def still_no(callback: CallbackQuery, db: Database):
    await callback.message.edit_reply_markup()
    await drop_pending(callback.bot, db, callback.message.chat.id, "ping", keep=callback.message.message_id)
    db.add_ping(pain=False)
    await callback.message.answer(LEXICON["end_how"], reply_markup=end_how_kb())


@user_router.callback_query(F.data == "relief:yes")
async def relief_yes(callback: CallbackQuery, db: Database):
    await callback.message.edit_reply_markup()
    await drop_pending(callback.bot, db, callback.message.chat.id, "relief", keep=callback.message.message_id)
    await callback.message.answer(LEXICON["end_how"], reply_markup=end_how_kb())


@user_router.callback_query(F.data == "relief:no")
async def relief_no(callback: CallbackQuery, db: Database):
    await callback.message.edit_reply_markup()
    await drop_pending(callback.bot, db, callback.message.chat.id, "relief", keep=callback.message.message_id)
    db.add_ping(pain=True)
    await callback.answer(LEXICON["noted"])


# ---------- время окончания эпизода ----------

@user_router.callback_query(F.data == "end:now")
async def end_now(callback: CallbackQuery, db: Database):
    await callback.message.edit_reply_markup()
    end = now_time()
    db.close_episode(end)
    await callback.message.answer(LEXICON["closed"].format(end=end))


@user_router.callback_query(F.data == "end:manual")
async def end_manual(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup()
    await state.set_state(Survey.ending)
    await callback.message.answer(LEXICON["ask_end"])


@user_router.message(Survey.ending, F.text.regexp(TIME_RE))
async def process_end_time(message: Message, state: FSMContext, db: Database):
    db.close_episode(message.text)
    await state.clear()
    await message.answer(LEXICON["closed"].format(end=message.text))


@user_router.message(Survey.ending)
async def process_bad_end_time(message: Message):
    await message.answer(LEXICON["bad_time"])


# ---------- ответы на вопросы опросника ----------

@user_router.callback_query(Survey.answering, F.data.startswith("ans:"))
async def answer_button(callback: CallbackQuery, state: FSMContext, db: Database):
    value = callback.data.removeprefix("ans:")
    await callback.message.edit_text(f"{callback.message.text}\n→ {value}")
    if value == STILL_HURTS:
        value = None
    elif value == NOW:
        value = now_time()
    await save_answer(callback.message, state, db, value)


@user_router.message(Survey.answering, F.text)
async def answer_text(message: Message, state: FSMContext, db: Database):
    data = await state.get_data()
    key = QUESTIONS[data["i"]][0]
    if key not in FREE_TEXT:
        await message.answer(LEXICON["use_buttons"])
    elif key in TIME_FIELDS and not TIME_RE.match(message.text):
        await message.answer(LEXICON["bad_time"])
    else:
        await save_answer(message, state, db, message.text)
