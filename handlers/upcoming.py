"""Хендлер «📅 Найближче» — події й задачі на наступні 7 днів."""
from datetime import timedelta

import keyboards
import views
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from services import clock, items

router = Router()


async def build_upcoming() -> views.View:
    today = await clock.today()
    rows = await items.get_upcoming(today + timedelta(days=1), today + timedelta(days=7))
    return views.upcoming_view(rows)


@router.message(Command("upcoming"))
@router.message(F.text == keyboards.BTN_UPCOMING)
async def upcoming(message: Message) -> None:
    view = await build_upcoming()
    await message.answer(view.text)
