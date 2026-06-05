"""Операції зі списком покупок (таблиця shopping_items)."""
from sqlalchemy import delete, select

from database import async_session
from models import ShoppingItem


async def add_items(titles: list[str]) -> int:
    """Додати одну або кілька позицій. Повертає кількість доданих."""
    clean = [t.strip() for t in titles if t.strip()]
    if not clean:
        return 0
    async with async_session() as session:
        session.add_all([ShoppingItem(title=t) for t in clean])
        await session.commit()
        return len(clean)


async def get_all() -> list[ShoppingItem]:
    async with async_session() as session:
        result = await session.execute(
            select(ShoppingItem).order_by(ShoppingItem.id)
        )
        return list(result.scalars().all())


async def delete_item(item_id: int) -> bool:
    async with async_session() as session:
        item = await session.get(ShoppingItem, item_id)
        if item is None:
            return False
        await session.delete(item)
        await session.commit()
        return True


async def clear_all() -> int:
    """Очистити весь список. Повертає кількість видалених."""
    async with async_session() as session:
        result = await session.execute(delete(ShoppingItem))
        await session.commit()
        return result.rowcount or 0
