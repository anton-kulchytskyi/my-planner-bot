"""Хендлер «➕ Додати» — FSM-флоу для задач і подій."""
from datetime import date

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
from services import items, storage

router = Router()


class Add(StatesGroup):
    task_title = State()
    task_date = State()
    event_title = State()
    event_date = State()
    event_time = State()


def _type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📋 Задача", callback_data="add:task"),
                InlineKeyboardButton(text="📅 Подія", callback_data="add:event"),
            ]
        ]
    )


async def _current_year() -> int:
    tz = await storage.get_setting("timezone")
    return utils.now_local(tz).year


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
    await state.set_state(Add.task_title)
    await callback.message.edit_text("📋 Нова задача.\nНазва?")
    await callback.answer()


@router.callback_query(F.data == "add:event")
async def choose_event(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(Add.event_title)
    await callback.message.edit_text("📅 Нова подія.\nНазва?")
    await callback.answer()


# --- Гілка «Задача» ------------------------------------------------------

@router.message(Add.task_title)
async def task_title(message: Message, state: FSMContext) -> None:
    await state.update_data(title=message.text.strip())
    await state.set_state(Add.task_date)
    await message.answer("На коли? (ДД.ММ або /skip)")


@router.message(Command("skip"), Add.task_date)
async def task_skip_date(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await items.add_item("task", data["title"])
    await state.clear()
    await message.answer(f"✅ Задача додана: {utils.esc(data['title'])}")


@router.message(Add.task_date)
async def task_date(message: Message, state: FSMContext) -> None:
    parsed = utils.parse_date(message.text, default_year=await _current_year())
    if parsed is None:
        await message.answer("Не зрозумів дату. Формат ДД.ММ (напр. 05.06) або /skip")
        return
    data = await state.get_data()
    await items.add_item("task", data["title"], date=parsed)
    await state.clear()
    await message.answer(
        f"✅ Задача додана: {utils.esc(data['title'])} (до {utils.fmt_date(parsed)})"
    )


# --- Гілка «Подія» -------------------------------------------------------

@router.message(Add.event_title)
async def event_title(message: Message, state: FSMContext) -> None:
    await state.update_data(title=message.text.strip())
    await state.set_state(Add.event_date)
    await message.answer("Дата? (ДД.ММ або ДД.ММ.РРРР)")


@router.message(Add.event_date)
async def event_date(message: Message, state: FSMContext) -> None:
    parsed = utils.parse_date(message.text, default_year=await _current_year())
    if parsed is None:
        await message.answer("Не зрозумів дату. Формат ДД.ММ або ДД.ММ.РРРР")
        return
    await state.update_data(date=parsed.isoformat())
    await state.set_state(Add.event_time)
    await message.answer("Час? (ГГ:ХХ або /skip)")


@router.message(Command("skip"), Add.event_time)
async def event_skip_time(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    event_dt = date.fromisoformat(data["date"])
    await items.add_item("event", data["title"], date=event_dt)
    await state.clear()
    await message.answer(
        f"✅ Подія додана: {utils.esc(data['title'])} — {utils.fmt_date(event_dt)}"
    )


@router.message(Add.event_time)
async def event_time(message: Message, state: FSMContext) -> None:
    parsed = utils.parse_time(message.text)
    if parsed is None:
        await message.answer("Не зрозумів час. Формат ГГ:ХХ (напр. 14:30) або /skip")
        return
    data = await state.get_data()
    event_dt = date.fromisoformat(data["date"])
    await items.add_item("event", data["title"], date=event_dt, time=parsed)
    await state.clear()
    await message.answer(
        f"✅ Подія додана: {utils.esc(data['title'])} — "
        f"{utils.fmt_date(event_dt)} {utils.fmt_time(parsed)}"
    )
    # TODO (Крок scheduler): поставити нагадування за 1 годину до події
