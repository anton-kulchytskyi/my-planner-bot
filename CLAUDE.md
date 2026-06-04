# Personal Planner Bot — CLAUDE.md

> Цей файл читається Claude Code при старті кожної сесії.
> Оновлюй після кожного значного кроку або рішення.

---

## Що це за проект

Особистий Telegram-бот-планувальник для одного користувача. Мінімальний інструмент: задачі, події, ранковий briefing. Без бекенду, без веб-інтерфейсу, без ролей.

**ТЗ:** див. `TZ.md` у корені проекту — там повний опис флоу, структури БД, команд і вимог.

---

## Стек

| Частина | Технологія |
|---|---|
| Бот | aiogram 3.x |
| Мова | Python 3.12 |
| БД | PostgreSQL (asyncpg + SQLAlchemy async) |
| Міграції | Alembic |
| Планувальник | APScheduler |
| Деплой | Railway (Dockerfile) |

---

## Структура проекту

```
planner-bot/
├── CLAUDE.md           ← цей файл
├── TZ.md               ← технічне завдання (базовий обсяг; розклад/AI/end_time — поза ним)
├── main.py             ← точка входу: middleware ALLOWED_USER_ID, /start, реєстрація роутерів, scheduler.setup
├── config.py           ← env: BOT_TOKEN, ALLOWED_USER_ID, DATABASE_URL (→asyncpg), ANTHROPIC_API_KEY(опц.)
├── database.py         ← async engine + async_sessionmaker + Base
├── models.py           ← Item, Setting, Recurrence
├── utils.py            ← парсинг/формат дат і часу, human_date, days_ago, esc (HTML)
├── keyboards.py        ← reply-меню (3/2/2) + inline_column(buttons) з абстрактних Button
├── views.py            ← ЧИСТИЙ рендер: today_view/upcoming_view/done_view → View(text, buttons); 🔁 і діапазон часу
├── handlers/
│   ├── __init__.py     ← setup_routers (порядок: фічі → ai catch-all останнім)
│   ├── add.py          ← «Додати» FSM: тип→назва→дата(кнопки)→година→хвилини→тривалість
│   ├── today.py        ← «Сьогодні» (+ callback tdone: відмітка простроченого)
│   ├── done.py         ← «Виконано» (callback done:)
│   ├── upcoming.py     ← «Найближче» (7 днів)
│   ├── schedule.py     ← «🔁 Розклад» FSM: перегляд/створення/видалення правил
│   ├── settings.py     ← «Налаштування»: час briefing (FSM)
│   ├── help.py         ← «Допомога»
│   └── ai.py           ← catch-all вільного тексту → AI; /reset; callback'и підтвердження дій
├── services/
│   ├── storage.py      ← settings (key-value) + типізовані: morning_time()/timezone()/set_morning_time()
│   ├── clock.py        ← єдине джерело локального часу: now()/today()/year() (таймзона з storage)
│   ├── items.py        ← CRUD/запити items (add_item, get_*, mark_done, delete_item, …)
│   ├── recurrence.py   ← правила розкладу: expand + materialize (60 днів) + CRUD + describe
│   ├── conflicts.py    ← детермінна find_conflicts (перетин інтервалів подій, без LLM)
│   ├── scheduler.py    ← APScheduler: briefing(cron) + нагадування(1год до старту + опц. 15хв до кінця) + матеріалізація(cron 00:05) + авточистка(cron 00:10)
│   └── ai.py           ← Claude (Sonnet 4.6): агентний tool-use, історія, AgentReply
├── alembic/versions/   ← 0001 initial · 0002 recurrences · 0003 event_end_time · 0004 notify_end
├── alembic.ini
├── entrypoint.sh       ← alembic upgrade head → python main.py
├── Dockerfile
├── .env.example
└── requirements.txt
```

---

## Середовище розробки

**Python локально не встановлено.** Весь цикл розробки — через Railway:

1. Пишемо код
2. Пушимо в GitHub
3. Railway автоматично деплоїть
4. Перевіряємо в Telegram

Локально нічого не піднімаємо (Python локально — лише Store-заглушка, не запускається). **Міграції застосовуються автоматично** через `entrypoint.sh` (`alembic upgrade head` перед стартом бота) — вручну нічого запускати не треба.

**Тести не пишемо** — перевірка відбувається вручну через реальний бот після деплою. Робочий цикл: пишемо код → коміт → `git push` → Railway авто-деплой → перевіряємо в Telegram. Після кожного кроку — звіт і очікування підтвердження.

---

## Правила розробки

### Архітектура
- Весь код в одному репозиторії, один сервіс на Railway
- БД — Railway PostgreSQL, підключення через `DATABASE_URL` з env
- Бот реагує тільки на `ALLOWED_USER_ID` з `.env` — решта ігнорується мовчки
- Жодних HTTP API, жодного фронту

### Код
- Async скрізь — aiogram 3 і SQLAlchemy async
- FSM через `aiogram.fsm` для багатокрокових флоу (`/add`)
- APScheduler з `AsyncIOScheduler` — не блокує event loop
- Налаштування тільки через `.env` / environment variables, жодних хардкодів
- Логування через стандартний `logging` — INFO рівень для продакшну
- Обробка помилок: `try/except` навколо DB операцій і зовнішніх викликів; при помилці — логуємо, надсилаємо юзеру коротке повідомлення про помилку

### Міграції
- Alembic для всіх змін схеми БД
- Нова фіча зі зміною схеми = нова міграція, не редагувати існуючі
- Накат **автоматичний** через `entrypoint.sh` на кожному деплої (нічого вручну)
- Async `alembic/env.py` (asyncpg); `DATABASE_URL` нормалізується в `config.py`

### Dockerfile
- `python:3.12-slim` base image
- `CMD ["./entrypoint.sh"]` → міграції + `python main.py`
- `.gitattributes` тримає `entrypoint.sh` у LF (щоб не зламався на Linux)

---

## Правила роботи з Claude Code — ОБОВ'ЯЗКОВО

### Перед початком
1. Прочитати `TZ.md` повністю
2. Показати план реалізації
3. Чекати підтвердження перед стартом

### Під час роботи
1. Виконувати **один пункт за раз**
2. Після кожного пункту показати що зроблено і чекати підтвердження
3. Не переходити далі без підтвердження

### Формат після кожного пункту
```
✅ Зроблено: [назва]
Що зроблено: [короткий опис]
Наступний крок: [назва]
Чекаю підтвердження.
```

---

## Environment variables

```env
BOT_TOKEN=
ALLOWED_USER_ID=
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/planner
ANTHROPIC_API_KEY=   # опційно — AI-асистент
```

---

## БД (схема)

- **items**: id, type(task/event), title, date, time, **end_time**, **notify_end**(bool), done, created_at, **recurrence_id**(FK→recurrences, SET NULL)
- **settings**: key, value (`morning_time`=08:00, `timezone`=Europe/Kyiv)
- **recurrences**: id, type, title, time, end_time, **notify_end**(bool), freq(daily/weekly/monthly/yearly), weekdays("0,2,4", Пн=0…Нд=6), month_day, month, start_date, materialized_through, created_at

---

## Поточний статус

**Бот живий на Railway, повністю в робочому стані.** Базовий обсяг (ТЗ) + три великі надбудови:

**Базовий функціонал (Кроки 1–7):** клавіатура-меню; «Додати» (FSM: задача/подія, дати кнопками,
час година→хвилини→**тривалість**); «Сьогодні» (прострочені з ✅, події, задачі); «Найближче» (7 днів);
«Виконано»; «Налаштування» (час briefing); Scheduler (ранковий briefing cron + нагадування за 1 год до події).

**AI-асистент (Sonnet 4.6)** — `services/ai.py`. Вільний текст → агентний tool-use цикл.
Інструменти: `list_items`, `items_on`, `check_conflicts`, `create_item`, `create_recurrence`,
`close_task`, `delete_item`. Створення — автономне зі зведенням; закриття/видалення —
інлайн-підтвердження (дія в `callback_data`). Коротка in-memory історія (10 повідомлень, TTL 30хв) + `/reset`.
Опційний: без `ANTHROPIC_API_KEY` — старий fallback «не розумію».

**Розклад / повторювані** — `services/recurrence.py`. Правила (`recurrences`) матеріалізуються у звичайні
`items` на 60 днів уперед (cron 00:05 + догін при старті). Кнопка «🔁 Розклад» (FSM) і AI-tool `create_recurrence`.
Повторювані позначені 🔁; видалення прибирає правило + майбутні входження + їх нагадування.

**Час закінчення подій + антиконфлікт** — у події є `time`/`end_time` (інтервал). `services/conflicts.py`
(`find_conflicts`) детермінно ловить накладки за перетином інтервалів: у кнопковому «Додати» — попередження
без API; у агента — tool `check_conflicts` (модель не рахує сама).

**Нагадування про закінчення події** — опційний прапорець `notify_end` (events і recurrences). Якщо ввімкнено
й є `end_time` — додаткове нагадування за фікс. `END_REMINDER_MIN`=15 хв до кінця (job `endreminder:{id}` поряд з
`reminder:{id}`). Прапорець доступний у кнопкових флоу «Додати» й «🔁 Розклад» (крок Так/Ні лише коли обрано
тривалість) та через AI (`notify_end` у `create_item`/`create_recurrence`, вмикається лише разом з `end`).
Позначка 🔔 у «Сьогодні»/«Найближче» і в описі правил. Кейс: забрати дитину з тренування.

---

**Авточистка БД** — `items.cleanup_old(cutoff)` + job у scheduler (cron 00:10 + догін при старті).
Видаляє завершене/минуле старше за `RETENTION_DAYS`=14 днів: минулі події та виконані задачі (з датою
в минулому або без дати — за `created_at`). **Невиконані задачі не чіпаються** (борг). Безпечно: матеріалізація
йде лише вперед, тож видалені минулі входження не воскресають. Беклог (задачі без дати) — окрема секція
«📥 Беклог» у «Найближче» і ранковому briefing (`today_view`/`upcoming_view`, `items.get_backlog()`).

---

## Ключові архітектурні рішення (контекст)

- **Глибокі модулі після рефакторингу:** `views.py` — чистий рендер (текст+кнопки, без БД/aiogram);
  `clock.py` — єдине джерело локального часу; `storage.py` — типізовані налаштування (парсинг сховано).
- **Розклад = матеріалізація (варіант B):** правило → реальні рядки items, тож «Сьогодні»/«Найближче»/
  нагадування працюють без змін. Матеріалізуємо лише ВПЕРЕД (не раніше сьогодні) → видалені входження не воскресають.
- **Антиконфлікт детермінний** (не LLM): дешевше + точніше; служить і кнопкам, і агенту.
- **In-memory:** FSM-стан і історія AI губляться при деплої/рестарті — прийнятно для single-user.
- **Без циклів імпорту:** `scheduler` ↔ `recurrence`/`handlers.today` — через lazy-імпорти всередині функцій.

**Можливе наступне:** моніторинг витрат на API (Sonnet); ідеї — редагування записів, гнучкіші нагадування,
повторювані з кінцем дії. Деталі — у memory (`ai-cost-and-conflict-check`).
