"""Хендлер «➕ Додати» — FSM-флоу для задач і подій."""
from datetime import date, datetime, time, timedelta

import utils
from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from keyboards import BTN_ADD
from services import clock, items, scheduler

router = Router()

HOUR_FROM = 8
HOUR_TO = 22

# (хвилини, підпис) для вибору тривалості події
DURATIONS = [(15, "15 хв"), (30, "30 хв"), (45, "45 хв"), (60, "1 год"), (90, "1.5 год"), (120, "2 год")]


class Add(StatesGroup):
    title = State()
    date = State()          # показано кнопки дати
    date_manual = State()   # очікуємо введену вручну дату
    event_hour = State()
    event_minute = State()
    event_duration = State()


def _duration_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"dur:{m}") for m, label in DURATIONS[i : i + 3]]
        for i in range(0, len(DURATIONS), 3)
    ]
    rows.append([InlineKeyboardButton(text="⏭ Без тривалості", callback_data="dur:none")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# --- Клавіатури ----------------------------------------------------------

def _type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📋 Задача", callback_data="add:task"),
                InlineKeyboardButton(text="📅 Подія", callback_data="add:event"),
            ]
        ]
    )


def _date_keyboard(allow_none: bool) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text="Сьогодні", callback_data="date:today"),
            InlineKeyboardButton(text="Завтра", callback_data="date:tomorrow"),
        ],
        [InlineKeyboardButton(text="📅 Інша дата", callback_data="date:manual")],
    ]
    if allow_none:
        rows.append([InlineKeyboardButton(text="⏭ Без дати", callback_data="date:none")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _hour_keyboard() -> InlineKeyboardMarkup:
    hours = list(range(HOUR_FROM, HOUR_TO + 1))
    rows = []
    for i in range(0, len(hours), 5):
        rows.append(
            [
                InlineKeyboardButton(text=f"{h:02d}", callback_data=f"hour:{h}")
                for h in hours[i : i + 5]
            ]
        )
    rows.append([InlineKeyboardButton(text="⏭ Без часу", callback_data="hour:none")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _minute_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=f"{m:02d}", callback_data=f"min:{m}")
                for m in (0, 15, 30, 45)
            ]
        ]
    )


# --- Helpers -------------------------------------------------------------

async def _proceed_after_date(message: Message, state: FSMContext, the_date: date | None) -> None:
    """Після вибору дати: задачу зберігаємо, для події йдемо до вибору часу."""
    data = await state.get_data()
    if data["type"] == "task":
        await items.add_item("task", data["title"], date=the_date)
        await state.clear()
        title = utils.esc(data["title"])
        if the_date:
            await message.answer(f"✅ Задача додана: {title} (до {utils.fmt_date(the_date)})")
        else:
            await message.answer(f"✅ Задача додана: {title}")
    else:  # event
        await state.update_data(date=the_date.isoformat())
        await state.set_state(Add.event_hour)
        await message.answer("О котрій? Обери годину:", reply_markup=_hour_keyboard())


# --- Вхід у флоу ---------------------------------------------------------

@router.message(Command("add"))
@router.message(F.text == BTN_ADD)
async def add_entry(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Що додаємо?", reply_markup=_type_keyboard())


@router.message(Command("cancel"), StateFilter("*"))
async def cancel(message: Message, state: FSMContext) -> None:
    if await state.get_state() is None:
        return
    await state.clear()
    await message.answer("Скасовано.")


@router.callback_query(F.data == "add:task")
async def choose_task(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_data({"type": "task"})
    await state.set_state(Add.title)
    await callback.message.edit_text("📋 Нова задача.\nНазва?")
    await callback.answer()


@router.callback_query(F.data == "add:event")
async def choose_event(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_data({"type": "event"})
    await state.set_state(Add.title)
    await callback.message.edit_text("📅 Нова подія.\nНазва?")
    await callback.answer()


# --- Назва + вибір дати --------------------------------------------------

@router.message(Add.title)
async def set_title(message: Message, state: FSMContext) -> None:
    data = await state.update_data(title=message.text.strip())
    await state.set_state(Add.date)
    await message.answer(
        "Коли?",
        reply_markup=_date_keyboard(allow_none=data["type"] == "task"),
    )


@router.callback_query(Add.date, F.data == "date:today")
async def date_today(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer()
    await _proceed_after_date(callback.message, state, await clock.today())


@router.callback_query(Add.date, F.data == "date:tomorrow")
async def date_tomorrow(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer()
    await _proceed_after_date(callback.message, state, await clock.today() + timedelta(days=1))


@router.callback_query(Add.date, F.data == "date:none")
async def date_none(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.answer()
    await _proceed_after_date(callback.message, state, None)


@router.callback_query(Add.date, F.data == "date:manual")
async def date_manual_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(Add.date_manual)
    await callback.message.edit_text("Введи дату (ДД.ММ або ДД.ММ.РРРР):")
    await callback.answer()


@router.message(Add.date_manual)
async def date_manual_input(message: Message, state: FSMContext) -> None:
    today = await clock.today()
    parsed = utils.parse_date(message.text, default_year=today.year)
    if parsed is None:
        await message.answer("Не зрозумів дату. Формат ДД.ММ або ДД.ММ.РРРР")
        return
    await _proceed_after_date(message, state, parsed)


# --- Час події: година -> хвилини ----------------------------------------

@router.callback_query(Add.event_hour, F.data == "hour:none")
async def hour_none(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    event_dt = date.fromisoformat(data["date"])
    await items.add_item("event", data["title"], date=event_dt)
    await state.clear()
    await callback.message.edit_text(
        f"✅ Подія додана: {utils.esc(data['title'])} — {utils.fmt_date(event_dt)}"
    )
    await callback.answer()


@router.callback_query(Add.event_hour, F.data.startswith("hour:"))
async def hour_chosen(callback: CallbackQuery, state: FSMContext) -> None:
    hour = int(callback.data.split(":")[1])
    await state.update_data(hour=hour)
    await state.set_state(Add.event_minute)
    await callback.message.edit_text(
        f"Година {hour:02d}. Хвилини:", reply_markup=_minute_keyboard()
    )
    await callback.answer()


@router.callback_query(Add.event_minute, F.data.startswith("min:"))
async def minute_chosen(callback: CallbackQuery, state: FSMContext) -> None:
    minute = int(callback.data.split(":")[1])
    data = await state.get_data()
    await state.update_data(time=f"{int(data['hour']):02d}:{minute:02d}")
    await state.set_state(Add.event_duration)
    await callback.message.edit_text(
        f"Скільки триватиме? (початок {int(data['hour']):02d}:{minute:02d})",
        reply_markup=_duration_keyboard(),
    )
    await callback.answer()


@router.callback_query(Add.event_duration, F.data == "dur:none")
async def duration_none(callback: CallbackQuery, state: FSMContext) -> None:
    await _finalize_event(callback.message, state, end_time=None)
    await callback.answer()


@router.callback_query(Add.event_duration, F.data.startswith("dur:"))
async def duration_chosen(callback: CallbackQuery, state: FSMContext) -> None:
    minutes = int(callback.data.split(":")[1])
    data = await state.get_data()
    start = utils.parse_time(data["time"])
    end = (datetime.combine(date.today(), start) + timedelta(minutes=minutes)).time()
    await _finalize_event(callback.message, state, end_time=end)
    await callback.answer()


async def _finalize_event(target: Message, state: FSMContext, end_time: time | None) -> None:
    data = await state.get_data()
    event_dt = date.fromisoformat(data["date"])
    start = utils.parse_time(data["time"])
    item = await items.add_item(
        "event", data["title"], date=event_dt, time=start, end_time=end_time
    )
    await state.clear()
    await scheduler.schedule_reminder_for(item)
    span = utils.fmt_time(start) + (f"–{utils.fmt_time(end_time)}" if end_time else "")
    await target.edit_text(
        f"✅ Подія додана: {utils.esc(data['title'])} — {utils.fmt_date(event_dt)} {span}"
    )
