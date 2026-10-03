from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SensorDataCreate(BaseModel):
    id_chamber: UUID
    temperature: float = Field(ge=-50, le=50)
    consumption_kw: float = Field(ge=0, le=999.999)
    timestamp: datetime


class SensorDataRead(SensorDataCreate):
    """Lectura tal como se devuelve desde la base de datos."""

    model_config = ConfigDict(from_attributes=True)

    id_data: int
    insertion_date: Optional[datetime] = None
    sensor_id: Optional[int] = None

class ChamberCreate(BaseModel):
    id_company: UUID
    name: str = Field(min_length=1, max_length=100)
    location: Optional[str] = Field(default=None, max_length=200)


class ChamberUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    location: Optional[str] = Field(default=None, max_length=200)
    active: Optional[bool] = None


class ChamberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_chamber: UUID
    id_company: Optional[UUID] = None
    name: Optional[str] = None
    location: Optional[str] = None
    active: Optional[bool] = None
    created_at: Optional[datetime] = None