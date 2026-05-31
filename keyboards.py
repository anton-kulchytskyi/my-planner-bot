"""Клавіатури: постійне меню + збірка inline з абстрактних кнопок."""
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from views import Button

BTN_TODAY = "☀️ Сьогодні"
BTN_ADD = "➕ Додати"
BTN_DONE = "✅ Виконано"
BTN_UPCOMING = "📅 Найближче"
BTN_SCHEDULE = "🔁 Розклад"
BTN_SETTINGS = "⚙️ Налаштування"
BTN_HELP = "❓ Допомога"


def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=BTN_TODAY),
                KeyboardButton(text=BTN_UPCOMING),
                KeyboardButton(text=BTN_SCHEDULE),
            ],
            [KeyboardButton(text=BTN_ADD), KeyboardButton(text=BTN_DONE)],
            [KeyboardButton(text=BTN_SETTINGS), KeyboardButton(text=BTN_HELP)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def inline_column(buttons: list[Button]) -> InlineKeyboardMarkup | None:
    """Кожна кнопка — окремим рядком. Порожній список -> None."""
    if not buttons:
        return None
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=b.label, callback_data=b.callback_data)]
            for b in buttons
        ]
    )
