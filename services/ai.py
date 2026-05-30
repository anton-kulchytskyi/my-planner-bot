"""AI-асистент на Claude.

Крок 2: агентний цикл tool-use + інструмент читання `list_items`.
Створення/закриття/видалення додаються в наступних кроках.
"""
import json
import logging
from datetime import date as date_cls, timedelta

from anthropic import AsyncAnthropic

import config
import utils
from models import Item
from services import clock, items, scheduler

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
    },
    {
        "name": "create_item",
        "description": (
            "Створити нову задачу або подію.\n"
            "• type: 'task' (задача) або 'event' (подія)\n"
            "• title: коротка назва\n"
            "• date: 'YYYY-MM-DD'. Відносні дати ('завтра', 'у п'ятницю') ти "
            "резолвиш сам на основі поточної дати. Для події дата ОБОВ'ЯЗКОВА, "
            "для задачі — опційна (тоді задача без дедлайну).\n"
            "• time: 'HH:MM', лише для події й лише якщо користувач назвав час. "
            "Для події з часом автоматично ставиться нагадування за годину.\n"
            "Якщо бракує назви або дати події — спершу перепитай користувача, "
            "не вигадуй."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["task", "event"]},
                "title": {"type": "string"},
                "date": {"type": "string", "description": "YYYY-MM-DD"},
                "time": {"type": "string", "description": "HH:MM (лише подія)"},
            },
            "required": ["type", "title"],
        },
        "cache_control": {"type": "ephemeral"},
    },
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


async def _create_item(tool_input: dict) -> dict:
    item_type = tool_input.get("type")
    title = (tool_input.get("title") or "").strip()
    raw_date = tool_input.get("date")
    raw_time = tool_input.get("time")

    if item_type not in ("task", "event"):
        return {"error": "type має бути 'task' або 'event'"}
    if not title:
        return {"error": "потрібна назва (title)"}

    the_date = None
    if raw_date:
        try:
            the_date = date_cls.fromisoformat(raw_date)
        except (ValueError, TypeError):
            return {"error": f"невалідна дата '{raw_date}', очікую YYYY-MM-DD"}

    if item_type == "event" and the_date is None:
        return {"error": "для події потрібна дата"}

    the_time = None
    if item_type == "event" and raw_time:
        the_time = utils.parse_time(raw_time)
        if the_time is None:
            return {"error": f"невалідний час '{raw_time}', очікую HH:MM"}

    item = await items.add_item(item_type, title, date=the_date, time=the_time)

    reminder_set = False
    if item_type == "event" and the_time is not None:
        await scheduler.schedule_reminder_for(item)
        reminder_set = True

    return {"created": _serialize(item), "reminder_set": reminder_set}


async def _run_tool(name: str, tool_input: dict) -> str:
    if name == "list_items":
        result = await _list_items(tool_input.get("scope", ""))
    elif name == "create_item":
        result = await _create_item(tool_input)
    else:
        result = {"error": f"unknown tool: {name}"}
    return json.dumps(result, ensure_ascii=False)


# --- Промпт і агентний цикл ----------------------------------------------

async def _system_prompt() -> str:
    now = await clock.now()
    return (
        "Ти — особистий асистент-планувальник усередині Telegram-бота. "
        "Відповідай ЧИСТОЮ українською мовою, стисло й по-дружньому. "
        "Категорично без русизмів і суржику. Вживай правильні слова: "
        "«подія» (не «событие»), «задача», «сьогодні», «виконано», «прострочено», "
        "«найближчі дні». Якщо сумніваєшся в слові — обери питомо українське.\n"
        f"Поточні дата й час користувача: {now:%Y-%m-%d %H:%M} ({now.tzname()}). "
        "Коли користувач питає про свої задачі, події чи розклад — спершу виклич "
        "list_items, щоб подивитися актуальні дані, і відповідай на їх основі.\n"
        "Коли користувач просить щось додати — виклич create_item. Відносні дати "
        "(«завтра», «у п'ятницю», «через тиждень») переводь у конкретну дату сам, "
        "спираючись на поточну. Після створення коротко підтвердь, що саме додав "
        "(назва, дата, час) і чи поставлено нагадування.\n"
        "Закривати й видаляти записи ти поки не вмієш — про це скажи, якщо попросять."
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
