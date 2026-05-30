"""Хендлер «✅ Виконано» — закрити незавершені задачі (сьогодні + без дати)."""
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from handlers.common import today_date
from keyboards import BTN_DONE
from services import items

router = Router()

EMPTY = "Немає незавершених задач 🎉"


async def render_done() -> tuple[str, InlineKeyboardMarkup | None]:
    today = await today_date()
    tasks = await items.get_open_tasks(today)
    if not tasks:
        return EMPTY, None
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"☑️ {task.title[:40]}",
                    callback_data=f"done:{task.id}",
                )
            ]
            for task in tasks
        ]
    )
    return "✅ <b>Незавершені задачі</b>\nТапни, щоб закрити:", keyboard


@router.message(Command("done"))
@router.message(F.text == BTN_DONE)
async def done(message: Message) -> None:
    text, keyboard = await render_done()
    await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("done:"))
async def mark_done(callback: CallbackQuery) -> None:
    item_id = int(callback.data.split(":")[1])
    await items.mark_done(item_id)
    text, keyboard = await render_done()
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer("✅ Закрито")
