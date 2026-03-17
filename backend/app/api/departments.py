"""Отделы (иерархия): список и админ-CRUD."""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Department, User
from app.schemas import DepartmentCreate, DepartmentResponse, DepartmentUpdate

from .deps import get_current_user, require_role

router = APIRouter(prefix="/departments", tags=["departments"])


@router.get("", response_model=list[DepartmentResponse])
def list_departments(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    parent_id: int | None = Query(None, description="Фильтр по родительскому отделу"),
):
    q = db.query(Department).order_by(Department.name.asc())
    if parent_id is None:
        return q.all()
    return q.filter(Department.parent_id == parent_id).all()


@router.post("", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
def create_department(
    data: DepartmentCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    require_role(user, ["admin", "chief"])
    name = (data.name or "").strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Название отдела обязательно")
    exists = db.query(Department).filter(Department.name == name).first()
    if exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Отдел с таким названием уже существует")
    if data.parent_id is not None:
        parent = db.query(Department).filter(Department.id == data.parent_id).first()
        if not parent:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Родительский отдел не найден")
    dep = Department(name=name, parent_id=data.parent_id)
    db.add(dep)
    db.commit()
    db.refresh(dep)
    return dep


@router.patch("/{department_id}", response_model=DepartmentResponse)
def update_department(
    department_id: int,
    data: DepartmentUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    require_role(user, ["admin", "chief"])
    dep = db.query(Department).filter(Department.id == department_id).first()
    if not dep:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Отдел не найден")
    updates = data.model_dump(exclude_unset=True)
    if "name" in updates and updates["name"] is not None:
        name = updates["name"].strip()
        if not name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Название отдела обязательно")
        exists = db.query(Department).filter(Department.name == name, Department.id != department_id).first()
        if exists:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Отдел с таким названием уже существует")
        dep.name = name
    if "parent_id" in updates:
        pid = updates["parent_id"]
        if pid is not None:
            if pid == department_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нельзя назначить отдел родителем самому себе")
            parent = db.query(Department).filter(Department.id == pid).first()
            if not parent:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Родительский отдел не найден")
        dep.parent_id = pid
    if "pos_x" in updates:
        dep.pos_x = updates["pos_x"]
    if "pos_y" in updates:
        dep.pos_y = updates["pos_y"]
    db.commit()
    db.refresh(dep)
    return dep


@router.delete("/{department_id}")
def delete_department(
    department_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    require_role(user, ["admin", "chief"])
    dep = db.query(Department).filter(Department.id == department_id).first()
    if not dep:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Отдел не найден")
    used = (
        db.query(User).filter(User.department_id == department_id).first()
        or db.execute(text("SELECT 1 FROM tickets WHERE department_id = :id LIMIT 1"), {"id": department_id}).first()
    )
    if used:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Отдел используется (есть сотрудники/заявки)")
    has_children = db.query(Department).filter(Department.parent_id == department_id).first()
    if has_children:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Сначала удалите/переназначьте дочерние отделы")
    db.delete(dep)
    db.commit()
    return {"ok": True}

