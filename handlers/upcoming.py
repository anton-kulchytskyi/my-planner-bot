"""Хендлер «📅 Найближче» — події й задачі на наступні 7 днів."""
from datetime import timedelta

import utils
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from handlers.common import today_date
from keyboards import BTN_UPCOMING
from services import items

router = Router()


async def render_upcoming() -> str:
    today = await today_date()
    start = today + timedelta(days=1)
    end = today + timedelta(days=7)
    rows = await items.get_upcoming(start, end)

    if not rows:
        return "На найближчі 7 днів нічого не заплановано 🎉"

    lines = ["📅 <b>Найближчі 7 днів</b>", ""]
    current = None
    for item in rows:
        if item.date != current:
            if current is not None:
                lines.append("")
            current = item.date
            lines.append(f"<b>{utils.human_date(item.date)}</b>")
        prefix = f"{utils.fmt_time(item.time)} — " if (item.type == "event" and item.time) else ""
        lines.append(f"• {prefix}{utils.esc(item.title)}")

    return "\n".join(lines)


@router.message(Command("upcoming"))
@router.message(F.text == BTN_UPCOMING)
async def upcoming(message: Message) -> None:
    await message.answer(await render_upcoming())
