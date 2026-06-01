"""Детермінна перевірка накладок подій (перетин інтервалів часу).

Без LLM: дешево й точно. Використовується і кнопковим флоу, і агентом.
"""
from datetime import date as date_, time as time_

from models import Item
from services import items


def _minutes(t: time_) -> int:
    return t.hour * 60 + t.minute


def _overlaps(a_s: int, a_e: int, b_s: int, b_e: int) -> bool:
    """Чи перетинаються інтервали [a_s,a_e] та [b_s,b_e] (хвилини).

    Подію без кінця трактуємо як точку (a_s == a_e): вона конфліктує, якщо
    потрапляє всередину іншого інтервалу.
    """
    if a_s == a_e:
        return (b_s <= a_s < b_e) if b_s != b_e else a_s == b_s
    if b_s == b_e:
        return a_s <= b_s < a_e
    return a_s < b_e and b_s < a_e


async def find_conflicts(
    day: date_,
    start: time_ | None,
    end: time_ | None = None,
    *,
    exclude_id: int | None = None,
) -> list[Item]:
    """Події на `day`, чий час перетинається з [start, end]. Без часу -> [] ."""
    if start is None:
        return []
    ns = _minutes(start)
    ne = _minutes(end) if end else ns
    if ne < ns:  # некоректний інтервал (перейшов за північ) — трактуємо як точку
        ne = ns

    result = []
    for event in await items.get_events_on(day):
        if event.time is None or event.id == exclude_id:
            continue
        es = _minutes(event.time)
        ee = _minutes(event.end_time) if event.end_time else es
        if _overlaps(ns, ne, es, ee):
            result.append(event)
    return result
