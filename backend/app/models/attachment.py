from datetime import datetime
import uuid
from pathlib import Path

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

UPLOADS_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"


def get_uploads_dir() -> Path:
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    return UPLOADS_DIR


def generate_stored_filename(original: str) -> str:
    ext = Path(original).suffix or ""
    return f"{uuid.uuid4().hex}{ext}"


class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ticket_id: Mapped[int | None] = mapped_column(ForeignKey("tickets.id"), nullable=True)
    message_id: Mapped[int | None] = mapped_column(ForeignKey("messages.id"), nullable=True)
    stored_name: Mapped[str] = mapped_column(String(255))
    original_name: Mapped[str] = mapped_column(String(255))
    uploaded_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    ticket = relationship("Ticket", backref="attachments")
    message = relationship("Message", backref="attachments")
    uploaded_by = relationship("User")

    def get_file_path(self) -> Path:
        return get_uploads_dir() / self.stored_name
