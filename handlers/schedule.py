"""Хендлер «🔁 Розклад» — перегляд / створення / видалення правил повторення."""
import keyboards
import utils
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from services import recurrence

router = Router()

WD = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"]
HOUR_FROM, HOUR_TO = 8, 22


class Schedule(StatesGroup):
    title = State()
    freq = State()
    weekly_days = State()
    monthly_day = State()
    yearly_date = State()
    event_hour = State()
    event_minute = State()


# --- Клавіатури ----------------------------------------------------------

def _freq_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Щодня", callback_data="sfreq:daily"),
                InlineKeyboardButton(text="Щотижня", callback_data="sfreq:weekly"),
            ],
            [
                InlineKeyboardButton(text="Щомісяця", callback_data="sfreq:monthly"),
                InlineKeyboardButton(text="Щороку", callback_data="sfreq:yearly"),
            ],
        ]
    )


def _weekday_kb(selected: set[int]) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(
            text=("✅ " + WD[i]) if i in selected else WD[i],
            callback_data=f"swd:{i}",
        )
        for i in range(7)
    ]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            buttons[:4],
            buttons[4:],
            [InlineKeyboardButton(text="Готово ➡️", callback_data="swddone")],
        ]
    )


def _hour_kb() -> InlineKeyboardMarkup:
    hours = list(range(HOUR_FROM, HOUR_TO + 1))
    rows = [
        [
            InlineKeyboardButton(text=f"{h:02d}", callback_data=f"shour:{h}")
            for h in hours[i : i + 5]
        ]
        for i in range(0, len(hours), 5)
    ]
    rows.append([InlineKeyboardButton(text="⏭ Без часу", callback_data="shour:none")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _minute_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=f"{m:02d}", callback_data=f"smin:{m}")
                for m in (0, 15, 30, 45)
            ]
        ]
    )


# --- Перегляд списку -----------------------------------------------------

async def build_schedule() -> tuple[str, InlineKeyboardMarkup]:
    rules = await recurrence.list_recurrences()
    rows: list[list[InlineKeyboardButton]] = []
    if not rules:
        text = "🔁 <b>Розклад</b>\n\nПоки порожньо. Додай перше правило 👇"
    else:
        lines = ["🔁 <b>Розклад</b>", ""]
        for idx, rule in enumerate(rules, 1):
            lines.append(f"{idx}. {utils.esc(recurrence.describe(rule))}")
            rows.append(
                [InlineKeyboardButton(text=f"🗑 {rule.title[:25]}", callback_data=f"schedel:{rule.id}")]
            )
        text = "\n".join(lines)
    rows.append([InlineKeyboardButton(text="➕ Додати розклад", callback_data="schedadd")])
    return text, InlineKeyboardMarkup(inline_keyboard=rows)


@router.message(Command("schedule"))
@router.message(F.text == keyboards.BTN_SCHEDULE)
async def schedule_entry(message: Message, state: FSMContext) -> None:
    await state.clear()
    text, kb = await build_schedule()
    await message.answer(text, reply_markup=kb)


# --- Видалення правила ---------------------------------------------------

@router.callback_query(F.data.startswith("schedel:"))
async def del_prompt(callback: CallbackQuery) -> None:
    rule_id = int(callback.data.split(":")[1])
    rule = await recurrence.get_recurrence(rule_id)
    if rule is None:
        text, kb = await build_schedule()
        await callback.message.edit_text(text, reply_markup=kb)
        await callback.answer("Вже немає")
        return
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Видалити", callback_data=f"schedyes:{rule_id}"),
                InlineKeyboardButton(text="✖️ Ні", callback_data="schedno"),
            ]
        ]
    )
    await callback.message.edit_text(
        f"Видалити розклад?\n{utils.esc(recurrence.describe(rule))}\n\n"
        "Майбутні входження теж зникнуть.",
        reply_markup=kb,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("schedyes:"))
async def del_confirm(callback: CallbackQuery) -> None:
    rule_id = int(callback.data.split(":")[1])
    await recurrence.delete_recurrence(rule_id)
    text, kb = await build_schedule()
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer("🗑 Видалено")


@router.callback_query(F.data == "schedno")
async def del_cancel(callback: CallbackQuery) -> None:
    text, kb = await build_schedule()
    await callback.message.edit_text(text, reply_markup=kb)
    await callback.answer("Скасовано")


# --- Створення правила (FSM) ---------------------------------------------

@router.callback_query(F.data == "schedadd")
async def add_choose_type(callback: CallbackQuery) -> None:
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📋 Задача", callback_data="schednew:task"),
                InlineKeyboardButton(text="📅 Подія", callback_data="schednew:event"),
            ]
        ]
    )
    await callback.message.edit_text("Повторювана задача чи подія?", reply_markup=kb)
    await callback.answer()


@router.callback_query(F.data.startswith("schednew:"))
async def add_set_type(callback: CallbackQuery, state: FSMContext) -> None:
    item_type = callback.data.split(":")[1]
    await state.set_data({"type": item_type})
    await state.set_state(Schedule.title)
    label = "📋 Повторювана задача." if item_type == "task" else "📅 Повторювана подія."
    await callback.message.edit_text(f"{label}\nНазва?")
    await callback.answer()


@router.message(Schedule.title)
async def add_title(message: Message, state: FSMContext) -> None:
    await state.update_data(title=message.text.strip())
    await state.set_state(Schedule.freq)
    await message.answer("Як часто?", reply_markup=_freq_kb())


@router.callback_query(Schedule.freq, F.data.startswith("sfreq:"))
async def add_freq(callback: CallbackQuery, state: FSMContext) -> None:
    freq = callback.data.split(":")[1]
    await state.update_data(freq=freq)
    if freq == "daily":
        await callback.message.edit_text("Щодня.")
        await callback.answer()
        await _proceed_after_params(callback.message, state)
    elif freq == "weekly":
        await state.update_data(weekdays=[])
        await state.set_state(Schedule.weekly_days)
        await callback.message.edit_text("Обери дні тижня:", reply_markup=_weekday_kb(set()))
        await callback.answer()
    elif freq == "monthly":
        await state.set_state(Schedule.monthly_day)
        await callback.message.edit_text("Якого числа місяця? (1–31)")
        await callback.answer()
    else:  # yearly
        await state.set_state(Schedule.yearly_date)
        await callback.message.edit_text("Яке число й місяць? (ДД.ММ, напр. 14.03)")
        await callback.answer()


@router.callback_query(Schedule.weekly_days, F.data.startswith("swd:"))
async def toggle_weekday(callback: CallbackQuery, state: FSMContext) -> None:
    i = int(callback.data.split(":")[1])
    data = await state.get_data()
    days = set(data.get("weekdays", []))
    days.discard(i) if i in days else days.add(i)
    await state.update_data(weekdays=sorted(days))
    await callback.message.edit_reply_markup(reply_markup=_weekday_kb(days))
    await callback.answer()


@router.callback_query(Schedule.weekly_days, F.data == "swddone")
async def weekday_done(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    if not data.get("weekdays"):
        await callback.answer("Обери хоча б один день", show_alert=True)
        return
    chosen = ", ".join(WD[i] for i in data["weekdays"])
    await callback.message.edit_text(f"Дні: {chosen}")
    await callback.answer()
    await _proceed_after_params(callback.message, state)


@router.message(Schedule.monthly_day)
async def add_monthly_day(message: Message, state: FSMContext) -> None:
    try:
        day = int(message.text.strip())
    except (ValueError, TypeError):
        day = 0
    if not 1 <= day <= 31:
        await message.answer("Введи число від 1 до 31.")
        return
    await state.update_data(month_day=day)
    await _proceed_after_params(message, state)


@router.message(Schedule.yearly_date)
async def add_yearly_date(message: Message, state: FSMContext) -> None:
    parts = message.text.strip().split(".")
    try:
        day, month = int(parts[0]), int(parts[1])
        valid = 1 <= day <= 31 and 1 <= month <= 12
    except (ValueError, IndexError):
        valid = False
    if not valid:
        await message.answer("Формат ДД.ММ (напр. 14.03).")
        return
    await state.update_data(month_day=day, month=month)
    await _proceed_after_params(message, state)


async def _proceed_after_params(target: Message, state: FSMContext) -> None:
    """Після частоти: для події — питаємо час, для задачі — одразу зберігаємо."""
    data = await state.get_data()
    if data["type"] == "event":
        await state.set_state(Schedule.event_hour)
        await target.answer("О котрій? Обери годину:", reply_markup=_hour_kb())
    else:
        await _finalize(target, state)


@router.callback_query(Schedule.event_hour, F.data == "shour:none")
async def hour_none(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text("Без часу.")
    await callback.answer()
    await _finalize(callback.message, state)


@router.callback_query(Schedule.event_hour, F.data.startswith("shour:"))
async def hour_chosen(callback: CallbackQuery, state: FSMContext) -> None:
    hour = int(callback.data.split(":")[1])
    await state.update_data(hour=hour)
    await state.set_state(Schedule.event_minute)
    await callback.message.edit_text(f"Година {hour:02d}. Хвилини:", reply_markup=_minute_kb())
    await callback.answer()


@router.callback_query(Schedule.event_minute, F.data.startswith("smin:"))
async def minute_chosen(callback: CallbackQuery, state: FSMContext) -> None:
    minute = int(callback.data.split(":")[1])
    data = await state.get_data()
    await state.update_data(time=f"{int(data['hour']):02d}:{minute:02d}")
    await _finalize(callback.message, state)


async def _finalize(target: Message, state: FSMContext) -> None:
    data = await state.get_data()
    weekdays = ",".join(str(i) for i in data["weekdays"]) if data.get("weekdays") else None
    the_time = utils.parse_time(data["time"]) if data.get("time") else None
    rule_id = await recurrence.create_recurrence(
        data["type"],
        data["title"],
        data["freq"],
        weekdays=weekdays,
        month_day=data.get("month_day"),
        month=data.get("month"),
        time=the_time,
    )
    await recurrence.materialize_rule(rule_id)
    rule = await recurrence.get_recurrence(rule_id)
    await state.clear()
    await target.answer(f"✅ Розклад додано:\n{utils.esc(recurrence.describe(rule))}")
