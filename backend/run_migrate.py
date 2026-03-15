#!/usr/bin/env python3
"""
Запуск миграций Alembic без команды alembic в PATH.
Из папки backend: python3 run_migrate.py
"""
import os
import sys

# Запуск из каталога backend (где лежит alembic.ini)
backend_dir = os.path.dirname(os.path.abspath(__file__))
if os.getcwd() != backend_dir:
    os.chdir(backend_dir)
    sys.path.insert(0, backend_dir)

def main():
    from alembic.config import Config
    from alembic import command

    alembic_cfg = Config(os.path.join(backend_dir, "alembic.ini"))
    command.upgrade(alembic_cfg, "head")
    print("Миграции применены: upgrade head")

if __name__ == "__main__":
    main()
