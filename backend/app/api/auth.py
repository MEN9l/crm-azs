from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.email import send_email
from app.core.security import verify_password, create_access_token, create_reset_token, decode_token, hash_password
from app.models import User
from app.schemas import LoginRequest, LoginResponse, UserBrief, UserCreate, UserResponse

from .deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email.strip().lower()).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный email или пароль",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Пользователь деактивирован")
    token = create_access_token(subject=user.id)
    return LoginResponse(
        access_token=token,
        user=UserBrief(id=user.id, full_name=user.full_name, email=user.email, role=user.role),
    )


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return user


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


@router.post("/forgot-password")
def forgot_password(data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email.strip().lower()).first()
    if not user:
        return {"detail": "Если такой email зарегистрирован, на него придёт ссылка для сброса пароля"}
    token = create_reset_token(user.id)
    base_url = (settings.frontend_url or "").rstrip("/")
    reset_link = f"{base_url}/?reset={token}" if base_url else f"/?reset={token}"
    send_email(
        user.email,
        "Сброс пароля — CRM АЗС",
        f"Перейдите по ссылке для сброса пароля (действует 1 час):\n{reset_link}",
    )
    return {"detail": "Если такой email зарегистрирован, на него придёт ссылка для сброса пароля"}


@router.post("/reset-password")
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    payload = decode_token(data.token)
    if not payload or payload.get("type") != "reset":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Недействительная или просроченная ссылка")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Недействительная ссылка")
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")
    user.hashed_password = hash_password(data.new_password)
    db.commit()
    return {"detail": "Пароль успешно изменён"}


# Только для первоначальной настройки: создание первого пользователя (без токена).
# В продакшене закрыть или требовать секретный ключ.
@router.post("/register", response_model=UserResponse)
def register(data: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == data.email.strip().lower()).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email уже занят")
    user = User(
        full_name=data.full_name,
        email=data.email.strip().lower(),
        phone=data.phone,
        hashed_password=hash_password(data.password),
        role=data.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
