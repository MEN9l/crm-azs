from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from pydantic import BaseModel

from app.core.database import get_db
from app.models import Chat, Message, Notification, Station, Task, Ticket, User
from app.models.chat import chat_member_table
from app.schemas import ChatResponse, ChatMemberResponse, MessageCreate, MessageResponse, UserBrief

from .chat_ws import manager as ws_manager
from .deps import get_current_user, require_role

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatAddMemberBody(BaseModel):
    user_id: int


def _user_in_chat_extra(db: Session, chat_id: int, user_id: int) -> bool:
    row = db.execute(
        chat_member_table.select().where(
            chat_member_table.c.chat_id == chat_id,
            chat_member_table.c.user_id == user_id,
        )
    ).first()
    return row is not None


def _user_can_see_chat(db: Session, chat: Chat, user: User) -> bool:
    """Пользователь видит чат: офис — общий; по станциям — чаты своих АЗС; плюс чаты, куда добавлен вручную."""
    if not chat:
        return False
    if _user_in_chat_extra(db, chat.id, user.id):
        return True
    if chat.type == "general":
        return bool(user.is_office)
    if chat.type == "station" and chat.station_id:
        return any(s.id == chat.station_id for s in user.stations)
    # ticket/task/direct — пока считаем доступ по станции или общий
    if chat.station_id:
        return any(s.id == chat.station_id for s in user.stations)
    return bool(user.is_office)


def _chats_visible_to_user(db: Session, user: User):
    """Чаты, которые пользователь имеет право видеть. Admin/chief видят все."""
    all_chats = db.query(Chat).all()
    if user.role in ("admin", "chief"):
        return all_chats
    return [c for c in all_chats if _user_can_see_chat(db, c, user)]


@router.get("/chats", response_model=list[ChatResponse])
def list_chats(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    """Список чатов: офис видит общий; АЗС — свои станции; плюс чаты, куда пользователя добавили."""
    return _chats_visible_to_user(db, user)


def _get_chat_or_404(db: Session, chat_id: int, user: User):
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Чат не найден")
    if not _user_can_see_chat(db, chat, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа к этому чату")
    return chat


@router.get("/chats/{chat_id}/messages", response_model=list[MessageResponse])
def list_messages(
    chat_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    _get_chat_or_404(db, chat_id, user)
    messages = (
        db.query(Message)
        .options(joinedload(Message.sender), joinedload(Message.attachments))
        .filter(Message.chat_id == chat_id)
        .order_by(Message.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    messages.reverse()
    return messages


@router.post("/chats/{chat_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    chat_id: int,
    data: MessageCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    chat = _get_chat_or_404(db, chat_id, user)
    msg = Message(chat_id=chat_id, sender_id=user.id, content=data.content.strip())
    db.add(msg)
    db.commit()
    db.refresh(msg)
    # Уведомить других участников чата (по заявке/задаче — создатель и исполнитель)
    notify_ids = set()
    if chat.ticket_id:
        ticket = db.query(Ticket).filter(Ticket.id == chat.ticket_id).first()
        if ticket:
            if ticket.creator_id and ticket.creator_id != user.id:
                notify_ids.add(ticket.creator_id)
            if ticket.assignee_id and ticket.assignee_id != user.id:
                notify_ids.add(ticket.assignee_id)
    if chat.task_id:
        task = db.query(Task).filter(Task.id == chat.task_id).first()
        if task and task.assignee_id and task.assignee_id != user.id:
            notify_ids.add(task.assignee_id)
    short_content = (data.content.strip()[:60] + "…") if len(data.content.strip()) > 60 else data.content.strip()
    for uid in notify_ids:
        db.add(Notification(user_id=uid, type="chat_message", message=f"Чат: {user.full_name}: {short_content}"))
    if notify_ids:
        db.commit()
    msg = db.query(Message).options(joinedload(Message.sender)).filter(Message.id == msg.id).first()
    # Рассылать новое сообщение всем подписчикам чата по WebSocket (чтобы сообщения появлялись без обновления)
    payload = {
        "id": msg.id,
        "chat_id": msg.chat_id,
        "sender_id": msg.sender_id,
        "content": msg.content,
        "created_at": msg.created_at.isoformat() if msg.created_at else None,
        "sender": {
            "id": user.id,
            "full_name": user.full_name or "",
            "email": user.email or "",
            "role": user.role or "",
        },
    }
    await ws_manager.broadcast(chat_id, payload)
    return msg


def _chat_member_ids(db: Session, chat: Chat) -> list[int]:
    """ID пользователей, которые имеют доступ к чату (базовые по типу + добавленные вручную)."""
    ids = set()
    if chat.type == "general":
        for u in db.query(User).filter(User.is_office == True, User.is_active == True).all():
            ids.add(u.id)
    if chat.station_id:
        st = db.query(Station).filter(Station.id == chat.station_id).first()
        if st:
            for u in st.users:
                if u.is_active:
                    ids.add(u.id)
    for u in chat.extra_members:
        if u.is_active:
            ids.add(u.id)
    return list(ids)


@router.get("/chats/{chat_id}/members", response_model=list[ChatMemberResponse])
def list_chat_members(
    chat_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    """Участники чата (кто видит чат): по типу чата + добавленные вручную. is_extra=True — добавлен вручную, можно убрать."""
    chat = _get_chat_or_404(db, chat_id, user)
    member_ids = _chat_member_ids(db, chat)
    if not member_ids:
        return []
    extra_ids = {row.user_id for row in db.execute(chat_member_table.select().where(chat_member_table.c.chat_id == chat_id)).fetchall()}
    users = db.query(User).filter(User.id.in_(member_ids), User.is_active == True).order_by(User.full_name).all()
    return [
        ChatMemberResponse(
            user=UserBrief(id=u.id, full_name=u.full_name, email=u.email, role=u.role, is_office=getattr(u, "is_office", False), position=getattr(u, "position", None), department=getattr(u, "department", None)),
            is_extra=(u.id in extra_ids),
        )
        for u in users
    ]


@router.post("/chats/{chat_id}/members", status_code=status.HTTP_204_NO_CONTENT)
def add_chat_member(
    chat_id: int,
    body: ChatAddMemberBody,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Добавить участника в чат (напр. сотрудника офиса в чат АЗС). Только admin/chief или с доступом к чату."""
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Чат не найден")
    if not _user_can_see_chat(db, chat, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа к этому чату")
    if current_user.role not in ("admin", "chief"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Только администратор или руководитель может добавлять участников")
    target = db.query(User).filter(User.id == body.user_id, User.is_active == True).first()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")
    if _user_in_chat_extra(db, chat_id, target.id):
        return
    db.execute(chat_member_table.insert().values(chat_id=chat_id, user_id=target.id))
    db.commit()


@router.delete("/chats/{chat_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_chat_member(
    chat_id: int,
    user_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Убрать участника из чата (только из добавленных вручную)."""
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Чат не найден")
    if not _user_can_see_chat(db, chat, current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нет доступа к этому чату")
    if current_user.role not in ("admin", "chief"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Только администратор или руководитель может удалять участников")
    db.execute(chat_member_table.delete().where(chat_member_table.c.chat_id == chat_id, chat_member_table.c.user_id == user_id))
    db.commit()
