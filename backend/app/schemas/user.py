from datetime import datetime

from pydantic import BaseModel


class UserBase(BaseModel):
    full_name: str
    email: str
    phone: str | None = None
    role: str = "operator"
    is_office: bool = False
    position: str | None = None
    department: str | None = None


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None
    role: str | None = None
    is_active: bool | None = None
    is_office: bool | None = None
    position: str | None = None
    department: str | None = None


class ProfileUpdate(BaseModel):
    """Обновление своего профиля (без роли и email)."""
    full_name: str | None = None
    phone: str | None = None
    position: str | None = None
    department: str | None = None


class UserResponse(UserBase):
    id: int
    is_active: bool
    is_superuser: bool
    created_at: datetime
    avatar: str | None = None

    class Config:
        from_attributes = True


class UserBrief(BaseModel):
    id: int
    full_name: str
    email: str
    role: str
    is_office: bool = False
    position: str | None = None
    department: str | None = None

    class Config:
        from_attributes = True
