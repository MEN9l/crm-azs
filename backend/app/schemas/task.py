from datetime import date, datetime

from pydantic import BaseModel

from .user import UserBrief


class TaskBase(BaseModel):
    title: str
    description: str | None = None
    status: str = "backlog"
    priority: str = "normal"
    ticket_id: int | None = None
    assignee_id: int | None = None
    department_id: int | None = None
    due_date: date | None = None


class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    priority: str = "normal"
    ticket_id: int | None = None
    assignee_id: int | None = None
    status: str = "backlog"
    department_id: int | None = None
    due_date: date | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    priority: str | None = None
    assignee_id: int | None = None
    department_id: int | None = None
    due_date: date | None = None


class TaskResponse(TaskBase):
    id: int
    created_at: datetime
    updated_at: datetime
    assignee: UserBrief | None = None

    class Config:
        from_attributes = True


class TaskHistoryResponse(BaseModel):
    id: int
    task_id: int
    user_id: int | None
    field_name: str
    old_value: str | None
    new_value: str | None
    created_at: datetime
    user: UserBrief | None = None

    class Config:
        from_attributes = True
