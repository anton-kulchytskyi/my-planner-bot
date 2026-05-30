#!/bin/sh
set -e

echo "Застосовую міграції БД..."
alembic upgrade head

echo "Запускаю бота..."
exec python main.py
