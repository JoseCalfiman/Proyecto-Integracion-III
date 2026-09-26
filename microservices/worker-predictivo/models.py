from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID

from db import Base

class GeneratedPrediction(Base):
    __tablename__ = "generated_predictions"

    prediction_id = Column(Integer, primary_key=True, autoincrement=True)
    chamber_id = Column(UUID(as_uuid=True), ForeignKey("chambers.id_chamber"), nullable=False, index=True)
    calculated_slope = Column(Float, nullable=True)
    projected_temperature = Column(Float, nullable=True)
    remaining_time_min = Column(Float, nullable=True)
    risk_level = Column(String(20), nullable=False)
    calculated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    def __repr__(self):
        return (
            f"GeneratedPrediction chamber_id={self.chamber_id} "
            f"risk_level={self.risk_level} "
            f"remaining_time_min={self.remaining_time_min}"
        )