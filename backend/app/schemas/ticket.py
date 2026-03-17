from datetime import date, datetime

from pydantic import BaseModel

from .user import UserBrief
from .station import StationResponse


class TicketBase(BaseModel):
    title: str
    description: str | None = None
    status: str = "new"
    priority: str = "normal"
    type: str = "general"
    tags: str | None = None
    station_id: int | None = None
    assignee_id: int | None = None
    department_id: int | None = None
    due_date: date | None = None


class TicketCreate(BaseModel):
    title: str
    description: str | None = None
    priority: str = "normal"
    type: str = "general"
    station_id: int | None = None
    department_id: int | None = None
    assignee_id: int | None = None
    due_date: date | None = None
    tags: str | None = None


class TicketUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None
    assignee_id: int | None = None
    department_id: int | None = None
    due_date: date | None = None
    tags: str | None = None


class TicketResponse(TicketBase):
    id: int
    creator_id: int | None
    created_at: datetime
    updated_at: datetime
    station: StationResponse | None = None
    creator: UserBrief | None = None
    assignee: UserBrief | None = None

    class Config:
        from_attributes = True


class TicketCommentCreate(BaseModel):
    content: str


class TicketCommentResponse(BaseModel):
    id: int
    ticket_id: int
    user_id: int
    content: str
    created_at: datetime
    user: UserBrief | None = None

    class Config:
        from_attributes = True


class TicketHistoryResponse(BaseModel):
    id: int
    ticket_id: int
    user_id: int | None
    field_name: str
    old_value: str | None
    new_value: str | None
    created_at: datetime
    user: UserBrief | None = None

    class Config:
        from_attributes = True
