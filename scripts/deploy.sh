#!/bin/bash
# Обновление CRM на сервере: git pull + пересборка + миграции + перезапуск.
# Запускать из корня проекта на сервере: bash scripts/deploy.sh

set -e
cd "$(dirname "$0")/.."

echo "=== Git pull ==="
git pull

echo "=== Сборка backend ==="
docker compose build backend

echo "=== Поднятие контейнеров ==="
docker compose up -d

echo "=== Миграции БД ==="
docker compose exec -T backend alembic upgrade head

echo "=== Перезапуск backend (применить новый образ) ==="
docker compose up -d --force-recreate backend

echo "=== Готово ==="
