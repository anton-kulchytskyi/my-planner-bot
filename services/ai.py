"""AI-асистент на Claude. Крок 1: проста відповідь без інструментів.

Інструменти (читання/створення/підтвердження) додаються в наступних кроках.
"""
import logging

from anthropic import AsyncAnthropic

import config
from services import clock

logger = logging.getLogger("planner-bot")

MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 1024

_client: AsyncAnthropic | None = (
    AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY) if config.ANTHROPIC_API_KEY else None
)


def enabled() -> bool:
    return _client is not None


async def _system_prompt() -> str:
    now = await clock.now()
    return (
        "Ти — особистий асистент-планувальник усередині Telegram-бота. "
        "Відповідай українською, стисло й по-дружньому. "
        f"Поточні дата й час користувача: {now:%Y-%m-%d %H:%M} ({now.tzname()}). "
        "Поки що ти лише спілкуєшся — інструменти для роботи із задачами й подіями "
        "додамо незабаром."
    )


async def respond(text: str) -> str:
    """Один прохід: текст користувача -> відповідь моделі (без інструментів)."""
    system = await _system_prompt()
    response = await _client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=system,
        messages=[{"role": "user", "content": text}],
    )
    return "".join(block.text for block in response.content if block.type == "text")
