import csv
import io
from datetime import date, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.email import send_email
from app.models import Attachment, Notification, Ticket, TicketComment, TicketHistory, User
from app.schemas import (
    TicketCreate,
    TicketResponse,
    TicketUpdate,
    TicketCommentCreate,
    TicketCommentResponse,
    TicketHistoryResponse,
)

from .deps import get_current_user, require_role

router = APIRouter(prefix="/tickets", tags=["tickets"])


def _query_tickets(db: Session, user: User):
    q = db.query(Ticket).options(
        joinedload(Ticket.station),
        joinedload(Ticket.creator),
        joinedload(Ticket.assignee),
    )
    if user.role not in ("chief", "admin"):
        station_ids = [s.id for s in user.stations]
        q = q.filter((Ticket.station_id == None) | (Ticket.station_id.in_(station_ids)))
        if user.role == "operator":
            q = q.filter((Ticket.creator_id == user.id) | (Ticket.assignee_id == user.id))
    return q


@router.get("", response_model=list[TicketResponse])
def list_tickets(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    status_filter: str | None = Query(None, alias="status"),
    search: str | None = Query(None, alias="q"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    due_week: bool = Query(False, description="Только заявки со сроком на эту неделю"),
    tag: str | None = Query(None, description="Фильтр по тегу (подстрока в тегах заявки)"),
):
    q = _query_tickets(db, user).order_by(Ticket.due_date.asc().nulls_last(), Ticket.id.desc())
    if status_filter:
        q = q.filter(Ticket.status == status_filter)
    if tag and tag.strip():
        q = q.filter(Ticket.tags.ilike(f"%{tag.strip()}%"))
    if due_week:
        today = date.today()
        week_end = today + timedelta(days=7)
        q = q.filter(Ticket.due_date != None, Ticket.due_date >= today, Ticket.due_date <= week_end)
    if search and search.strip():
        term = f"%{search.strip()}%"
        q = q.filter(or_(
            Ticket.title.ilike(term),
            (Ticket.description != None) & (Ticket.description.ilike(term)),
        ))
    return q.offset(offset).limit(limit).all()


@router.get("/export")
def export_tickets_csv(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    status_filter: str | None = Query(None, alias="status"),
    search: str | None = Query(None, alias="q"),
    due_week: bool = Query(False),
    tag: str | None = Query(None),
    date_from: date | None = Query(None, description="Начало периода по дате создания"),
    date_to: date | None = Query(None, description="Конец периода по дате создания"),
):
    """Экспорт заявок в CSV с учётом фильтров (те же, что в списке + период)."""
    q = (
        _query_tickets(db, user)
        .options(
            joinedload(Ticket.station),
            joinedload(Ticket.creator),
            joinedload(Ticket.assignee),
        )
        .order_by(Ticket.due_date.asc().nulls_last(), Ticket.id.desc())
    )
    if status_filter:
        q = q.filter(Ticket.status == status_filter)
    if tag and tag.strip():
        q = q.filter(Ticket.tags.ilike(f"%{tag.strip()}%"))
    if due_week:
        today = date.today()
        week_end = today + timedelta(days=7)
        q = q.filter(Ticket.due_date != None, Ticket.due_date >= today, Ticket.due_date <= week_end)
    if search and search.strip():
        term = f"%{search.strip()}%"
        q = q.filter(or_(
            Ticket.title.ilike(term),
            (Ticket.description != None) & (Ticket.description.ilike(term)),
        ))
    if date_from is not None:
        q = q.filter(Ticket.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to is not None:
        q = q.filter(Ticket.created_at < datetime.combine(date_to, datetime.min.time()) + timedelta(days=1))
    tickets = q.limit(5000).all()
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";")
    writer.writerow(["ID", "Название", "Описание", "Статус", "Приоритет", "Тип", "АЗС", "Создатель", "Исполнитель", "Срок", "Теги", "Создана"])
    for t in tickets:
        station_code = t.station.code if t.station else ""
        creator_name = t.creator.full_name if t.creator else ""
        assignee_name = t.assignee.full_name if t.assignee else ""
        due = str(t.due_date) if t.due_date else ""
        created = t.created_at.strftime("%Y-%m-%d %H:%M") if t.created_at else ""
        writer.writerow([
            t.id, t.title or "", (t.description or "")[:500], t.status, t.priority, t.type or "",
            station_code, creator_name, assignee_name, due, t.tags or "", created,
        ])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue().encode("utf-8-sig")]),
        media_type="text/csv; charset=utf-8-sig",
        headers={"Content-Disposition": "attachment; filename=tickets_export.csv"},
    )


@router.get("/{ticket_id}", response_model=TicketResponse)
def get_ticket(
    ticket_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    ticket = (
        _query_tickets(db, user)
        .filter(Ticket.id == ticket_id)
        .first()
    )
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заявка не найдена")
    return ticket


@router.post("", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
def create_ticket(
    data: TicketCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    ticket = Ticket(
        title=data.title,
        description=data.description,
        priority=data.priority,
        type=data.type,
        station_id=data.station_id,
        creator_id=user.id,
        department_id=getattr(data, "department_id", None),
        due_date=data.due_date,
        tags=data.tags,
    )
    if getattr(data, "assignee_id", None) and user.role in ("admin", "chief"):
        ticket.assignee_id = data.assignee_id
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    # Уведомление chief и admin о новой заявке (кроме создателя)
    for u in db.query(User).filter(User.role.in_(("chief", "admin")), User.id != user.id, User.is_active == True):
        db.add(Notification(user_id=u.id, type="ticket_created", message=f"Новая заявка #{ticket.id}: {ticket.title[:50]}"))
    db.commit()
    if user.email:
        send_email(
            user.email,
            f"Заявка #{ticket.id} создана",
            f"Заявка создана: {ticket.title}\n\nНомер: #{ticket.id}\nСтатус: {ticket.status}",
        )
    ticket = (
        db.query(Ticket)
        .options(
            joinedload(Ticket.station),
            joinedload(Ticket.creator),
            joinedload(Ticket.assignee),
        )
        .filter(Ticket.id == ticket.id)
        .first()
    )
    return ticket


@router.patch("/{ticket_id}", response_model=TicketResponse)
def update_ticket(
    ticket_id: int,
    data: TicketUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    ticket = _query_tickets(db, user).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заявка не найдена")
    updates = data.model_dump(exclude_unset=True)
    if "assignee_id" in updates and user.role not in ("admin", "chief"):
        del updates["assignee_id"]
    if "department_id" in updates and user.role not in ("admin", "chief"):
        # отдел можно выбрать при постановке, но менять маршрут заявки — только руководителям
        del updates["department_id"]
    history_fields = ("status", "assignee_id", "due_date")
    old_vals = {k: getattr(ticket, k) for k in history_fields if k in updates}
    for k, v in updates.items():
        setattr(ticket, k, v)
    for k in history_fields:
        if k not in updates:
            continue
        old_v = old_vals.get(k)
        new_v = updates[k]
        if old_v is not None:
            old_s = str(old_v)
        else:
            old_s = None
        if new_v is not None:
            new_s = str(new_v)
        else:
            new_s = None
        if old_s != new_s:
            db.add(TicketHistory(ticket_id=ticket_id, user_id=user.id, field_name=k, old_value=old_s, new_value=new_s))
    if "status" in updates:
        notify_user_id = ticket.assignee_id or ticket.creator_id
        if notify_user_id and notify_user_id != user.id:
            db.add(Notification(user_id=notify_user_id, type="ticket_status", message=f"Заявка #{ticket_id}: статус изменён на {updates['status']}"))
    if "assignee_id" in updates and updates.get("assignee_id"):
        assignee_id = updates["assignee_id"]
        db.add(Notification(user_id=assignee_id, type="ticket_assign", message=f"Вам назначена заявка #{ticket_id}: {ticket.title[:50]}"))
        assignee = db.get(User, assignee_id)
        if assignee and getattr(assignee, "email", None):
            send_email(
                assignee.email,
                f"Вам назначена заявка #{ticket_id}",
                f"Вам назначена заявка: {ticket.title}\n\nНомер: #{ticket_id}\nСтатус: {ticket.status}",
            )
    db.commit()
    db.refresh(ticket)
    ticket = (
        db.query(Ticket)
        .options(
            joinedload(Ticket.station),
            joinedload(Ticket.creator),
            joinedload(Ticket.assignee),
        )
        .filter(Ticket.id == ticket_id)
        .first()
    )
    return ticket


@router.get("/{ticket_id}/history", response_model=list[TicketHistoryResponse])
def list_ticket_history(
    ticket_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    ticket = _query_tickets(db, user).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заявка не найдена")
    try:
        records = (
            db.query(TicketHistory)
            .options(joinedload(TicketHistory.user))
            .filter(TicketHistory.ticket_id == ticket_id)
            .order_by(TicketHistory.created_at.desc())
            .all()
        )
        return records
    except Exception:
        return []


@router.get("/{ticket_id}/comments", response_model=list[TicketCommentResponse])
def list_ticket_comments(
    ticket_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    ticket = _query_tickets(db, user).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заявка не найдена")
    comments = (
        db.query(TicketComment)
        .options(joinedload(TicketComment.user))
        .filter(TicketComment.ticket_id == ticket_id)
        .order_by(TicketComment.created_at.asc())
        .all()
    )
    return comments


@router.post(
    "/{ticket_id}/comments",
    response_model=TicketCommentResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_ticket_comment(
    ticket_id: int,
    data: TicketCommentCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    ticket = _query_tickets(db, user).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заявка не найдена")
    comment = TicketComment(
        ticket_id=ticket_id,
        user_id=user.id,
        content=data.content.strip()[:5000],
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    comment = (
        db.query(TicketComment)
        .options(joinedload(TicketComment.user))
        .filter(TicketComment.id == comment.id)
        .first()
    )
    return comment


@router.delete("/{ticket_id}")
def delete_ticket(
    ticket_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    ticket = _query_tickets(db, user).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заявка не найдена")

    is_privileged = user.role in ("admin", "chief")
    is_creator = ticket.creator_id is not None and ticket.creator_id == user.id
    if not (is_privileged or is_creator):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Недостаточно прав")

    # Создателю разрешаем удаление только пока заявка не ушла в работу
    if (not is_privileged) and ticket.status not in ("new", "canceled"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Можно удалить только новую или отменённую заявку")

    # Удаляем вложения (и файлы на диске), комментарии и историю, чтобы не упереться в FK.
    atts = db.query(Attachment).filter(Attachment.ticket_id == ticket_id).all()
    for a in atts:
        try:
            p = a.get_file_path()
            if p.exists():
                p.unlink()
        except Exception:
            pass
        db.delete(a)

    db.query(TicketComment).filter(TicketComment.ticket_id == ticket_id).delete(synchronize_session=False)
    db.query(TicketHistory).filter(TicketHistory.ticket_id == ticket_id).delete(synchronize_session=False)
    db.delete(ticket)
    db.commit()
    return {"ok": True}
