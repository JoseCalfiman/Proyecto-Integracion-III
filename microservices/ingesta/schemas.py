from datetime import datetime, timezone
from typing import Optional
from uuid import UUID
 
from pydantic import BaseModel, Field, field_validator, model_validator
 
# Rangos físicos razonables para una cámara frigorífica/congelador.
# Cubren desde congeladores industriales (-50°C) hasta ambientes
# fuera de control (hasta 50°C) sin permitir valores absurdos.
MIN_TEMPERATURE = -50.0
MAX_TEMPERATURE = 50.0
 
# El consumo eléctrico (kW) nunca puede ser negativo. El máximo es
# un techo de seguridad para detectar payloads corruptos.
MIN_CONSUMPTION_KW = 0.0
MAX_CONSUMPTION_KW = 999.999
 
 
class SensorDataCreate(BaseModel):
    """Schema de entrada para registrar una lectura de sensor."""
 
    chamber_id: UUID = Field(
        ...,
        description="ID (UUID) de la cámara a la que pertenece la lectura.",
    )
    temperature: float = Field(
        ...,
        ge=MIN_TEMPERATURE,
        le=MAX_TEMPERATURE,
        description="Temperatura registrada en °C (entre -50 y 50).",
    )
    consumption_kw: float = Field(
        ...,
        ge=MIN_CONSUMPTION_KW,
        le=MAX_CONSUMPTION_KW,
        description="Consumo eléctrico instantáneo en kW (no puede ser negativo).",
    )
    recorded_at: datetime = Field(
        ...,
        description="Timestamp (UTC) en que se tomó la lectura.",
    )
 
    @field_validator("temperature", "consumption_kw")
    @classmethod
    def _no_nan_or_inf(cls, value: float) -> float:
        """Rechaza NaN/Infinity, que Pydantic no filtra por defecto con float."""
        import math
 
        if math.isnan(value) or math.isinf(value):
            raise ValueError("El valor no puede ser NaN ni infinito")
        return round(value, 3)
 
    @field_validator("recorded_at")
    @classmethod
    def _recorded_at_not_in_future(cls, value: datetime) -> datetime:
        """No se aceptan lecturas con timestamp futuro (margen de 5 min
        para tolerar pequeños desfases de reloj entre dispositivos)."""
        now = datetime.now(timezone.utc)
        # Si el timestamp viene sin tzinfo, se asume UTC.
        value_utc = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        max_skew_seconds = 300  # 5 minutos
        if (value_utc - now).total_seconds() > max_skew_seconds:
            raise ValueError("recorded_at no puede estar en el futuro")
        return value
 
    @model_validator(mode="after")
    def _sanity_check(self) -> "SensorDataCreate":
        """Validación cruzada opcional: aquí se pueden agregar reglas que
        combinen varios campos (ej. rangos distintos según tipo de cámara)."""
        return self
 
    class Config:
        json_schema_extra = {
            "example": {
                "chamber_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "temperature": -18.5,
                "consumption_kw": 2.340,
                "recorded_at": "2026-09-18T14:30:00Z",
            }
        }
 
 
class SensorDataRead(SensorDataCreate):
    """Schema de salida: extiende el de creación con los campos generados
    por la base de datos al persistir el registro."""
 
    id_data: int
    insertion_date: Optional[datetime] = None
    sensor_id: Optional[int] = Field(
        default=None, description="ID del sensor que reportó la lectura, si aplica."
    )
 
    class Config:
        from_attributes = True  # permite construir desde el modelo ORM (SQLAlchemy)
 
