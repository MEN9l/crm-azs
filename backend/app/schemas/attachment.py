from datetime import datetime

from pydantic import BaseModel


class AttachmentResponse(BaseModel):
    id: int
    ticket_id: int | None
    message_id: int | None
    original_name: str
    created_at: datetime

    class Config:
        from_attributes = True
