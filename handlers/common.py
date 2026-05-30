"""Спільні helpers для хендлерів."""
from datetime import date

import utils
from services import storage


async def today_date() -> date:
    tz = await storage.get_setting("timezone")
    return utils.now_local(tz).date()
