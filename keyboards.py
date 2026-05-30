"""Постійна Reply-клавіатура головного меню."""
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

BTN_TODAY = "☀️ Сьогодні"
BTN_ADD = "➕ Додати"
BTN_DONE = "✅ Виконано"
BTN_UPCOMING = "📅 Найближче"
BTN_SETTINGS = "⚙️ Налаштування"
BTN_HELP = "❓ Допомога"


def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_TODAY), KeyboardButton(text=BTN_ADD)],
            [KeyboardButton(text=BTN_DONE), KeyboardButton(text=BTN_UPCOMING)],
            [KeyboardButton(text=BTN_SETTINGS), KeyboardButton(text=BTN_HELP)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )
