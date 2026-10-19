from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel


class Status(str, Enum):
    ONLINE = "ONLINE"
    DEGRADED = "DEGRADED"
    OFFLINE = "OFFLINE"


class HealthResponse(BaseModel):
    status: str = "ok"


class Replicas(BaseModel):
    desired: int
    ready: int


class ComponentStatus(BaseModel):
    name: str
    type: str 
    status: Status
    latency_ms: Optional[int] = None  
    detail: str
    last_check: datetime
    replicas: Optional[Replicas] = None 
    restarts: Optional[int] = None  
    restartable: bool


class Summary(BaseModel):
    total: int
    online: int
    degraded: int
    offline: int


class SystemStatus(BaseModel):
    status: Status
    checked_at: datetime
    summary: Summary
    components: List[ComponentStatus]
