from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SensorDataCreate(BaseModel):
    """Lectura de sensor recibida (por MQTT o API)."""

    chamber_id: UUID
    temperature: float = Field(ge=-50, le=50)  # °C
    consumption_kw: float = Field(ge=0, le=999.999)
    recorded_at: datetime


class SensorDataRead(SensorDataCreate):
    """Lectura tal como se devuelve desde la base de datos."""

    model_config = ConfigDict(from_attributes=True)

    id_data: int
    insertion_date: Optional[datetime] = None
    sensor_id: Optional[int] = None