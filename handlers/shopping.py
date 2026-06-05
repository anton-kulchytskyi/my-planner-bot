"""Хендлер «🛒 Покупки» — окремий список покупок.

Тап по позиції = видалити («купив»). Додавання — FSM, можна кілька
позицій за раз (через кому або з нового рядка). В історії не зберігається.
"""
import keyboards
import views
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from services import shopping

router = Router()


class Shopping(StatesGroup):
    adding = State()


async def _build() -> views.View:
    return views.shopping_view(await shopping.get_all())


@router.message(Command("shopping"))
@router.message(F.text == keyboards.BTN_SHOPPING)
async def show(message: Message) -> None:
    view = await _build()
    await message.answer(view.text, reply_markup=keyboards.inline_column(view.buttons))


@router.callback_query(F.data == "shop_add")
async def ask_add(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(Shopping.adding)
    await callback.message.answer(
        "Що додати? Можна кілька — через кому або з нового рядка."
    )
    await callback.answer()


@router.message(Shopping.adding)
async def do_add(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").replace("\n", ",")
    count = await shopping.add_items(raw.split(","))
    await state.clear()
    if count == 0:
        await message.answer("Нічого не додав — порожній текст.")
        return
    view = await _build()
    await message.answer(
        f"✅ Додав ({count})", reply_markup=keyboards.inline_column(view.buttons)
    )


@router.callback_query(F.data.startswith("shop_del:"))
async def delete_one(callback: CallbackQuery) -> None:
    item_id = int(callback.data.split(":")[1])
    await shopping.delete_item(item_id)
    view = await _build()
    await callback.message.edit_text(
        view.text, reply_markup=keyboards.inline_column(view.buttons)
    )
    await callback.answer("🛒 Прибрав")


@router.callback_query(F.data == "shop_clear")
async def clear(callback: CallbackQuery) -> None:
    await shopping.clear_all()
    view = await _build()
    await callback.message.edit_text(
        view.text, reply_markup=keyboards.inline_column(view.buttons)
    )
    await callback.answer("🗑 Очищено")
