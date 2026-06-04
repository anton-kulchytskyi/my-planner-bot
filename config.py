"""Конфігурація бота — читається тільки з environment variables."""
import os


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Не задано обов'язкову env-змінну: {name}")
    return value


def _normalize_db_url(url: str) -> str:
    """Приводить URL до asyncpg-формату (Railway дає postgresql:// або postgres://)."""
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://"):]
    return url


BOT_TOKEN: str = _require("BOT_TOKEN")
ALLOWED_USER_ID: int = int(_require("ALLOWED_USER_ID"))

DATABASE_URL: str = _require("DATABASE_URL")
DATABASE_URL_ASYNC: str = _normalize_db_url(DATABASE_URL)

# Опційно: без ключа AI-асистент вимкнений, бот працює як раніше.
ANTHROPIC_API_KEY: str | None = os.environ.get("ANTHROPIC_API_KEY")

# Авточистка: старші за стільки днів завершені/минулі записи видаляються.
# Можна змінити на Railway без редагування коду (за замовчуванням 14).
RETENTION_DAYS: int = int(os.environ.get("RETENTION_DAYS", "14"))

# За скільки хвилин до закінчення події слати нагадування (якщо ввімкнено notify_end).
END_REMINDER_MIN: int = int(os.environ.get("END_REMINDER_MIN", "15"))
