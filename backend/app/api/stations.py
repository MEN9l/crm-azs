from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Station
from app.schemas import StationCreate, StationResponse, StationUpdate

from .deps import get_current_user, require_role
from app.models import User

router = APIRouter(prefix="/stations", tags=["stations"])


@router.get("", response_model=list[StationResponse])
def list_stations(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    q = db.query(Station)
    if user.role not in ("chief", "admin", "superuser"):
        q = q.join(Station.users).filter(User.id == user.id)
    return q.all()


@router.get("/{station_id}", response_model=StationResponse)
def get_station(
    station_id: int,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    station = db.query(Station).filter(Station.id == station_id).first()
    if not station:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="АЗС не найдена")
    return station


@router.post("", response_model=StationResponse, status_code=status.HTTP_201_CREATED)
def create_station(
    data: StationCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    require_role(user, ["admin", "chief"])
    if db.query(Station).filter(Station.code == data.code).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Код АЗС уже существует")
    station = Station(name=data.name, code=data.code, address=data.address, is_active=data.is_active)
    db.add(station)
    db.commit()
    db.refresh(station)
    return station


@router.patch("/{station_id}", response_model=StationResponse)
def update_station(
    station_id: int,
    data: StationUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
):
    require_role(user, ["admin", "chief"])
    station = db.query(Station).filter(Station.id == station_id).first()
    if not station:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="АЗС не найдена")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(station, k, v)
    db.commit()
    db.refresh(station)
    return station
