"""Список пользователей и админка (для admin/chief)."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.email import send_email
from app.core.security import create_reset_token
from app.models import Station, User
from app.schemas import UserBrief, UserResponse, UserUpdate

from .deps import get_current_user, require_role

router = APIRouter(prefix="/users", tags=["users"])


def _user_to_brief(u: User) -> UserBrief:
    return UserBrief(id=u.id, full_name=u.full_name, email=u.email, role=u.role)


@router.get("", response_model=list[UserBrief])
def list_users(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    if user.role in ("admin", "chief"):
        return db.query(User).filter(User.is_active == True).order_by(User.full_name).all()
    station_ids = [s.id for s in user.stations]
    if not station_ids:
        return [_user_to_brief(user)]
    try:
        q = (
            db.query(User)
            .filter(User.is_active == True)
            .filter(User.stations.any(Station.id.in_(station_ids)))
            .order_by(User.full_name)
        )
        return q.all()
    except Exception:
        return [_user_to_brief(user)]


@router.get("/admin", response_model=list[UserResponse])
def list_users_admin(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    """Полный список пользователей для админки (admin/chief)."""
    require_role(user, ["admin", "chief"])
    return db.query(User).order_by(User.full_name).all()


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    data: UserUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Обновить роль, активность, имя, телефон (только admin/chief)."""
    require_role(current_user, ["admin", "chief"])
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")
    updates = data.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(target, key, value)
    db.commit()
    db.refresh(target)
    return target


@router.post("/{user_id}/send-reset-link")
def send_user_reset_link(
    user_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Отправить пользователю ссылку для сброса пароля (только admin/chief)."""
    require_role(current_user, ["admin", "chief"])
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")
    token = create_reset_token(target.id)
    base_url = (settings.frontend_url or "").rstrip("/")
    reset_link = f"{base_url}/?reset={token}" if base_url else f"/?reset={token}"
    send_email(
        target.email,
        "Сброс пароля — CRM АЗС",
        f"Вам отправлена ссылка для сброса пароля (действует 1 час):\n{reset_link}",
    )
    return {"detail": "Ссылка для сброса пароля отправлена на email пользователя"}
