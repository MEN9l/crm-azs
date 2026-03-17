from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


user_station_table = Table(
    "user_station",
    Base.metadata,
    Column("user_id", ForeignKey("users.id"), primary_key=True),
    Column("station_id", ForeignKey("stations.id"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    role: Mapped[str] = mapped_column(String(50), default="operator")  # operator, manager, chief, admin
    is_office: Mapped[bool] = mapped_column(Boolean, default=False)  # сотрудник офиса (видит общий чат, может быть добавлен в чаты АЗС)
    position: Mapped[str | None] = mapped_column(String(255), nullable=True)   # должность
    department: Mapped[str | None] = mapped_column(String(255), nullable=True)  # подразделение
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"), nullable=True)
    avatar: Mapped[str | None] = mapped_column(String(512), nullable=True)     # путь к аватарке, напр. avatars/1.jpg
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # для отображения «кто в сети»

    department_ref = relationship("Department")

    stations: Mapped[list["Station"]] = relationship(
        "Station", secondary=user_station_table, back_populates="users"
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Station(Base):
    __tablename__ = "stations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    address: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    users: Mapped[list[User]] = relationship(
        "User", secondary=user_station_table, back_populates="stations"
    )

