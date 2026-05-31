"""Моделі БД: items, settings, recurrences (див. TZ.md)."""
from datetime import date as date_, datetime, time as time_

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Text, Time, func
from sqlalchemy.orm import Mapped, mapped_column

from database import Base


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[str] = mapped_column(Text, nullable=False)  # 'task' | 'event'
    title: Mapped[str] = mapped_column(Text, nullable=False)
    date: Mapped[date_ | None] = mapped_column(Date, nullable=True)
    time: Mapped[time_ | None] = mapped_column(Time, nullable=True)
    done: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=func.false())
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # Якщо рядок згенеровано з правила розкладу — посилання на нього.
    recurrence_id: Mapped[int | None] = mapped_column(
        ForeignKey("recurrences.id", ondelete="SET NULL"), nullable=True
    )


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)


class Recurrence(Base):
    """Правило повторюваного запису (розклад).

    freq:
      • daily   — щодня
      • weekly  — у дні тижня з `weekdays` (Пн=0 … Нд=6, через кому: "0,2,4")
      • monthly — щомісяця `month_day`-го числа
      • yearly  — щороку `month`/`month_day`
    """
    __tablename__ = "recurrences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[str] = mapped_column(Text, nullable=False)  # 'task' | 'event'
    title: Mapped[str] = mapped_column(Text, nullable=False)
    time: Mapped[time_ | None] = mapped_column(Time, nullable=True)

    freq: Mapped[str] = mapped_column(Text, nullable=False)
    weekdays: Mapped[str | None] = mapped_column(Text, nullable=True)   # weekly: "0,2,4"
    month_day: Mapped[int | None] = mapped_column(Integer, nullable=True)  # monthly/yearly
    month: Mapped[int | None] = mapped_column(Integer, nullable=True)      # yearly

    start_date: Mapped[date_] = mapped_column(Date, nullable=False)
    materialized_through: Mapped[date_ | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
