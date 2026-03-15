"""Список пользователей и админка (для admin/chief)."""
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, status, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.email import send_email
from app.core.security import create_reset_token
from app.models import Station, User
from app.models.attachment import get_uploads_dir
from app.schemas import UserBrief, UserResponse, UserUpdate, ProfileUpdate

from .deps import get_current_user, require_role

router = APIRouter(prefix="/users", tags=["users"])

AVATAR_MAX_SIZE = 3 * 1024 * 1024  # 3 MB
AVATAR_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


@router.get("/me", response_model=UserResponse)
def get_my_profile(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Профиль текущего пользователя."""
    db.refresh(current_user)
    return current_user


@router.patch("/me", response_model=UserResponse)
def update_my_profile(
    data: ProfileUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Обновить свой профиль (имя, телефон, должность, подразделение)."""
    updates = data.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(current_user, key, value)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/me/avatar", response_model=UserResponse)
def upload_my_avatar(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    file: UploadFile = File(...),
):
    """Загрузить свою аватарку (jpg, png, gif, webp; макс. 3 МБ)."""
    ext = Path(file.filename or "").suffix.lower()
    if ext not in AVATAR_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Только изображения: jpg, png, gif, webp")
    content = file.file.read()
    if len(content) > AVATAR_MAX_SIZE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Файл слишком большой (макс. 3 МБ)")
    uploads = get_uploads_dir()
    avatars_dir = uploads / "avatars"
    avatars_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{current_user.id}{ext}"
    (avatars_dir / stored_name).write_bytes(content)
    current_user.avatar = f"avatars/{stored_name}"
    db.commit()
    db.refresh(current_user)
    return current_user


@router.get("/me/avatar")
def get_my_avatar(
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Отдать файл аватарки текущего пользователя."""
    if not current_user.avatar:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Аватар не задан")
    path = get_uploads_dir() / current_user.avatar
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Файл не найден")
    return FileResponse(path, media_type="image/jpeg")


@router.get("/{user_id}/avatar")
def get_user_avatar(
    user_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Отдать аватарку пользователя (для отображения в интерфейсе)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.avatar:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Аватар не найден")
    path = get_uploads_dir() / user.avatar
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Файл не найден")
    return FileResponse(path, media_type="image/jpeg")


def _user_to_brief(u: User) -> UserBrief:
    return UserBrief(
        id=u.id,
        full_name=u.full_name,
        email=u.email,
        role=u.role,
        is_office=getattr(u, "is_office", False),
        position=getattr(u, "position", None),
        department=getattr(u, "department", None),
    )


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
