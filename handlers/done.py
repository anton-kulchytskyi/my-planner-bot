"""Хендлер «✅ Виконано» (заглушка — наповнюється в наступному кроці)."""
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from keyboards import BTN_DONE

router = Router()


@router.message(Command("done"))
@router.message(F.text == BTN_DONE)
async def done(message: Message) -> None:
    await message.answer("🚧 «Виконано» — скоро")
