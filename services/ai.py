"""AI-асистент на Claude.

Агентний цикл tool-use з інструментами: list_items (читання),
create_item (створення), close_task / delete_item (з підтвердженням користувача).
"""
import json
import logging
import time
from dataclasses import dataclass
from datetime import date as date_cls, timedelta

from anthropic import AsyncAnthropic

import config
import utils
from models import Item
from services import clock, items, recurrence, scheduler

logger = logging.getLogger("planner-bot")

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 1024
MAX_ITERATIONS = 6  # запобіжник від runaway tool-loop

MAX_HISTORY = 10          # повідомлень (≈5 обмінів) тримаємо в контексті
HISTORY_TTL = 30 * 60     # секунд тиші до авто-скидання

_client: AsyncAnthropic | None = (
    AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY) if config.ANTHROPIC_API_KEY else None
)


def enabled() -> bool:
    return _client is not None


@dataclass
class AgentReply:
    """Відповідь агента: або текст, або запит на підтвердження дії."""
    text: str | None = None
    confirm: dict | None = None  # {"action": "close"|"delete", "id": int, "title": str}


# --- Коротка історія розмови (in-memory, для фоллоу-апів) -----------------

_sessions: dict[int, dict] = {}  # user_id -> {"messages": [...], "ts": monotonic}


def _get_history(user_id: int) -> list[dict]:
    session = _sessions.get(user_id)
    if session is None:
        return []
    if time.monotonic() - session["ts"] > HISTORY_TTL:
        _sessions.pop(user_id, None)
        return []
    return session["messages"]


def _save_turn(user_id: int, user_text: str, assistant_text: str) -> None:
    session = _sessions.setdefault(user_id, {"messages": [], "ts": 0.0})
    session["messages"].append({"role": "user", "content": user_text})
    session["messages"].append({"role": "assistant", "content": assistant_text})
    session["messages"] = session["messages"][-MAX_HISTORY:]  # парами -> зріз з role=user
    session["ts"] = time.monotonic()


def reset(user_id: int) -> None:
    _sessions.pop(user_id, None)


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
            "• end: 'HH:MM' — час закінчення події. Постав, якщо користувач назвав "
            "тривалість («годину» -> end = time+1:00) або кінець («до 16:00»).\n"
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
                "end": {"type": "string", "description": "HH:MM кінець (лише подія)"},
            },
            "required": ["type", "title"],
        },
    },
    {
        "name": "close_task",
        "description": (
            "Позначити задачу виконаною. Працює ЛИШЕ для задач (type=task), "
            "не для подій. Передай id задачі (дізнайся його через list_items). "
            "Дія потребує підтвердження користувача — не вважай її виконаною одразу."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"id": {"type": "integer"}},
            "required": ["id"],
        },
    },
    {
        "name": "delete_item",
        "description": (
            "Видалити запис (задачу або подію) за id. Єдиний спосіб прибрати "
            "помилкову чи скасовану подію. Дія потребує підтвердження користувача."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"id": {"type": "integer"}},
            "required": ["id"],
        },
    },
    {
        "name": "items_on",
        "description": (
            "Що заплановано на конкретну дату (події та задачі, включно з "
            "повторюваними). Використовуй ПЕРЕД створенням події з часом, щоб "
            "перевірити накладки й завантаженість дня."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"date": {"type": "string", "description": "YYYY-MM-DD"}},
            "required": ["date"],
        },
    },
    {
        "name": "create_recurrence",
        "description": (
            "Створити повторюване правило (розклад). Приклади: «щовівторка о 18 "
            "тренування», «по буднях о 9 стендап», «14 березня щороку день "
            "народження мами».\n"
            "• type: 'task' або 'event'\n"
            "• freq: daily | weekly | monthly | yearly\n"
            "• weekdays: масив чисел для weekly (Пн=0 … Нд=6), напр. [1,3]\n"
            "• month_day: число 1–31 для monthly та yearly\n"
            "• month: 1–12 для yearly\n"
            "• time: 'HH:MM', лише для події"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["task", "event"]},
                "title": {"type": "string"},
                "freq": {"type": "string", "enum": ["daily", "weekly", "monthly", "yearly"]},
                "weekdays": {"type": "array", "items": {"type": "integer"}},
                "month_day": {"type": "integer"},
                "month": {"type": "integer"},
                "time": {"type": "string", "description": "HH:MM (лише подія)"},
                "end": {"type": "string", "description": "HH:MM кінець (лише подія)"},
            },
            "required": ["type", "title", "freq"],
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
        "end": item.end_time.strftime("%H:%M") if item.end_time else None,
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
    the_end = None
    if item_type == "event" and raw_time:
        the_time = utils.parse_time(raw_time)
        if the_time is None:
            return {"error": f"невалідний час '{raw_time}', очікую HH:MM"}
        raw_end = tool_input.get("end")
        if raw_end:
            the_end = utils.parse_time(raw_end)
            if the_end is None:
                return {"error": f"невалідний кінець '{raw_end}', очікую HH:MM"}

    item = await items.add_item(
        item_type, title, date=the_date, time=the_time, end_time=the_end
    )

    reminder_set = False
    if item_type == "event" and the_time is not None:
        await scheduler.schedule_reminder_for(item)
        reminder_set = True

    return {"created": _serialize(item), "reminder_set": reminder_set}


async def _items_on(date_str: str) -> dict:
    try:
        day = date_cls.fromisoformat(date_str)
    except (ValueError, TypeError):
        return {"error": f"невалідна дата '{date_str}', очікую YYYY-MM-DD"}
    return {
        "date": day.isoformat(),
        "events": [_serialize(i) for i in await items.get_events_on(day)],
        "tasks": [_serialize(i) for i in await items.get_tasks_on(day)],
    }


async def _create_recurrence(tool_input: dict) -> dict:
    item_type = tool_input.get("type")
    title = (tool_input.get("title") or "").strip()
    freq = tool_input.get("freq")

    if item_type not in ("task", "event"):
        return {"error": "type має бути 'task' або 'event'"}
    if not title:
        return {"error": "потрібна назва (title)"}
    if freq not in ("daily", "weekly", "monthly", "yearly"):
        return {"error": "freq має бути daily/weekly/monthly/yearly"}

    weekdays = month_day = month = None
    if freq == "weekly":
        days = tool_input.get("weekdays") or []
        if not days or not all(isinstance(d, int) and 0 <= d <= 6 for d in days):
            return {"error": "для weekly потрібен weekdays — масив чисел 0..6"}
        weekdays = ",".join(str(d) for d in sorted(set(days)))
    elif freq in ("monthly", "yearly"):
        month_day = tool_input.get("month_day")
        if not isinstance(month_day, int) or not 1 <= month_day <= 31:
            return {"error": "потрібен month_day 1..31"}
        if freq == "yearly":
            month = tool_input.get("month")
            if not isinstance(month, int) or not 1 <= month <= 12:
                return {"error": "для yearly потрібен month 1..12"}

    the_time = the_end = None
    if item_type == "event" and tool_input.get("time"):
        the_time = utils.parse_time(tool_input["time"])
        if the_time is None:
            return {"error": f"невалідний час '{tool_input['time']}', очікую HH:MM"}
        if tool_input.get("end"):
            the_end = utils.parse_time(tool_input["end"])
            if the_end is None:
                return {"error": f"невалідний кінець '{tool_input['end']}', очікую HH:MM"}

    rule_id = await recurrence.create_recurrence(
        item_type, title, freq,
        weekdays=weekdays, month_day=month_day, month=month,
        time=the_time, end_time=the_end,
    )
    await recurrence.materialize_rule(rule_id)
    rule = await recurrence.get_recurrence(rule_id)
    return {"created_recurrence": recurrence.describe(rule)}


async def _run_tool(name: str, tool_input: dict) -> str:
    if name == "list_items":
        result = await _list_items(tool_input.get("scope", ""))
    elif name == "create_item":
        result = await _create_item(tool_input)
    elif name == "items_on":
        result = await _items_on(tool_input.get("date", ""))
    elif name == "create_recurrence":
        result = await _create_recurrence(tool_input)
    else:
        result = {"error": f"unknown tool: {name}"}
    return json.dumps(result, ensure_ascii=False)


async def _prepare_confirm(name: str, tool_input: dict) -> dict:
    """Валідує деструктивну дію. ok=True -> треба підтвердження; інакше -> помилка моделі."""
    try:
        item_id = int(tool_input.get("id"))
    except (TypeError, ValueError):
        return {"ok": False, "error": "потрібен числовий id"}

    item = await items.get_item(item_id)
    if item is None:
        return {"ok": False, "error": f"запис id={item_id} не знайдено"}

    if name == "close_task":
        if item.type != "task":
            return {"ok": False, "error": "закрити можна лише задачу; подію можна видалити"}
        if item.done:
            return {"ok": False, "error": "задача вже виконана"}
        return {"ok": True, "confirm": {"action": "close", "id": item_id, "title": item.title}}

    # delete_item
    return {"ok": True, "confirm": {"action": "delete", "id": item_id, "title": item.title}}


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
        "У події є початок (time) і кінець (end). Подія займає інтервал [time, end]. "
        "Якщо користувач назвав тривалість — порахуй end сам.\n"
        "ПЕРЕД створенням події з часом виклич items_on(дата) і перевір накладки за "
        "ІНТЕРВАЛАМИ: дві події конфліктують, якщо їхні проміжки [time, end] "
        "перетинаються. Якщо є перетин — попередь про конкретну накладку; якщо день "
        "насичений — згадай. Прохання все одно виконуй, але додай коротке "
        "попередження й, за потреби, запропонуй інший час.\n"
        "Коли користувач описує регулярність («щовівторка», «по буднях», «щороку "
        "14 березня») — це розклад, виклич create_recurrence, а не create_item.\n"
        "Коли користувач просить закрити або видалити запис: знайди його через "
        "list_items, зіставляючи назву НЕЧУТЛИВО ДО РЕГІСТРУ й за змістом "
        "(часткова згадка теж підходить, напр. «зустріч» = «Зустріч з Іваном»). "
        "Знайшовши — ОДРАЗУ виклич close_task(id) (лише задачі) або delete_item(id). "
        "КАТЕГОРИЧНО НЕ питай «ти впевнений?» і не проси підтвердження текстом — "
        "після виклику інструмента бот САМ покаже кнопки [Так/Ні]. Текстом уточнюй "
        "лише тоді, коли під опис підходить кілька записів або жодного."
    )


def _text_of(response) -> str:
    return "".join(block.text for block in response.content if block.type == "text")


async def respond(user_id: int, text: str) -> AgentReply:
    """Агентний цикл. Повертає текст або запит на підтвердження деструктивної дії."""
    system = await _system_prompt()
    messages: list[dict] = list(_get_history(user_id)) + [{"role": "user", "content": text}]

    for _ in range(MAX_ITERATIONS):
        response = await _client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=system,
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason != "tool_use":
            final = _text_of(response)
            _save_turn(user_id, text, final)
            return AgentReply(text=final)

        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            if block.name in ("close_task", "delete_item"):
                prepared = await _prepare_confirm(block.name, block.input)
                if prepared["ok"]:
                    return AgentReply(confirm=prepared["confirm"])  # чекаємо кнопку
                output = json.dumps({"error": prepared["error"]}, ensure_ascii=False)
            else:
                output = await _run_tool(block.name, block.input)
            tool_results.append(
                {"type": "tool_result", "tool_use_id": block.id, "content": output}
            )
        messages.append({"role": "user", "content": tool_results})

    logger.warning("AI: вичерпано ліміт ітерацій tool-loop")
    return AgentReply(text="Щось я заплутався 🤔 Спробуй переформулювати.")
