from datetime import datetime

from pydantic import BaseModel


class PollOptionCreate(BaseModel):
    text: str


class PollCreate(BaseModel):
    question: str
    options: list[PollOptionCreate]  # минимум 2 варианта


class PollOptionResponse(BaseModel):
    id: int
    poll_id: int
    text: str
    votes_count: int = 0

    class Config:
        from_attributes = True


class PollResponse(BaseModel):
    id: int
    question: str
    created_by_id: int
    created_at: datetime
    closed_at: datetime | None
    options: list[PollOptionResponse]
    my_vote_option_id: int | None = None  # за что проголосовал текущий пользователь

    class Config:
        from_attributes = True


class PollVoteCreate(BaseModel):
    option_id: int
