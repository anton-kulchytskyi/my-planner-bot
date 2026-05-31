"""Розклад: розгортання правил повторення у звичайні рядки items.

Матеріалізуємо лише вперед (від materialized_through, але не раніше за
сьогодні) — тож видалені вручну входження не воскресають.
"""
import logging
from datetime import date, timedelta

from sqlalchemy import select

from database import async_session
from models import Item, Recurrence
from services import clock, scheduler, storage

logger = logging.getLogger("planner-bot")

HORIZON_DAYS = 60  # на скільки днів уперед тримаємо згенеровані входження


def _weekday_set(rule: Recurrence) -> set[int]:
    if not rule.weekdays:
        return set()
    return {int(x) for x in rule.weekdays.split(",") if x != ""}


def _occurs_on(rule: Recurrence, day: date) -> bool:
    if day < rule.start_date:
        return False
    if rule.freq == "daily":
        return True
    if rule.freq == "weekly":
        return day.weekday() in _weekday_set(rule)
    if rule.freq == "monthly":
        return day.day == rule.month_day
    if rule.freq == "yearly":
        return day.day == rule.month_day and day.month == rule.month
    return False


def _expand(rule: Recurrence, from_date: date, to_date: date) -> list[date]:
    result = []
    day = from_date
    while day <= to_date:
        if _occurs_on(rule, day):
            result.append(day)
        day += timedelta(days=1)
    return result


async def _materialize_one(rule_id: int, today: date, until: date, tz) -> int:
    async with async_session() as session:
        rule = await session.get(Recurrence, rule_id)
        if rule is None:
            return 0

        start = (
            rule.materialized_through + timedelta(days=1)
            if rule.materialized_through
            else rule.start_date
        )
        start = max(start, rule.start_date, today)  # ніколи не раніше сьогодні

        created: list[Item] = []
        if start <= until:
            for day in _expand(rule, start, until):
                item = Item(
                    type=rule.type,
                    title=rule.title,
                    date=day,
                    time=rule.time,
                    recurrence_id=rule.id,
                )
                session.add(item)
                created.append(item)

        rule.materialized_through = until
        await session.commit()

        # нагадування для нових подій з часом (replace_existing -> без дублів)
        for item in created:
            if item.type == "event" and item.time is not None:
                scheduler.schedule_event_reminder(item, tz)

    if created:
        logger.info("Розклад #%s: матеріалізовано %d входжень", rule_id, len(created))
    return len(created)


async def _all_rule_ids() -> list[int]:
    async with async_session() as session:
        result = await session.execute(select(Recurrence.id))
        return [row[0] for row in result.all()]


async def materialize_all() -> None:
    """Розгортає всі правила до горизонту (сьогодні + HORIZON_DAYS)."""
    today = await clock.today()
    until = today + timedelta(days=HORIZON_DAYS)
    tz = await storage.timezone()
    for rule_id in await _all_rule_ids():
        await _materialize_one(rule_id, today, until, tz)


async def materialize_rule(rule_id: int) -> None:
    """Матеріалізувати одне правило негайно (після створення)."""
    today = await clock.today()
    until = today + timedelta(days=HORIZON_DAYS)
    tz = await storage.timezone()
    await _materialize_one(rule_id, today, until, tz)
