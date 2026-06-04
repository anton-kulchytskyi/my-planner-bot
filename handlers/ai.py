"""Catch-all хендлер вільного тексту — вхід в AI-асистент (реєструється останнім).

Якщо ключа нема — поводиться як старий fallback.
"""
import logging

import utils
from aiogram import F, Router
from aiogram.enums import ChatAction
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from services import ai, items, scheduler

logger = logging.getLogger("planner-bot")

router = Router()

NO_AI = "Не розумію 🤔 Скористайся кнопками меню або /help."
AI_ERROR = "Асистент тимчасово недоступний 🤕 Спробуй пізніше або кнопки меню."


def _confirm_keyboard(action: str, item_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Так", callback_data=f"aiconfirm:{action}:{item_id}"),
                InlineKeyboardButton(text="✖️ Ні", callback_data="aicancel"),
            ]
        ]
    )


@router.message(Command("reset"))
async def reset_session(message: Message) -> None:
    ai.reset(message.from_user.id)
    await message.answer("Контекст розмови очищено 🧹")


@router.message()
async def free_text(message: Message) -> None:
    if not ai.enabled():
        await message.answer(NO_AI)
        return

    text = message.text
    if not text:
        await message.answer("Поки що я розумію лише текст 🙂")
        return

    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    try:
        reply = await ai.respond(message.from_user.id, text)
    except Exception:
        logger.exception("AI respond failed")
        await message.answer(AI_ERROR)
        return

    if reply.confirm:
        c = reply.confirm
        verb = "Закрити задачу" if c["action"] == "close" else "Видалити"
        await message.answer(
            f"{verb}: «{utils.esc(c['title'])}»?",
            reply_markup=_confirm_keyboard(c["action"], c["id"]),
        )
        return

    # Вільний текст моделі: легкий Markdown → HTML (екранує спецсимволи)
    await message.answer(utils.md_to_html(reply.text) if reply.text else "…")


@router.callback_query(F.data.startswith("aiconfirm:"))
async def confirm_action(callback: CallbackQuery) -> None:
    _, action, raw_id = callback.data.split(":")
    item_id = int(raw_id)
    if action == "close":
        ok = await items.mark_done(item_id)
        msg = "✅ Задачу закрито" if ok else "Не вдалося — можливо, вже закрита."
    else:  # delete
        ok = await items.delete_item(item_id)
        if ok:
            scheduler.cancel_reminder(item_id)
            msg = "🗑 Видалено"
        else:
            msg = "Не вдалося — запис не знайдено."
    await callback.message.edit_text(msg)
    await callback.answer()


@router.callback_query(F.data == "aicancel")
async def cancel_action(callback: CallbackQuery) -> None:
    await callback.message.edit_text("Скасовано.")
    await callback.answer()
