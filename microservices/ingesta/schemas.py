
# su funcion principal es crear los modelos de datos que se utilizan en la API y en la base de datos. Estos modelos definen la estructura de los datos, las validaciones y las relaciones entre ellos.  

from datetime import datetime
from typing import Optional, Literal
from uuid import UUID

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator



class SensorDataCreate(BaseModel):
    id_chamber: UUID = Field(validation_alias=AliasChoices("id_chamber", "chamber_id"))
    temperature: float = Field(ge=-50, le=50)
    consumption_kw: float = Field(ge=0, le=999.999)
    timestamp: datetime = Field(validation_alias=AliasChoices("timestamp", "recorded_at"))


class DashboardLive(BaseModel):
    active_chambers: int
    active_alerts: int
    total_consumption_kw: float
    estimated_savings_clp: float


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

class AlertAction(BaseModel):
    id_user: UUID  # temporal: saldrá del JWT cuando exista auth
    note: Optional[str] = Field(default=None, max_length=500)


class AlertRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_alert: int
    id_chamber: Optional[UUID] = None
    chamber_name: Optional[str] = None
    id_prediction: Optional[int] = None
    id_haccp_rule: Optional[int] = None
    alert_type: Optional[str] = None
    severity: str
    status: str
    message: Optional[str] = None
    generation_date: Optional[datetime] = None
    id_user_acknowledged: Optional[UUID] = None
    acknowledgment_date: Optional[datetime] = None
    id_user_resolved: Optional[UUID] = None
    resolution_date: Optional[datetime] = None


class AlertAuditRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_audit: int
    id_alert: int
    id_user: Optional[UUID] = None
    action: Optional[str] = None
    detail: Optional[str] = None
    action_date: Optional[datetime] = None

HaccpSeverity = Literal["low", "medium", "high", "critical"]


class HaccpRuleUpdate(BaseModel):
    max_absolute_temp: float = Field(ge=-50, le=50)
    min_absolute_temp: float = Field(ge=-50, le=50)
    tolerance_time_min: int = Field(ge=1, le=1440)
    severity: HaccpSeverity = "medium"
    active: bool = True
    id_user_modified: Optional[UUID] = None  # temporal: saldrá del JWT

    @model_validator(mode="after")
    def check_range(self):
        if self.min_absolute_temp >= self.max_absolute_temp:
            raise ValueError("min_absolute_temp debe ser menor que max_absolute_temp")
        return self


class HaccpRuleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_rule: Optional[int] = None
    id_chamber: UUID
    chamber_name: Optional[str] = None
    max_absolute_temp: float
    min_absolute_temp: float
    tolerance_time_min: int
    severity: str
    active: bool
    review_date: Optional[datetime] = None
    id_user_modified: Optional[UUID] = None