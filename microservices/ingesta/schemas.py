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