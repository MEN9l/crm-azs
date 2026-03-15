from datetime import datetime

from pydantic import BaseModel


class AnnouncementCreate(BaseModel):
    title: str
    content: str
    is_pinned: bool = False
    is_important: bool = False
    tag: str | None = None


class AnnouncementUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    is_pinned: bool | None = None
    is_important: bool | None = None
    tag: str | None = None


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
    is_pinned: bool = False
    is_important: bool = False
    tag: str | None = None

    class Config:
        from_attributes = True


class AnnouncementCommentCreate(BaseModel):
    content: str


class AnnouncementCommentResponse(BaseModel):
    id: int
    announcement_id: int
    author_id: int
    author: AuthorBrief | None = None
    content: str
    created_at: datetime

    class Config:
        from_attributes = True
