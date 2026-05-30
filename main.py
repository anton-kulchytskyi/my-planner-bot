"""Personal Planner Bot — точка входу.

Реагує тільки на ALLOWED_USER_ID, решта ігнорується мовчки.
"""
import asyncio
import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart
from aiogram.types import Message, TelegramObject, Update, User
from sqlalchemy import text

import config
import database
from handlers import setup_routers
from keyboards import main_keyboard
from services import scheduler, storage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("planner-bot")

start_router = Router()
fallback_router = Router()


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


@start_router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        "Привіт! 👋 Я твій планувальник.\n"
        "Користуйся кнопками меню знизу.",
        reply_markup=main_keyboard(),
    )


@fallback_router.message()
async def fallback(message: Message) -> None:
    await message.answer(
        "Не розумію 🤔 Скористайся кнопками меню або /help.",
        reply_markup=main_keyboard(),
    )


async def init_db() -> None:
    """Перевіряє з'єднання з БД і засіває дефолтні налаштування."""
    async with database.engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    await storage.ensure_defaults()
    logger.info("БД підключена ✅")


async def main() -> None:
    await init_db()

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode="HTML"),
    )
    dp = Dispatcher()
    dp.update.outer_middleware(allowed_user_middleware)
    dp.include_router(start_router)
    setup_routers(dp)
    dp.include_router(fallback_router)  # catch-all — реєструється останнім

    await scheduler.setup(bot)

    logger.info("Бот запускається (polling)...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
