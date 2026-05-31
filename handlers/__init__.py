"""Реєстрація всіх роутерів у диспетчері."""
from aiogram import Dispatcher

from . import add, done, help, schedule, settings, today, upcoming


def setup_routers(dp: Dispatcher) -> None:
    dp.include_router(today.router)
    dp.include_router(add.router)
    dp.include_router(done.router)
    dp.include_router(upcoming.router)
    dp.include_router(schedule.router)
    dp.include_router(settings.router)
    dp.include_router(help.router)
