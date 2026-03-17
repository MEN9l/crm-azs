from datetime import datetime

from pydantic import BaseModel


class DepartmentBase(BaseModel):
    name: str
    parent_id: int | None = None
    pos_x: int | None = None
    pos_y: int | None = None


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentUpdate(BaseModel):
    name: str | None = None
    parent_id: int | None = None
    pos_x: int | None = None
    pos_y: int | None = None


class DepartmentResponse(DepartmentBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

