"""Доступ до таблиці settings — сирий key-value + типізовані аксесори."""
from datetime import time
from zoneinfo import ZoneInfo

import utils
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


# --- Типізовані аксесори (парсинг і дефолти живуть тут, не в викликачах) ---

async def timezone() -> ZoneInfo:
    return ZoneInfo(await get_setting("timezone"))


async def morning_time() -> time:
    return utils.parse_time(await get_setting("morning_time")) or time(8, 0)


async def set_morning_time(value: time) -> None:
    await set_setting("morning_time", utils.fmt_time(value))
