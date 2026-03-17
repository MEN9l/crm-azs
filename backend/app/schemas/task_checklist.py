from datetime import datetime

from pydantic import BaseModel, Field

from .user import UserBrief


class TaskChecklistItemCreate(BaseModel):
    station_name: str = Field(..., min_length=1, max_length=255)


class TaskChecklistBulkCreate(BaseModel):
    stations: list[str] = Field(default_factory=list)


class TaskChecklistItemUpdate(BaseModel):
    is_done: bool


class TaskChecklistItemResponse(BaseModel):
    id: int
    task_id: int
    station_name: str
    is_done: bool
    done_by_id: int | None = None
    done_at: datetime | None = None
    created_at: datetime
    done_by: UserBrief | None = None

    class Config:
        from_attributes = True

