from datetime import date, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.models import Task, TaskChecklistItem, TaskHistory, User
from app.schemas import (
    TaskChecklistBulkCreate,
    TaskChecklistItemCreate,
    TaskChecklistItemResponse,
    TaskChecklistItemUpdate,
    TaskCreate,
    TaskHistoryResponse,
    TaskResponse,
    TaskUpdate,
)

from .deps import get_current_user

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskResponse])
def list_tasks(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    status_filter: str | None = Query(None, alias="status"),
    search: str | None = Query(None, alias="q"),
    due_week: bool = Query(False, description="Только задачи со сроком на эту неделю"),
    limit: int = Query(300, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    q = db.query(Task).options(joinedload(Task.assignee), joinedload(Task.department)).order_by(Task.id.desc())
    if status_filter:
        q = q.filter(Task.status == status_filter)
    if due_week:
        today = date.today()
        week_end = today + timedelta(days=7)
        q = q.filter(Task.due_date != None, Task.due_date >= today, Task.due_date <= week_end)
    if search and search.strip():
        term = f"%{search.strip()}%"
        q = q.filter(or_(Task.title.ilike(term), (Task.description != None) & (Task.description.ilike(term))))
    return q.offset(offset).limit(limit).all()


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    task = db.query(Task).options(joinedload(Task.assignee), joinedload(Task.department)).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Задача не найдена")
    return task


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
def create_task(
    data: TaskCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    task = Task(
        title=data.title,
        description=data.description,
        status=getattr(data, "status", "backlog") or "backlog",
        priority=data.priority,
        ticket_id=data.ticket_id,
        assignee_id=None,
        department_id=getattr(data, "department_id", None),
        due_date=data.due_date,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    task = db.query(Task).options(joinedload(Task.assignee), joinedload(Task.department)).filter(Task.id == task.id).first()
    return task


@router.get("/{task_id}/history", response_model=list[TaskHistoryResponse])
def list_task_history(
    task_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Задача не найдена")
    records = (
        db.query(TaskHistory)
        .options(joinedload(TaskHistory.user))
        .filter(TaskHistory.task_id == task_id)
        .order_by(TaskHistory.created_at.desc())
        .all()
    )
    return records


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    data: TaskUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Задача не найдена")
    updates = data.model_dump(exclude_unset=True)
    # assignee_id оставляем в модели для совместимости, но в UI используем department_id
    history_fields = ("status", "assignee_id", "department_id", "due_date")
    old_vals = {k: getattr(task, k) for k in history_fields if k in updates}
    for k, v in updates.items():
        setattr(task, k, v)
    for k in history_fields:
        if k not in updates:
            continue
        old_v, new_v = old_vals.get(k), updates[k]
        old_s = str(old_v) if old_v is not None else None
        new_s = str(new_v) if new_v is not None else None
        if old_s != new_s:
            db.add(TaskHistory(task_id=task_id, user_id=user.id, field_name=k, old_value=old_s, new_value=new_s))
    db.commit()
    db.refresh(task)
    task = db.query(Task).options(joinedload(Task.assignee), joinedload(Task.department)).filter(Task.id == task_id).first()
    return task


@router.get("/{task_id}/checklist", response_model=list[TaskChecklistItemResponse])
def list_task_checklist(
    task_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Задача не найдена")
    items = (
        db.query(TaskChecklistItem)
        .options(joinedload(TaskChecklistItem.done_by))
        .filter(TaskChecklistItem.task_id == task_id)
        .order_by(TaskChecklistItem.id.asc())
        .all()
    )
    return items


@router.post("/{task_id}/checklist", response_model=TaskChecklistItemResponse, status_code=status.HTTP_201_CREATED)
def create_task_checklist_item(
    task_id: int,
    data: TaskChecklistItemCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Задача не найдена")
    name = (data.station_name or "").strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Название АЗС не заполнено")
    item = TaskChecklistItem(task_id=task_id, station_name=name, is_done=False)
    db.add(item)
    db.commit()
    db.refresh(item)
    item = (
        db.query(TaskChecklistItem)
        .options(joinedload(TaskChecklistItem.done_by))
        .filter(TaskChecklistItem.id == item.id)
        .first()
    )
    return item


@router.post("/{task_id}/checklist/bulk", response_model=list[TaskChecklistItemResponse], status_code=status.HTTP_201_CREATED)
def bulk_create_task_checklist(
    task_id: int,
    data: TaskChecklistBulkCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Задача не найдена")
    raw = data.stations or []
    names: list[str] = []
    seen: set[str] = set()
    for s in raw:
        n = (s or "").strip()
        if not n:
            continue
        key = n.lower()
        if key in seen:
            continue
        seen.add(key)
        names.append(n)
    if not names:
        return []
    if len(names) > 1000:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Слишком много АЗС за раз (макс. 1000)")
    objs = [TaskChecklistItem(task_id=task_id, station_name=n, is_done=False) for n in names]
    db.add_all(objs)
    db.commit()
    ids = [o.id for o in objs if o.id]
    items = (
        db.query(TaskChecklistItem)
        .options(joinedload(TaskChecklistItem.done_by))
        .filter(TaskChecklistItem.id.in_(ids))
        .order_by(TaskChecklistItem.id.asc())
        .all()
    )
    return items


@router.patch("/{task_id}/checklist/{item_id}", response_model=TaskChecklistItemResponse)
def update_task_checklist_item(
    task_id: int,
    item_id: int,
    data: TaskChecklistItemUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    item = db.query(TaskChecklistItem).filter(TaskChecklistItem.id == item_id, TaskChecklistItem.task_id == task_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пункт чек-листа не найден")
    item.is_done = bool(data.is_done)
    if item.is_done:
        item.done_by_id = user.id
        item.done_at = datetime.utcnow()
    else:
        item.done_by_id = None
        item.done_at = None
    db.commit()
    db.refresh(item)
    item = (
        db.query(TaskChecklistItem)
        .options(joinedload(TaskChecklistItem.done_by))
        .filter(TaskChecklistItem.id == item.id)
        .first()
    )
    return item


@router.delete("/{task_id}/checklist/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task_checklist_item(
    task_id: int,
    item_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    item = db.query(TaskChecklistItem).filter(TaskChecklistItem.id == item_id, TaskChecklistItem.task_id == task_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пункт чек-листа не найден")
    db.delete(item)
    db.commit()
    return None
