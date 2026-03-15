"""Объявления на общей доске (главная страница)."""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Announcement(Base):
    __tablename__ = "announcements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(500))
    content: Mapped[str] = mapped_column(Text)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    is_important: Mapped[bool] = mapped_column(Boolean, default=False)
    tag: Mapped[str | None] = mapped_column(String(100), nullable=True)  # Важное, Техническое, HR и т.д.

    author = relationship("User", backref="announcements")
    comments: Mapped[list["AnnouncementComment"]] = relationship(
        "AnnouncementComment", back_populates="announcement", order_by="AnnouncementComment.id"
    )


class AnnouncementComment(Base):
    __tablename__ = "announcement_comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    announcement_id: Mapped[int] = mapped_column(ForeignKey("announcements.id", ondelete="CASCADE"), index=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    announcement = relationship("Announcement", back_populates="comments")
    author = relationship("User", backref="announcement_comments")
