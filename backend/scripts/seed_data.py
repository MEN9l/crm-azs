"""
Скрипт создания первого пользователя и тестовых данных.
Запуск из корня backend: python -m scripts.seed_data
Или: cd backend && PYTHONPATH=. python scripts/seed_data.py
"""
import sys
from pathlib import Path

# Добавляем корень backend в path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import User, Station, Ticket, Task, Chat, Message

# Первый пользователь (админ)
ADMIN_EMAIL = "admin@azs.local"
ADMIN_PASSWORD = "admin123"
ADMIN_NAME = "Администратор"

# Пользователь АЗС (для проверки чата и ролей)
OPERATOR_EMAIL = "operator@azs.local"
OPERATOR_PASSWORD = "operator123"
OPERATOR_NAME = "Оператор АЗС"

# Тестовые АЗС
STATIONS = [
    {"name": "АЗС-1 Центральная", "code": "AZS-01", "address": "ул. Центральная, 1"},
    {"name": "АЗС-2 Северная", "code": "AZS-02", "address": "ул. Северная, 5"},
]



def seed(db: Session) -> None:
    admin_exists = db.query(User).filter(User.email == ADMIN_EMAIL).first()
    if admin_exists:
        print(f"Пользователь {ADMIN_EMAIL} уже есть. Пропуск создания админа и данных.")
        # Всё равно добавляем оператора, если его нет
        first_station = db.query(Station).first()
        general_chat = db.query(Chat).filter(Chat.type == "general").first()
        if first_station and general_chat:
            add_operator(db, first_station.id, general_chat.id, admin_exists.id)
        else:
            print("Нет АЗС или общего чата — сначала запустите сид без существующего админа.")
        return

    admin = User(
        full_name=ADMIN_NAME,
        email=ADMIN_EMAIL,
        hashed_password=hash_password(ADMIN_PASSWORD),
        role="admin",
        is_superuser=True,
        is_active=True,
        is_office=True,
    )
    db.add(admin)
    db.flush()

    stations = []
    for s in STATIONS:
        st = Station(name=s["name"], code=s["code"], address=s["address"])
        db.add(st)
        db.flush()
        stations.append(st)
        admin.stations.append(st)

    # Общего чата больше нет — только чаты по АЗС и групповые/личные

    for st in stations:
        station_chat = Chat(type="station", name=st.name, station_id=st.id)
        db.add(station_chat)

    # Пару тестовых заявок и задач
    t1 = Ticket(
        title="Не работает колонка №3",
        description="Клиент сообщил о сбое.",
        status="new",
        priority="high",
        station_id=stations[0].id,
        creator_id=admin.id,
    )
    db.add(t1)
    db.flush()
    t2 = Ticket(
        title="Закончилась бумага для чеков",
        status="in_progress",
        station_id=stations[1].id,
        creator_id=admin.id,
    )
    db.add(t2)

    task1 = Task(title="Проверить уровень топлива", status="backlog", priority="normal")
    task2 = Task(title="Вызвать сервисников", status="in_progress", priority="high")
    db.add(task1)
    db.add(task2)

    db.commit()
    print(f"Создан пользователь: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
    print("Созданы АЗС:", [s.code for s in stations])
    print("Созданы чаты по АЗС и тестовые заявки/задачи.")

    # Пользователь АЗС для проверки чата
    add_operator(db, stations[0].id, admin.id)


def add_operator(db: Session, station_id: int, admin_id: int) -> None:
    """Создаёт пользователя-оператора АЗС, если его ещё нет."""
    if db.query(User).filter(User.email == OPERATOR_EMAIL).first():
        print(f"Пользователь {OPERATOR_EMAIL} уже есть. Пропуск.")
        return
    station = db.query(Station).filter(Station.id == station_id).first()
    if not station:
        return
    operator = User(
        full_name=OPERATOR_NAME,
        email=OPERATOR_EMAIL,
        hashed_password=hash_password(OPERATOR_PASSWORD),
        role="operator",
        is_active=True,
    )
    db.add(operator)
    db.flush()
    operator.stations.append(station)
    db.commit()
    print(f"Создан пользователь АЗС: {OPERATOR_EMAIL} / {OPERATOR_PASSWORD}")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()
