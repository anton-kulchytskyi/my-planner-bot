"""Хендлер «☀️ Сьогодні» — прострочені, події й задачі дня."""
import keyboards
import views
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from services import clock, items

router = Router()


async def build_today(include_backlog: bool = False) -> views.View:
    """Збирає дані за сьогодні й рендерить (використовується і в briefing).

    include_backlog=True (briefing) додає секцію задач без дати; кнопка
    «Сьогодні» лишається чистою (беклог дивимось у «Найближче»).
    """
    today = await clock.today()
    return views.today_view(
        today,
        overdue=await items.get_overdue_tasks(today),
        events=await items.get_events_on(today),
        tasks=await items.get_tasks_on(today),
        backlog=await items.get_backlog() if include_backlog else None,
    )


@router.message(Command("today"))
@router.message(F.text == keyboards.BTN_TODAY)
async def today(message: Message) -> None:
    view = await build_today()
    await message.answer(view.text, reply_markup=keyboards.inline_column(view.buttons))


@router.callback_query(F.data.startswith("tdone:"))
async def today_mark_done(callback: CallbackQuery) -> None:
    item_id = int(callback.data.split(":")[1])
    await items.mark_done(item_id)
    view = await build_today()
    await callback.message.edit_text(
        view.text, reply_markup=keyboards.inline_column(view.buttons)
    )
    await callback.answer("✅ Готово")
