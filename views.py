"""Чистий рендер: домен -> текст + специфікації кнопок.

Без БД і без aiogram — лише форматування. Завдяки цьому логіку
повідомлень (секції, відмінювання, групування) можна перевіряти напряму.
"""
from dataclasses import dataclass, field
from datetime import date

import utils
from models import Item, ShoppingItem


@dataclass(frozen=True)
class Button:
    label: str
    callback_data: str


@dataclass(frozen=True)
class View:
    text: str
    buttons: list[Button] = field(default_factory=list)


TODAY_EMPTY = "Сьогодні нічого не заплановано 🎉"
UPCOMING_EMPTY = "На найближчі 7 днів нічого не заплановано 🎉"
DONE_EMPTY = "Немає незавершених задач 🎉"
SHOPPING_EMPTY = "🛒 Список покупок порожній"


def _mark(item: Item) -> str:
    """🔁 для повторюваних (згенерованих з розкладу) записів."""
    return "🔁 " if item.recurrence_id else ""


def _end_bell(item: Item) -> str:
    """ 🔔 — якщо для події ввімкнено нагадування про закінчення."""
    return " 🔔" if item.notify_end else ""


def _time_prefix(item: Item) -> str:
    """'10:00–11:00 — ' / '10:00 — ' / ''"""
    if not item.time:
        return ""
    if item.end_time:
        return f"{utils.fmt_time(item.time)}–{utils.fmt_time(item.end_time)} — "
    return f"{utils.fmt_time(item.time)} — "


def _backlog_lines(backlog: list[Item]) -> list[str]:
    """Секція беклогу (задачі без дати) або [] якщо порожньо."""
    if not backlog:
        return []
    lines = ["📥 <b>Беклог (без дати):</b>"]
    for item in backlog:
        lines.append(f"• {_mark(item)}{utils.esc(item.title)}")
    lines.append("")
    return lines


def today_view(
    today: date,
    overdue: list[Item],
    events: list[Item],
    tasks: list[Item],
    backlog: list[Item] | None = None,
) -> View:
    backlog = backlog or []
    if not (overdue or events or tasks or backlog):
        return View(TODAY_EMPTY)

    lines = [f"☀️ <b>Сьогодні, {utils.human_date(today)}</b>", ""]

    if overdue:
        lines.append("⚠️ <b>Прострочено:</b>")
        for item in overdue:
            delta = (today - item.date).days
            lines.append(f"• {_mark(item)}{utils.esc(item.title)} ({utils.days_ago(delta)})")
        lines.append("")

    if events:
        lines.append("📅 <b>Події:</b>")
        for item in events:
            lines.append(f"• {_time_prefix(item)}{_mark(item)}{utils.esc(item.title)}{_end_bell(item)}")
        lines.append("")

    if tasks:
        lines.append("📋 <b>На сьогодні:</b>")
        for item in tasks:
            lines.append(f"• {_mark(item)}{utils.esc(item.title)}")
        lines.append("")

    lines += _backlog_lines(backlog)

    buttons = [Button(f"✅ {item.title[:30]}", f"tdone:{item.id}") for item in overdue]
    return View("\n".join(lines).strip(), buttons)


def upcoming_view(rows: list[Item], backlog: list[Item] | None = None) -> View:
    backlog = backlog or []
    if not (rows or backlog):
        return View(UPCOMING_EMPTY)

    lines = ["📅 <b>Найближчі 7 днів</b>", ""]
    current = None
    for item in rows:
        if item.date != current:
            if current is not None:
                lines.append("")
            current = item.date
            lines.append(f"<b>{utils.human_date(item.date)}</b>")
        prefix = _time_prefix(item) if item.type == "event" else ""
        bell = _end_bell(item) if item.type == "event" else ""
        lines.append(f"• {prefix}{_mark(item)}{utils.esc(item.title)}{bell}")

    if backlog:
        if rows:
            lines.append("")
        lines += _backlog_lines(backlog)

    return View("\n".join(lines).strip())


def done_view(tasks: list[Item]) -> View:
    if not tasks:
        return View(DONE_EMPTY)
    buttons = [Button(f"☑️ {task.title[:40]}", f"done:{task.id}") for task in tasks]
    return View("✅ <b>Незавершені задачі</b>\nТапни, щоб закрити:", buttons)


def shopping_view(items: list[ShoppingItem]) -> View:
    """Список покупок: тап по позиції = видалити («купив»)."""
    add = Button("➕ Додати", "shop_add")
    if not items:
        return View(SHOPPING_EMPTY, [add])
    buttons = [Button(f"🛒 {it.title[:40]}", f"shop_del:{it.id}") for it in items]
    buttons.append(add)
    buttons.append(Button("🗑 Очистити все", "shop_clear"))
    text = "🛒 <b>Список покупок</b>\nТапни позицію, щоб прибрати:"
    return View(text, buttons)
