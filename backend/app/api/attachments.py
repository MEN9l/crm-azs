"""Вложения к заявкам: загрузка и скачивание."""
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Attachment, Chat, Message, Ticket, User
from app.models.attachment import get_uploads_dir, generate_stored_filename
from app.schemas.attachment import AttachmentResponse

from .deps import get_current_user
from .tickets import _query_tickets

router = APIRouter(prefix="/attachments", tags=["attachments"])

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".txt", ".zip"}


@router.get("/ticket/{ticket_id}", response_model=list[AttachmentResponse])
def list_ticket_attachments(
    ticket_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    ticket = _query_tickets(db, user).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заявка не найдена")
    return db.query(Attachment).filter(Attachment.ticket_id == ticket_id).order_by(Attachment.created_at.desc()).all()


@router.post("/ticket/{ticket_id}", response_model=AttachmentResponse, status_code=status.HTTP_201_CREATED)
def upload_ticket_attachment(
    ticket_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    file: UploadFile = File(...),
):
    ticket = _query_tickets(db, user).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заявка не найдена")
    ext = Path(file.filename or "").suffix.lower()
    if ext and ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Недопустимый тип файла")
    content = file.file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Файл слишком большой (макс. 10 МБ)")
    stored = generate_stored_filename(file.filename or "file")
    uploads_dir = get_uploads_dir()
    (uploads_dir / stored).write_bytes(content)
    att = Attachment(
        ticket_id=ticket_id,
        stored_name=stored,
        original_name=file.filename or "file",
        uploaded_by_id=user.id,
    )
    db.add(att)
    db.commit()
    db.refresh(att)
    return att


@router.get("/message/{message_id}", response_model=list[AttachmentResponse])
def list_message_attachments(
    message_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    msg = db.query(Message).filter(Message.id == message_id).first()
    if not msg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Сообщение не найдено")
    chat = db.query(Chat).filter(Chat.id == msg.chat_id).first()
    if not chat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Чат не найден")
    return db.query(Attachment).filter(Attachment.message_id == message_id).order_by(Attachment.created_at).all()


@router.post("/message/{message_id}", response_model=AttachmentResponse, status_code=status.HTTP_201_CREATED)
def upload_message_attachment(
    message_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    file: UploadFile = File(...),
):
    msg = db.query(Message).filter(Message.id == message_id).first()
    if not msg:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Сообщение не найдено")
    ext = Path(file.filename or "").suffix.lower()
    if ext and ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Недопустимый тип файла")
    content = file.file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Файл слишком большой (макс. 10 МБ)")
    stored = generate_stored_filename(file.filename or "file")
    uploads_dir = get_uploads_dir()
    (uploads_dir / stored).write_bytes(content)
    att = Attachment(
        message_id=message_id,
        stored_name=stored,
        original_name=file.filename or "file",
        uploaded_by_id=user.id,
    )
    db.add(att)
    db.commit()
    db.refresh(att)
    return att


@router.get("/{attachment_id}/download")
def download_attachment(
    attachment_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    att = db.query(Attachment).filter(Attachment.id == attachment_id).first()
    if not att:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Файл не найден")
    if att.ticket_id:
        ticket = _query_tickets(db, user).filter(Ticket.id == att.ticket_id).first()
        if not ticket:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Нет доступа")
    if att.message_id:
        msg = db.query(Message).filter(Message.id == att.message_id).first()
        if not msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Нет доступа")
    path = att.get_file_path()
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Файл не найден на диске")
    return FileResponse(path, filename=att.original_name)
