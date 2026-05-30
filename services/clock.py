"""Єдине джерело локального часу/дати в таймзоні користувача."""
from datetime import date, datetime

from services import storage


async def now() -> datetime:
    return datetime.now(await storage.timezone())


async def today() -> date:
    return (await now()).date()


async def year() -> int:
    return (await now()).year
