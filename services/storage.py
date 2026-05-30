"""Доступ до таблиці settings з дефолтними значеннями."""
from database import async_session
from models import Setting

DEFAULTS: dict[str, str] = {
    "morning_time": "08:00",
    "timezone": "Europe/Kyiv",
}


async def get_setting(key: str) -> str:
    async with async_session() as session:
        obj = await session.get(Setting, key)
        if obj is not None:
            return obj.value
    return DEFAULTS.get(key, "")


async def set_setting(key: str, value: str) -> None:
    async with async_session() as session:
        obj = await session.get(Setting, key)
        if obj is None:
            session.add(Setting(key=key, value=value))
        else:
            obj.value = value
        await session.commit()


async def ensure_defaults() -> None:
    """Засіває дефолтні налаштування, якщо їх ще немає."""
    async with async_session() as session:
        for key, value in DEFAULTS.items():
            if await session.get(Setting, key) is None:
                session.add(Setting(key=key, value=value))
        await session.commit()
