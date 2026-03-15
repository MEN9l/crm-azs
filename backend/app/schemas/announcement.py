from datetime import datetime

from pydantic import BaseModel


class AnnouncementCreate(BaseModel):
    title: str
    content: str


class AnnouncementUpdate(BaseModel):
    title: str | None = None
    content: str | None = None


class AuthorBrief(BaseModel):
    id: int
    full_name: str

    class Config:
        from_attributes = True


class AnnouncementResponse(BaseModel):
    id: int
    title: str
    content: str
    author_id: int
    author: AuthorBrief | None = None
    created_at: datetime

    class Config:
        from_attributes = True
