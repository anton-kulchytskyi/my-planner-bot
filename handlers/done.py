"""Хендлер «✅ Виконано» — закрити незавершені задачі (сьогодні + без дати)."""
import keyboards
import views
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from services import clock, items

router = Router()


async def build_done() -> views.View:
    return views.done_view(await items.get_open_tasks(await clock.today()))


@router.message(Command("done"))
@router.message(F.text == keyboards.BTN_DONE)
async def done(message: Message) -> None:
    view = await build_done()
    await message.answer(view.text, reply_markup=keyboards.inline_column(view.buttons))


@router.callback_query(F.data.startswith("done:"))
async def mark_done(callback: CallbackQuery) -> None:
    item_id = int(callback.data.split(":")[1])
    await items.mark_done(item_id)
    view = await build_done()
    await callback.message.edit_text(
        view.text, reply_markup=keyboards.inline_column(view.buttons)
    )
    await callback.answer("✅ Закрито")
