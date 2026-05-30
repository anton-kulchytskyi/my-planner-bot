"""APScheduler: ранковий briefing + нагадування про події."""
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import config
import keyboards
import utils
from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from models import Item
from services import clock, items, storage

logger = logging.getLogger("planner-bot")

scheduler = AsyncIOScheduler()
_bot: Bot | None = None

BRIEFING_JOB_ID = "briefing"


# --- Briefing ------------------------------------------------------------

async def _send_briefing() -> None:
    from handlers.today import build_today  # lazy — уникаємо циклічного імпорту

    view = await build_today()
    await _bot.send_message(
        config.ALLOWED_USER_ID, view.text, reply_markup=keyboards.inline_column(view.buttons)
    )


async def reschedule_briefing() -> None:
    """(Пере)ставляє щоденний briefing за часом із налаштувань."""
    at = await storage.morning_time()
    tz = await storage.timezone()
    scheduler.add_job(
        _send_briefing,
        CronTrigger(hour=at.hour, minute=at.minute, timezone=tz),
        id=BRIEFING_JOB_ID,
        replace_existing=True,
    )
    logger.info("Briefing заплановано на %02d:%02d", at.hour, at.minute)


# --- Нагадування про події ----------------------------------------------

async def _send_reminder(title: str, time_str: str) -> None:
    await _bot.send_message(
        config.ALLOWED_USER_ID,
        f"⏰ Нагадування: через 1 годину — {utils.esc(title)} ({time_str})",
    )


def schedule_event_reminder(item: Item, tz: ZoneInfo) -> None:
    """Ставить нагадування за 1 годину до події (якщо час іще не минув)."""
    if item.time is None or item.date is None:
        return
    event_dt = datetime.combine(item.date, item.time, tzinfo=tz)
    remind_at = event_dt - timedelta(hours=1)
    if remind_at <= datetime.now(tz):
        return
    scheduler.add_job(
        _send_reminder,
        DateTrigger(run_date=remind_at),
        args=[item.title, utils.fmt_time(item.time)],
        id=f"reminder:{item.id}",
        replace_existing=True,
    )


async def schedule_reminder_for(item: Item) -> None:
    """Зручна обгортка для виклику з хендлера створення події."""
    schedule_event_reminder(item, await storage.timezone())


# --- Старт ---------------------------------------------------------------

async def setup(bot: Bot) -> None:
    global _bot
    _bot = bot

    await reschedule_briefing()

    # Відновлюємо нагадування для майбутніх подій (джоби в пам'яті губляться при рестарті)
    tz = await storage.timezone()
    today = await clock.today()
    for event in await items.get_events_with_time_from(today):
        schedule_event_reminder(event, tz)

    scheduler.start()
    logger.info("Scheduler запущено")
