"""Хендлер «⚙️ Налаштування» — зміна часу ранкового briefing."""
import keyboards
import utils
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from services import scheduler, storage

router = Router()


class Settings(StatesGroup):
    briefing_time = State()


def _settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🕐 Змінити час briefing", callback_data="set:briefing")]
        ]
    )


@router.message(Command("settings"))
@router.message(F.text == keyboards.BTN_SETTINGS)
async def settings(message: Message) -> None:
    current = utils.fmt_time(await storage.morning_time())
    await message.answer(
        f"⚙️ <b>Налаштування</b>\nBriefing зараз: {current}",
        reply_markup=_settings_keyboard(),
    )


@router.callback_query(F.data == "set:briefing")
async def ask_time(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(Settings.briefing_time)
    await callback.message.edit_text("Введи час briefing (ГГ:ХХ):")
    await callback.answer()


@router.message(Settings.briefing_time)
async def set_time(message: Message, state: FSMContext) -> None:
    parsed = utils.parse_time(message.text)
    if parsed is None:
        await message.answer("Не зрозумів час. Формат ГГ:ХХ (напр. 07:30)")
        return
    await storage.set_morning_time(parsed)
    await state.clear()
    await scheduler.reschedule_briefing()
    await message.answer(f"✅ Briefing о {utils.fmt_time(parsed)}")
