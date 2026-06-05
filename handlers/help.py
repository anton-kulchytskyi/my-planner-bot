"""Хендлер «❓ Допомога» — опис усіх кнопок."""
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from keyboards import (
    BTN_ADD,
    BTN_DONE,
    BTN_HELP,
    BTN_SCHEDULE,
    BTN_SETTINGS,
    BTN_SHOPPING,
    BTN_TODAY,
    BTN_UPCOMING,
)

router = Router()

HELP_TEXT = (
    "❓ <b>Як користуватися ботом</b>\n\n"
    f"{BTN_TODAY} — план на сьогодні: прострочені задачі, події й задачі дня.\n"
    f"{BTN_ADD} — додати задачу або подію.\n"
    f"{BTN_DONE} — відмітити незавершені задачі виконаними.\n"
    f"{BTN_UPCOMING} — події й задачі на найближчі 7 днів.\n"
    f"{BTN_SCHEDULE} — повторювані задачі/події (🔁 у списках).\n"
    f"{BTN_SHOPPING} — окремий список покупок: тап по позиції прибирає її.\n"
    f"{BTN_SETTINGS} — змінити час ранкового briefing.\n"
    f"{BTN_HELP} — це повідомлення.\n\n"
    "Команди працюють так само: /today, /add, /done, /upcoming, /shopping, /settings, /help.\n"
    "Щоранку бот сам надсилає план на день.\n\n"
    "🤖 <b>Асистент:</b> просто напиши звичайним текстом — напр. «завтра о 15 "
    "зустріч з Іваном», «що в мене на тиждень?», «закрий задачу …». "
    "Команда /reset очищає контекст розмови."
)


@router.message(Command("help"))
@router.message(F.text == BTN_HELP)
async def help_handler(message: Message) -> None:
    await message.answer(HELP_TEXT)
