"""AI-асистент на Claude.

Крок 2: агентний цикл tool-use + інструмент читання `list_items`.
Створення/закриття/видалення додаються в наступних кроках.
"""
import json
import logging
from datetime import timedelta

from anthropic import AsyncAnthropic

import config
from models import Item
from services import clock, items

logger = logging.getLogger("planner-bot")

MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 1024
MAX_ITERATIONS = 6  # запобіжник від runaway tool-loop

_client: AsyncAnthropic | None = (
    AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY) if config.ANTHROPIC_API_KEY else None
)


def enabled() -> bool:
    return _client is not None


# --- Інструменти ---------------------------------------------------------

TOOLS = [
    {
        "name": "list_items",
        "description": (
            "Отримати задачі та події користувача. Використовуй, коли треба знати, "
            "що в нього заплановано, перш ніж відповідати чи радити.\n"
            "scope:\n"
            "• today — прострочені задачі, події й задачі на сьогодні\n"
            "• upcoming — події й задачі на наступні 7 днів\n"
            "• open — незавершені задачі (сьогодні + без дати)\n"
            "• overdue — лише прострочені задачі"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "scope": {
                    "type": "string",
                    "enum": ["today", "upcoming", "open", "overdue"],
                }
            },
            "required": ["scope"],
        },
        "cache_control": {"type": "ephemeral"},
    }
]


def _serialize(item: Item) -> dict:
    return {
        "id": item.id,
        "type": item.type,
        "title": item.title,
        "date": item.date.isoformat() if item.date else None,
        "time": item.time.strftime("%H:%M") if item.time else None,
        "done": item.done,
    }


async def _list_items(scope: str) -> dict:
    today = await clock.today()
    if scope == "today":
        return {
            "today": today.isoformat(),
            "overdue": [_serialize(i) for i in await items.get_overdue_tasks(today)],
            "events_today": [_serialize(i) for i in await items.get_events_on(today)],
            "tasks_today": [_serialize(i) for i in await items.get_tasks_on(today)],
        }
    if scope == "upcoming":
        rows = await items.get_upcoming(today + timedelta(days=1), today + timedelta(days=7))
        return {"upcoming": [_serialize(i) for i in rows]}
    if scope == "open":
        return {"open_tasks": [_serialize(i) for i in await items.get_open_tasks(today)]}
    if scope == "overdue":
        return {"overdue": [_serialize(i) for i in await items.get_overdue_tasks(today)]}
    return {"error": f"unknown scope: {scope}"}


async def _run_tool(name: str, tool_input: dict) -> str:
    if name == "list_items":
        result = await _list_items(tool_input.get("scope", ""))
    else:
        result = {"error": f"unknown tool: {name}"}
    return json.dumps(result, ensure_ascii=False)


# --- Промпт і агентний цикл ----------------------------------------------

async def _system_prompt() -> str:
    now = await clock.now()
    return (
        "Ти — особистий асистент-планувальник усередині Telegram-бота. "
        "Відповідай українською, стисло й по-дружньому. "
        f"Поточні дата й час користувача: {now:%Y-%m-%d %H:%M} ({now.tzname()}). "
        "Коли користувач питає про свої задачі, події чи розклад — спершу виклич "
        "list_items, щоб подивитися актуальні дані, і відповідай на їх основі. "
        "Поки що ти вмієш лише дивитися (створення й закриття задач додамо незабаром)."
    )


def _text_of(response) -> str:
    return "".join(block.text for block in response.content if block.type == "text")


async def respond(text: str) -> str:
    """Агентний цикл: модель може викликати інструменти, поки не дасть фінальну відповідь."""
    system = await _system_prompt()
    messages: list[dict] = [{"role": "user", "content": text}]

    for _ in range(MAX_ITERATIONS):
        response = await _client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system,
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason != "tool_use":
            return _text_of(response)

        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                output = await _run_tool(block.name, block.input)
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": output}
                )
        messages.append({"role": "user", "content": tool_results})

    logger.warning("AI: вичерпано ліміт ітерацій tool-loop")
    return "Щось я заплутався 🤔 Спробуй переформулювати."
