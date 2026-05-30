"""Допоміжні функції: парсинг/форматування дат і часу, текст."""
from datetime import date, datetime, time
from html import escape


def esc(value: str) -> str:
    """Екранує текст для HTML parse_mode."""
    return escape(value)


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


_MONTHS_GEN = {
    1: "січня", 2: "лютого", 3: "березня", 4: "квітня",
    5: "травня", 6: "червня", 7: "липня", 8: "серпня",
    9: "вересня", 10: "жовтня", 11: "листопада", 12: "грудня",
}


def human_date(value: date) -> str:
    """23 травня"""
    return f"{value.day} {_MONTHS_GEN[value.month]}"


def _days_word(n: int) -> str:
    n = abs(n)
    if 11 <= n % 100 <= 14:
        return "днів"
    last = n % 10
    if last == 1:
        return "день"
    if 2 <= last <= 4:
        return "дні"
    return "днів"


def days_ago(delta: int) -> str:
    """1 -> 'вчора', 3 -> '3 дні тому'"""
    if delta == 1:
        return "вчора"
    return f"{delta} {_days_word(delta)} тому"
