"""Опросы на главной странице."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Poll(Base):
    __tablename__ = "polls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    question: Mapped[str] = mapped_column(String(500))
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_by = relationship("User", backref="polls_created")
    options: Mapped[list["PollOption"]] = relationship(
        "PollOption", back_populates="poll", order_by="PollOption.id"
    )
    votes: Mapped[list["PollVote"]] = relationship("PollVote", back_populates="poll")


class PollOption(Base):
    __tablename__ = "poll_options"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    poll_id: Mapped[int] = mapped_column(ForeignKey("polls.id", ondelete="CASCADE"), index=True)
    text: Mapped[str] = mapped_column(String(300))

    poll = relationship("Poll", back_populates="options")
    votes: Mapped[list["PollVote"]] = relationship("PollVote", back_populates="option")


class PollVote(Base):
    __tablename__ = "poll_votes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    poll_id: Mapped[int] = mapped_column(ForeignKey("polls.id", ondelete="CASCADE"), index=True)
    option_id: Mapped[int] = mapped_column(ForeignKey("poll_options.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    poll = relationship("Poll", back_populates="votes")
    option = relationship("PollOption", back_populates="votes")
    user = relationship("User", backref="poll_votes")
