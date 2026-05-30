"""Конфігурація бота — читається тільки з environment variables."""
import os


def _require(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Не задано обов'язкову env-змінну: {name}")
    return value


BOT_TOKEN: str = _require("BOT_TOKEN")
ALLOWED_USER_ID: int = int(_require("ALLOWED_USER_ID"))

# DATABASE_URL додамо на Кроці 2 (PostgreSQL)
DATABASE_URL: str | None = os.environ.get("DATABASE_URL")
