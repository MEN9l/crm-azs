"""Дашборд: напоминания по срокам (заявки и задачи, требующие внимания)."""
from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.models import Task, Ticket, User
from app.api.tickets import _query_tickets

from .deps import get_current_user

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

TOMORROW_DAYS = 1  # считаем «требуют внимания» просроченные и со сроком до завтра


@router.get("/attention")
def attention(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    """Заявки и задачи со сроком до завтра включительно или просроченные (не закрытые)."""
    today = date.today()
    due_limit = today + timedelta(days=TOMORROW_DAYS)
    tickets_q = (
        _query_tickets(db, user)
        .options(
            joinedload(Ticket.station),
            joinedload(Ticket.creator),
            joinedload(Ticket.assignee),
        )
        .filter(Ticket.due_date != None)
        .filter(Ticket.due_date <= due_limit)
        .filter(~Ticket.status.in_(["done", "canceled"]))
        .order_by(Ticket.due_date.asc(), Ticket.id.desc())
    )
    tickets = tickets_q.limit(50).all()
    tasks_q = (
        db.query(Task)
        .options(joinedload(Task.assignee))
        .filter(Task.due_date != None)
        .filter(Task.due_date <= due_limit)
        .filter(Task.status != "done")
        .order_by(Task.due_date.asc(), Task.id.desc())
    )
    tasks = tasks_q.limit(50).all()
    return {
        "tickets": [
            {
                "id": t.id,
                "title": t.title,
                "due_date": t.due_date.isoformat() if t.due_date else None,
                "status": t.status,
                "priority": t.priority,
            }
            for t in tickets
        ],
        "tasks": [
            {
                "id": t.id,
                "title": t.title,
                "due_date": t.due_date.isoformat() if t.due_date else None,
                "status": t.status,
            }
            for t in tasks
        ],
    }
