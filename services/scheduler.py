"""APScheduler: ранковий briefing + нагадування про події."""
import logging
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

import config
import utils
from models import Item
from services import items, storage

logger = logging.getLogger("planner-bot")

scheduler = AsyncIOScheduler()
_bot: Bot | None = None

BRIEFING_JOB_ID = "briefing"


async def _tz() -> ZoneInfo:
    return ZoneInfo(await storage.get_setting("timezone"))


# --- Briefing ------------------------------------------------------------

async def _send_briefing() -> None:
    from handlers.today import render_today  # lazy — уникаємо циклічного імпорту

    text, keyboard = await render_today()
    await _bot.send_message(config.ALLOWED_USER_ID, text, reply_markup=keyboard)


async def reschedule_briefing() -> None:
    """(Пере)ставляє щоденний briefing за часом із налаштувань."""
    raw = await storage.get_setting("morning_time")
    parsed = utils.parse_time(raw) or time(8, 0)
    tz = await _tz()
    scheduler.add_job(
        _send_briefing,
        CronTrigger(hour=parsed.hour, minute=parsed.minute, timezone=tz),
        id=BRIEFING_JOB_ID,
        replace_existing=True,
    )
    logger.info("Briefing заплановано на %02d:%02d", parsed.hour, parsed.minute)


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
    schedule_event_reminder(item, await _tz())


# --- Старт ---------------------------------------------------------------

async def setup(bot: Bot) -> None:
    global _bot
    _bot = bot

    await reschedule_briefing()

    # Відновлюємо нагадування для майбутніх подій (джоби в пам'яті губляться при рестарті)
    tz = await _tz()
    today = utils.now_local(str(tz)).date()
    for event in await items.get_events_with_time_from(today):
        schedule_event_reminder(event, tz)

    scheduler.start()
    logger.info("Scheduler запущено")
