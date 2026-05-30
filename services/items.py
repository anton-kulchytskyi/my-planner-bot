"""Операції з таблицею items."""
from datetime import date as date_, time as time_

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
