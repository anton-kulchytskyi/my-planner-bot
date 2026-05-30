"""Хендлер «➕ Додати» (заглушка — FSM-флоу наповнюється в наступному кроці)."""
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from keyboards import BTN_ADD

router = Router()


@router.message(Command("add"))
@router.message(F.text == BTN_ADD)
async def add(message: Message) -> None:
    await message.answer("🚧 «Додати» — скоро")
