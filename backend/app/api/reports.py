"""Простые отчёты для дашборда."""
import csv
import io
from datetime import date, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.models import Ticket, Task, Station, User
from app.api.tickets import _query_tickets
from .deps import get_current_user, require_role

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/summary")
def report_summary(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    date_from: date | None = Query(None, description="Начало периода (заявки по created_at)"),
    date_to: date | None = Query(None, description="Конец периода"),
):
    tickets_q = _query_tickets(db, user)
    if date_from is not None:
        dt_from = datetime.combine(date_from, datetime.min.time())
        tickets_q = tickets_q.filter(Ticket.created_at >= dt_from)
    if date_to is not None:
        dt_to_end = datetime.combine(date_to, datetime.min.time()) + timedelta(days=1)
        tickets_q = tickets_q.filter(Ticket.created_at < dt_to_end)
    tickets = tickets_q.all()
    by_status = {}
    for t in tickets:
        by_status[t.status] = by_status.get(t.status, 0) + 1
    open_tickets = by_status.get("new", 0) + by_status.get("in_progress", 0)
    done_tickets = [t for t in tickets if t.status == "done" and t.updated_at and t.created_at]
    avg_close_hours = None
    if done_tickets:
        total_sec = sum((t.updated_at - t.created_at).total_seconds() for t in done_tickets)
        avg_close_hours = round(total_sec / len(done_tickets) / 3600, 1)
    tickets_by_station = []
    station_counts = {}
    for t in tickets:
        sid = t.station_id or 0
        station_counts[sid] = station_counts.get(sid, 0) + 1
    for sid, count in station_counts.items():
        if sid:
            st = db.query(Station).filter(Station.id == sid).first()
            tickets_by_station.append({"station_id": sid, "station_code": st.code if st else "", "station_name": st.name if st else "", "tickets_count": count})
        else:
            tickets_by_station.append({"station_id": None, "station_code": "", "station_name": "Без АЗС", "tickets_count": count})
    tasks = db.query(Task).all()
    tasks_by_status = {}
    for t in tasks:
        tasks_by_status[t.status] = tasks_by_status.get(t.status, 0) + 1
    in_progress_tasks = tasks_by_status.get("in_progress", 0) + tasks_by_status.get("review", 0)
    stations_count = db.query(Station).filter(Station.is_active == True).count()
    return {
        "open_tickets": open_tickets,
        "total_tickets": len(tickets),
        "by_status": by_status,
        "avg_close_hours": avg_close_hours,
        "tickets_by_station": tickets_by_station,
        "in_progress_tasks": in_progress_tasks,
        "total_tasks": len(tasks),
        "tasks_by_status": tasks_by_status,
        "stations_count": stations_count,
        "date_from": date_from.isoformat() if date_from else None,
        "date_to": date_to.isoformat() if date_to else None,
    }


@router.get("/export")
def report_export_csv(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    format: str = Query("csv", alias="format"),
):
    """Экспорт сводки и списка заявок в CSV. Только admin и chief."""
    require_role(user, ["admin", "chief"])
    if format.lower() != "csv":
        return {"detail": "Поддерживается только format=csv"}
    tickets_q = _query_tickets(db, user).options(
        joinedload(Ticket.station),
        joinedload(Ticket.creator),
        joinedload(Ticket.assignee),
    ).order_by(Ticket.id.desc())
    tickets = tickets_q.all()
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["Сводка"])
    w.writerow(["Показатель", "Значение"])
    w.writerow(["Открытые заявки", sum(1 for t in tickets if t.status in ("new", "in_progress"))])
    w.writerow(["Всего заявок", len(tickets)])
    w.writerow(["АЗС (активных)", db.query(Station).filter(Station.is_active == True).count()])
    w.writerow([])
    w.writerow(["Заявки"])
    w.writerow(["ID", "Название", "Статус", "Приоритет", "АЗС", "Создатель", "Исполнитель", "Срок", "Создана"])
    for t in tickets:
        station_code = t.station.code if t.station else ""
        creator_name = t.creator.full_name if t.creator else ""
        assignee_name = t.assignee.full_name if t.assignee else ""
        due = str(t.due_date) if t.due_date else ""
        created = t.created_at.isoformat() if t.created_at else ""
        w.writerow([t.id, (t.title or ""), t.status, t.priority, station_code, creator_name, assignee_name, due, created])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=report.csv"},
    )
