"""
WebSocket-чат: подключения по chat_id, рассылка новых сообщений.
"""
import json
import asyncio
from collections import defaultdict
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from sqlalchemy.orm import joinedload

from app.core.database import SessionLocal
from app.core.security import decode_token
from app.models import User, Chat, Message
from app.models.chat import chat_member_table


class ConnectionManager:
    def __init__(self):
        self._by_chat: dict[int, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, chat_id: int) -> None:
        await websocket.accept()
        async with self._lock:
            self._by_chat[chat_id].add(websocket)

    def disconnect(self, websocket: WebSocket, chat_id: int) -> None:
        self._by_chat[chat_id].discard(websocket)
        if not self._by_chat[chat_id]:
            del self._by_chat[chat_id]

    async def broadcast(self, chat_id: int, payload: dict[str, Any]) -> None:
        async with self._lock:
            sockets = list(self._by_chat.get(chat_id, []))
        for ws in sockets:
            try:
                await ws.send_text(json.dumps(payload, default=str))
            except Exception:
                pass


manager = ConnectionManager()


def get_user_from_token(token: str | None) -> User | None:
    if not token:
        return None
    payload = decode_token(token)
    if not payload or "sub" not in payload:
        return None
    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError):
        return None
    db = SessionLocal()
    try:
        return db.query(User).filter(User.id == user_id, User.is_active == True).first()
    finally:
        db.close()


def _user_can_see_chat_ws(db, chat: Chat, user: User) -> bool:
    if user.role in ("admin", "chief"):
        return True
    row = db.execute(
        chat_member_table.select().where(
            chat_member_table.c.chat_id == chat.id,
            chat_member_table.c.user_id == user.id,
        )
    ).first()
    if row:
        return True
    if chat.type == "general":
        return bool(user.is_office)
    if chat.station_id:
        return any(s.id == chat.station_id for s in user.stations)
    return bool(user.is_office)


async def handle_ws_chat(websocket: WebSocket, chat_id: int, token: str | None) -> None:
    user = get_user_from_token(token)
    if not user:
        await websocket.close(code=4001)
        return
    db = SessionLocal()
    try:
        user = db.query(User).options(joinedload(User.stations)).filter(User.id == user.id).first()
        chat = db.query(Chat).options(joinedload(Chat.extra_members)).filter(Chat.id == chat_id).first()
        if not chat:
            await websocket.close(code=4004)
            return
        if not _user_can_see_chat_ws(db, chat, user):
            await websocket.close(code=4003)
            return
    finally:
        db.close()

    await manager.connect(websocket, chat_id)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                obj = json.loads(data)
                content = (obj.get("content") or "").strip()
            except (json.JSONDecodeError, TypeError):
                continue
            if not content:
                continue

            db = SessionLocal()
            try:
                msg = Message(chat_id=chat_id, sender_id=user.id, content=content[:5000])
                db.add(msg)
                db.commit()
                db.refresh(msg)
                payload = {
                    "id": msg.id,
                    "chat_id": msg.chat_id,
                    "sender_id": msg.sender_id,
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat() if msg.created_at else None,
                    "sender": {"id": user.id, "full_name": user.full_name, "email": user.email, "role": user.role},
                }
            finally:
                db.close()

            await manager.broadcast(chat_id, payload)
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket, chat_id)
