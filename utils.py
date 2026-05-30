"""Допоміжні функції: парсинг дат/часу і локальний час."""
from datetime import date, datetime, time
from html import escape
from zoneinfo import ZoneInfo


def esc(value: str) -> str:
    """Екранує текст для HTML parse_mode."""
    return escape(value)


def now_local(tz_name: str) -> datetime:
    return datetime.now(ZoneInfo(tz_name))


def parse_date(value: str, *, default_year: int) -> date | None:
    """ДД.ММ.РРРР або ДД.ММ (рік = default_year). Повертає None якщо невалідно."""
    value = value.strip()
    try:
        if value.count(".") == 2:
            return datetime.strptime(value, "%d.%m.%Y").date()
        parsed = datetime.strptime(value, "%d.%m")
        return date(default_year, parsed.month, parsed.day)
    except ValueError:
        return None


def parse_time(value: str) -> time | None:
    """ГГ:ХХ. Повертає None якщо невалідно."""
    try:
        return datetime.strptime(value.strip(), "%H:%M").time()
    except ValueError:
        return None


def fmt_date(value: date) -> str:
    return value.strftime("%d.%m.%Y")


def fmt_time(value: time) -> str:
    return value.strftime("%H:%M")
