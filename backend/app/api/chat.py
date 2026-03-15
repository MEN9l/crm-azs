from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.models import Chat, Message, Notification, Task, Ticket, User
from app.schemas import ChatResponse, MessageCreate, MessageResponse

from .chat_ws import manager as ws_manager
from .deps import get_current_user

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/chats", response_model=list[ChatResponse])
def list_chats(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    # Пока возвращаем все чаты; потом фильтр по правам
    return db.query(Chat).all()


@router.get("/chats/{chat_id}/messages", response_model=list[MessageResponse])
def list_messages(
    chat_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Чат не найден")
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
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Чат не найден")
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
