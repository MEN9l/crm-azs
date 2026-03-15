from datetime import datetime

from pydantic import BaseModel

from .attachment import AttachmentResponse
from .user import UserBrief


class MessageCreate(BaseModel):
    content: str


class MessageResponse(BaseModel):
    id: int
    chat_id: int
    sender_id: int
    content: str
    created_at: datetime
    sender: UserBrief | None = None
    attachments: list[AttachmentResponse] = []

    class Config:
        from_attributes = True


class ChatResponse(BaseModel):
    id: int
    type: str
    name: str | None
    station_id: int | None
    ticket_id: int | None
    task_id: int | None

    class Config:
        from_attributes = True
