from sqlalchemy import Column, BigInteger, String, Numeric, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class Prediction(Base):
    __tablename__ = "predictions"

    id_prediction = Column(BigInteger, primary_key=True, autoincrement=True)
    id_chamber = Column(String(36), nullable=False)  # ← SIN FK
    calculated_slope = Column(Numeric(8, 4))
    projected_temperature = Column(Numeric(5, 2))
    remaining_time_min = Column(Numeric(8, 2))
    risk_level = Column(String(20), nullable=False)
    calculation_date = Column(DateTime(timezone=True), default=datetime.utcnow)
    id_worker = Column(String(50))


# Alias para compatibilidad con haccp_predictions.py
GeneratedPrediction = Prediction