"""Хендлер «📅 Найближче» (заглушка — наповнюється в наступному кроці)."""
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from keyboards import BTN_UPCOMING

router = Router()


@router.message(Command("upcoming"))
@router.message(F.text == BTN_UPCOMING)
async def upcoming(message: Message) -> None:
    await message.answer("🚧 «Найближче» — скоро")
