"""Моделі БД: items та settings (див. TZ.md)."""
from datetime import date as date_, datetime, time as time_

from sqlalchemy import Boolean, Date, DateTime, Integer, Text, Time, func
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


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
