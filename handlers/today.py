"""Хендлер «☀️ Сьогодні» (заглушка — наповнюється в наступному кроці)."""
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from keyboards import BTN_TODAY

router = Router()


@router.message(Command("today"))
@router.message(F.text == BTN_TODAY)
async def today(message: Message) -> None:
    await message.answer("🚧 «Сьогодні» — скоро")
