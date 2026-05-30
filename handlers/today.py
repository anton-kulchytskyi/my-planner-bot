"""Хендлер «☀️ Сьогодні» — прострочені, події й задачі дня."""
import utils
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from handlers.common import today_date
from keyboards import BTN_TODAY
from services import items

router = Router()


def _overdue_keyboard(overdue: list) -> InlineKeyboardMarkup | None:
    if not overdue:
        return None
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"✅ {item.title[:30]}",
                    callback_data=f"tdone:{item.id}",
                )
            ]
            for item in overdue
        ]
    )


async def render_today() -> tuple[str, InlineKeyboardMarkup | None]:
    """Будує текст і клавіатуру для «Сьогодні» / ранкового briefing."""
    today = await today_date()
    overdue = await items.get_overdue_tasks(today)
    events = await items.get_events_on(today)
    tasks = await items.get_tasks_on(today)

    if not (overdue or events or tasks):
        return "Сьогодні нічого не заплановано 🎉", None

    lines = [f"☀️ <b>Сьогодні, {utils.human_date(today)}</b>", ""]

    if overdue:
        lines.append("⚠️ <b>Прострочено:</b>")
        for item in overdue:
            delta = (today - item.date).days
            lines.append(f"• {utils.esc(item.title)} ({utils.days_ago(delta)})")
        lines.append("")

    if events:
        lines.append("📅 <b>Події:</b>")
        for item in events:
            prefix = f"{utils.fmt_time(item.time)} — " if item.time else ""
            lines.append(f"• {prefix}{utils.esc(item.title)}")
        lines.append("")

    if tasks:
        lines.append("📋 <b>На сьогодні:</b>")
        for item in tasks:
            lines.append(f"• {utils.esc(item.title)}")
        lines.append("")

    return "\n".join(lines).strip(), _overdue_keyboard(overdue)


@router.message(Command("today"))
@router.message(F.text == BTN_TODAY)
async def today(message: Message) -> None:
    text, keyboard = await render_today()
    await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("tdone:"))
async def today_mark_done(callback: CallbackQuery) -> None:
    item_id = int(callback.data.split(":")[1])
    await items.mark_done(item_id)
    text, keyboard = await render_today()
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer("✅ Готово")
