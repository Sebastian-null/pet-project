# Briefs — магазин белья + CRM

Монорепозиторий с независимой витриной на Next.js и Python-бэкендом. Витрина и CRM обращаются только к REST API; PostgreSQL не доступен фронтендам напрямую.

## Стек

- `storefront/` — Next.js (App Router), TypeScript, SSR-каталог.
- `backend/` — FastAPI, SQLAlchemy 2, Alembic, JWT, Jinja2 + HTMX для CRM.
- `postgres` — собственная БД в Docker volume.

## Быстрый старт

```bash
cp .env.example .env
docker compose up --build
```

После старта:

- витрина: http://localhost:3000
- API / Swagger: http://localhost:8000/docs
- CRM: http://localhost:8000/admin/login

Демо-учётная запись CRM: `admin@briefs.local` / `change-me-now`.

## Что уже покрывает MVP

- каталог `Product → Variant → SKU`, цвета, размеры, остатки;
- оформление заказа с атомарным резервированием склада;
- роли `admin` и `manager`, JWT для API;
- CRM с товарами, заказами, клиентами и краткой аналитикой;
- Alembic-миграция и seed-данные.

## Дальше по плану

1. Подключить оплату (LiqPay/Fondy) через отдельный payment adapter и webhook.
2. Вынести email/уведомления в Celery + Redis после появления реального провайдера.
3. Добавить изображения в S3-совместимое хранилище, поиск/фильтры и тесты API.
