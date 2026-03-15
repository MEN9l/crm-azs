# Backend CRM АЗС

Этот backend реализован на стеке **FastAPI + SQLAlchemy + PostgreSQL**.

## Используемый стек

- **Web‑framework**: FastAPI
- **ORM/доступ к данным**: SQLAlchemy 2.x (Declarative, AsyncSession)
- **База данных**: PostgreSQL (драйверы `asyncpg` и `psycopg2-binary`)
- **Миграции схемы БД**: Alembic
- **Запуск приложения**: Uvicorn

Выбор FastAPI + SQLAlchemy + PostgreSQL является зафиксированным целевым стеком для всего backend‑сервиса CRM.

## Базовая структура каталогов

Планируемая структура каталогов backend (MVP):

```text
backend/
  pyproject.toml
  README.md
  app/
    main.py
    core/
      config.py
      database.py
      security.py
    models/
      __init__.py
    schemas/
      __init__.py
    api/
      __init__.py
      v1/
        __init__.py
    services/
      __init__.py
    repositories/
      __init__.py
```

- `app/main.py` — точка входа FastAPI, подключение роутеров и middleware.
- `app/core/` — базовая инфраструктура: конфигурация, подключение к БД, безопасность.
- `app/models/` — ORM‑модели SQLAlchemy.
- `app/schemas/` — Pydantic‑схемы запросов/ответов.
- `app/api/` — маршруты HTTP/WS (v1, v2 и т.д.).
- `app/services/` — бизнес‑логика.
- `app/repositories/` — слой доступа к данным (репозитории поверх ORM).

На следующих этапах сюда будут добавлены конкретные модели (`User`, `Station`, `Ticket`, `Task` и др.), роутеры и бизнес‑логика.

