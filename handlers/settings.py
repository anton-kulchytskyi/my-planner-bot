"""Хендлер «⚙️ Налаштування» (заглушка — наповнюється в наступному кроці)."""
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from keyboards import BTN_SETTINGS

router = Router()


@router.message(Command("settings"))
@router.message(F.text == BTN_SETTINGS)
async def settings(message: Message) -> None:
    await message.answer("🚧 «Налаштування» — скоро")
