from pydantic import BaseModel


class StationBase(BaseModel):
    name: str
    code: str
    address: str
    is_active: bool = True


class StationCreate(StationBase):
    pass


class StationUpdate(BaseModel):
    name: str | None = None
    address: str | None = None
    is_active: bool | None = None


class StationResponse(StationBase):
    id: int

    class Config:
        from_attributes = True
