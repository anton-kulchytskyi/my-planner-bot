"""Personal Planner Bot — точка входу.

Крок 1: мінімальний бот без БД для перевірки деплою.
Реагує тільки на ALLOWED_USER_ID, решта ігнорується мовчки.
"""
import asyncio
import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import CommandStart
from aiogram.types import Message, TelegramObject, Update, User
from sqlalchemy import text

import config
import database
from services import storage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("planner-bot")

router = Router()


async def allowed_user_middleware(
    handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
    event: Update,
    data: Dict[str, Any],
) -> Any:
    """Пропускає далі тільки апдейти від ALLOWED_USER_ID, решту — мовчки ігнорує."""
    user: User | None = data.get("event_from_user")
    if user is None or user.id != config.ALLOWED_USER_ID:
        return None
    return await handler(event, data)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        "Привіт! 👋 Я твій планувальник.\n"
        "Поки що це тестовий деплой — функціонал додаємо по кроках."
    )


@router.message()
async def fallback(message: Message) -> None:
    await message.answer("Бот живий ✅ (функціонал ще в розробці)")


async def init_db() -> None:
    """Перевіряє з'єднання з БД і засіває дефолтні налаштування."""
    async with database.engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    await storage.ensure_defaults()
    logger.info("БД підключена ✅")


async def main() -> None:
    await init_db()

    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher()
    dp.update.outer_middleware(allowed_user_middleware)
    dp.include_router(router)

    logger.info("Бот запускається (polling)...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
