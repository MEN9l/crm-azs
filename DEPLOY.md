# Подготовка backend и первый запуск

## 1. Переменные окружения (Docker)

В корне проекта (рядом с `docker-compose.yml`) создай файл `.env`:

```env
POSTGRES_USER=crm_user
POSTGRES_PASSWORD=crm_pass
POSTGRES_DB=crm_azs
POSTGRES_HOST=db
POSTGRES_PORT=5432

SECRET_KEY=замени_на_длинный_случайный_ключ
ACCESS_TOKEN_EXPIRE_MINUTES=480
```

В `docker-compose.yml` у сервиса `backend` должны быть переданы переменные для БД (например `POSTGRES_HOST=db`), чтобы приложение подключалось к контейнеру PostgreSQL.

## 2. Миграции (создание таблиц в БД)

После первого запуска контейнеров выполни миграции **внутри контейнера backend**:

```bash
docker compose exec backend alembic upgrade head
```

Если Alembic лежит в `backend/` и при сборке образ копирует только `app/`, то либо добавь в Dockerfile копирование `alembic.ini` и папки `alembic/`, либо запускай миграции с хоста (при этом БД должна быть доступна по localhost, например через проброс порта 5432).

**Вариант с хоста** (если PostgreSQL доступен на localhost:5432):

```bash
cd backend
# В .env на хосте укажи POSTGRES_HOST=localhost и те же POSTGRES_USER/PASSWORD/DB
pip install -r requirements.txt
alembic upgrade head
```

**Вариант через контейнер** (нужно копировать alembic в образ):

В `backend/Dockerfile` добавь:

```dockerfile
COPY alembic.ini .
COPY alembic ./alembic
```

И в `backend/docker-compose` для backend задай рабочую директорию и команду так, чтобы при `alembic upgrade head` находились `alembic.ini` и `alembic/`. Затем:

```bash
docker compose run --rm backend alembic upgrade head
```

## 3. Первый пользователь и тестовые данные

После успешного выполнения миграций создай первого пользователя и тестовые АЗС/чаты:

**С хоста** (при наличии доступа к БД):

```bash
cd backend
PYTHONPATH=. python scripts/seed_data.py
```

**Через контейнер**:

```bash
docker compose exec backend python -m scripts.seed_data
```

Скрипт создаст:
- пользователя **admin@azs.local** / **admin123** (роль admin);
- две АЗС (AZS-01, AZS-02);
- общий чат «Общий офис»;
- несколько тестовых заявок и задач.

## 4. Вход на сайт

Открой в браузере адрес, где развёрнут фронт (тот же хост, что отдаёт nginx).  
Страница логина запрашивает `POST /api/auth/login`.  
Войди: **admin@azs.local** / **admin123**.

## 5. Если фронт отдаётся с того же домена

Nginx проксирует `/api/` на backend. В `index.html` запросы идут на `/api/auth/login`, `/api/tickets` и т.д. — префикс `/api` отрезается nginx, бэкенд слушает маршруты без префикса (`/auth/login`, `/tickets`, …). Если раздаёшь API с другого пути (например `/backend/`), нужно либо поменять `location` в nginx, либо в `index.html` заменить базовый путь API (например на `/backend`).

## 6. Бэкап БД

Скрипт `scripts/backup_db.sh` создаёт дамп PostgreSQL в папку `backups/`:

```bash
cd /opt/crm-azs
bash scripts/backup_db.sh
```

Рекомендуется настроить cron (раз в день):

```bash
0 3 * * * cd /opt/crm-azs && bash scripts/backup_db.sh
```

Хранить копии лучше не только на сервере, а копировать в облако или на другой диск.

## 7. HTTPS (Let's Encrypt)

Если есть домен, привязанный к IP сервера:

```bash
sudo apt install -y certbot
sudo certbot certonly --standalone -d ваш-домен.ru
```

После получения сертификата добавь в nginx конфиг блок `listen 443 ssl` и пути к сертификатам (обычно `/etc/letsencrypt/live/ваш-домен.ru/`). Редирект с HTTP на HTTPS:

```nginx
server { listen 80; server_name ваш-домен.ru; return 301 https://$server_name$request_uri; }
server { listen 443 ssl; server_name ваш-домен.ru; ssl_certificate ...; ssl_certificate_key ...; ... }
```

Перезапуск nginx: `docker compose restart nginx`.

## 8. Резюме команд на сервере

```bash
cd /opt/crm-azs
docker compose up -d
docker compose exec backend alembic upgrade head
docker compose exec backend python -m scripts.seed_data
# Открыть в браузере http(s)://твой-домен и войти admin@azs.local / admin123
```

## 9. Ошибка 403 (Forbidden)

Если после входа или при действиях в интерфейсе приходит **403**:

- **«Пользователь деактивирован»** — в БД у пользователя выставлено `is_active = false`. Включите пользователя:
  ```bash
  docker compose exec db psql -U crm_user -d crm_azs -c "UPDATE users SET is_active = true WHERE email = 'admin@azs.local';"
  ```
  Подставьте нужный `email`, если ошибка у другого пользователя.

- **«Недостаточно прав»** — запрошенное действие разрешено только ролям admin/chief (например, отчёты, создание АЗС). Войдите под учётной записью с ролью admin или chief.

## 10. Автоматизация обновлений (Git)

Чтобы не закидывать файлы вручную, храните проект в **Git** и на сервере обновляйтесь одной командой.

### Однократная настройка

**На компьютере (где правите код):**

1. Инициализируйте репозиторий и залейте на GitHub / GitLab / свой сервер:
   ```bash
   cd "путь/к/проекту/crm-azs"
   git init
   git add .
   git commit -m "Initial"
   git remote add origin https://github.com/ВАШ_ЛОГИН/crm-azs.git
   git push -u origin main
   ```
2. Файл `.env` и папка `data/` в `.gitignore` — в репозиторий не попадут (секреты и БД остаются только на сервере).

**На сервере (один раз):**

1. Установите Git, если ещё нет: `apt install -y git`
2. Клонируйте проект (вместо копирования папки):
   ```bash
   cd /opt
   git clone https://github.com/ВАШ_ЛОГИН/crm-azs.git
   cd crm-azs
   ```
3. Создайте на сервере файл `.env` с паролями (как в разделе 1). Папку `data/` при первом запуске создаст Docker.
4. Первый запуск: `docker compose up -d`, затем миграции и seed (как в разделе 8).

### Обновление без ручной загрузки файлов

**На компьютере:** после изменений делаете только:

```bash
git add .
git commit -m "Описание изменений"
git push
```

**На сервере:** заходите по SSH и запускаете один скрипт:

```bash
cd /opt/crm-azs
bash scripts/deploy.sh
```

Скрипт `scripts/deploy.sh` делает: `git pull` → сборка backend → `docker compose up -d` → миграции → перезапуск backend. Фронт (nginx отдаёт папку `frontend/`) и конфиг nginx обновляются из репозитория при `git pull`.

### Опционально: авто-деплой по push (webhook)

Если хотите, чтобы сервер сам подтягивал код после каждого `git push`:

- **GitHub/GitLab:** настройте Webhook, который дергает URL на вашем сервере; на сервере — маленький сервис (скрипт по HTTP), который по запросу выполняет `cd /opt/crm-azs && bash scripts/deploy.sh`. Либо используйте GitHub Actions: по push в `main` выполнять SSH на сервер и там запускать `deploy.sh`.
- Без вебхуков достаточно по необходимости заходить по SSH и запускать `bash scripts/deploy.sh` после `git push`.
