"""Catch-all хендлер вільного тексту — вхід в AI-асистент (реєструється останнім).

Якщо ключа нема — поводиться як старий fallback.
"""
import logging

from aiogram import Router
from aiogram.enums import ChatAction
from aiogram.types import Message

from services import ai

logger = logging.getLogger("planner-bot")

router = Router()

NO_AI = "Не розумію 🤔 Скористайся кнопками меню або /help."
AI_ERROR = "Асистент тимчасово недоступний 🤕 Спробуй пізніше або кнопки меню."


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
        reply = await ai.respond(text)
    except Exception:
        logger.exception("AI respond failed")
        await message.answer(AI_ERROR)
        return

    await message.answer(reply or "…")
