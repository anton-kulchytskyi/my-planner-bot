"""Операції з таблицею items."""
from datetime import date as date_, time as time_

from sqlalchemy import and_, nulls_last, or_, select

from database import async_session
from models import Item


async def add_item(
    item_type: str,
    title: str,
    date: date_ | None = None,
    time: time_ | None = None,
) -> Item:
    async with async_session() as session:
        item = Item(type=item_type, title=title, date=date, time=time)
        session.add(item)
        await session.commit()
        await session.refresh(item)
        return item


async def get_overdue_tasks(today: date_) -> list[Item]:
    """Невиконані задачі з датою в минулому."""
    async with async_session() as session:
        result = await session.execute(
            select(Item)
            .where(
                Item.type == "task",
                Item.done.is_(False),
                Item.date.is_not(None),
                Item.date < today,
            )
            .order_by(Item.date)
        )
        return list(result.scalars().all())


async def get_events_on(day: date_) -> list[Item]:
    async with async_session() as session:
        result = await session.execute(
            select(Item)
            .where(Item.type == "event", Item.date == day)
            .order_by(nulls_last(Item.time))
        )
        return list(result.scalars().all())


async def get_tasks_on(day: date_) -> list[Item]:
    """Невиконані задачі на конкретний день."""
    async with async_session() as session:
        result = await session.execute(
            select(Item)
            .where(Item.type == "task", Item.done.is_(False), Item.date == day)
            .order_by(Item.id)
        )
        return list(result.scalars().all())


async def get_upcoming(start: date_, end: date_) -> list[Item]:
    """Події та невиконані задачі в діапазоні дат [start, end]."""
    async with async_session() as session:
        result = await session.execute(
            select(Item)
            .where(
                Item.date >= start,
                Item.date <= end,
                or_(
                    Item.type == "event",
                    and_(Item.type == "task", Item.done.is_(False)),
                ),
            )
            .order_by(Item.date, nulls_last(Item.time))
        )
        return list(result.scalars().all())


async def mark_done(item_id: int) -> bool:
    async with async_session() as session:
        item = await session.get(Item, item_id)
        if item is None or item.type != "task":
            return False
        item.done = True
        await session.commit()
        return True
