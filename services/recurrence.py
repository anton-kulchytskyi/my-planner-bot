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
                    end_time=rule.end_time,
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


# --- CRUD правил ---------------------------------------------------------

async def create_recurrence(
    item_type: str,
    title: str,
    freq: str,
    *,
    weekdays: str | None = None,
    month_day: int | None = None,
    month: int | None = None,
    time=None,
    end_time=None,
) -> int:
    today = await clock.today()
    async with async_session() as session:
        rule = Recurrence(
            type=item_type,
            title=title,
            freq=freq,
            weekdays=weekdays,
            month_day=month_day,
            month=month,
            time=time,
            end_time=end_time,
            start_date=today,
        )
        session.add(rule)
        await session.commit()
        return rule.id


async def get_recurrence(rule_id: int) -> Recurrence | None:
    async with async_session() as session:
        return await session.get(Recurrence, rule_id)


async def list_recurrences() -> list[Recurrence]:
    async with async_session() as session:
        result = await session.execute(select(Recurrence).order_by(Recurrence.id))
        return list(result.scalars().all())


async def delete_recurrence(rule_id: int) -> bool:
    """Видаляє правило + його МАЙБУТНІ входження (минулі лишаються як історія)."""
    today = await clock.today()
    async with async_session() as session:
        rule = await session.get(Recurrence, rule_id)
        if rule is None:
            return False
        result = await session.execute(
            select(Item).where(Item.recurrence_id == rule_id, Item.date >= today)
        )
        for item in result.scalars().all():
            if item.type == "event" and item.time is not None:
                scheduler.cancel_reminder(item.id)
            await session.delete(item)
        await session.delete(rule)
        await session.commit()
        return True


# --- Опис правила людською мовою -----------------------------------------

_WD = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"]


def _freq_phrase(rule: Recurrence) -> str:
    if rule.freq == "daily":
        return "щодня"
    if rule.freq == "weekly":
        return "щотижня: " + ", ".join(_WD[i] for i in sorted(_weekday_set(rule)))
    if rule.freq == "monthly":
        return f"щомісяця {rule.month_day}-го"
    if rule.freq == "yearly":
        return f"щороку {rule.month_day:02d}.{rule.month:02d}"
    return rule.freq


def describe(rule: Recurrence) -> str:
    icon = "📅" if rule.type == "event" else "📋"
    if rule.time and rule.end_time:
        at = f" {rule.time.strftime('%H:%M')}–{rule.end_time.strftime('%H:%M')}"
    elif rule.time:
        at = f" о {rule.time.strftime('%H:%M')}"
    else:
        at = ""
    return f"{icon} {rule.title} — {_freq_phrase(rule)}{at}"
