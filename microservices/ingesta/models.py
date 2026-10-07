import uuid

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship

from database import Base

class Company(Base):
    __tablename__ = "company"

    id_company = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tax_id = Column(String(12), nullable=False, unique=True)
    name = Column(String(150))
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Role(Base):
    __tablename__ = "roles"

    id_role = Column(Integer, primary_key=True, autoincrement=True)
    role_name = Column(String(30), nullable=False, unique=True)


class User(Base):
    __tablename__ = "users"

    id_user = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_company = Column(UUID(as_uuid=True), ForeignKey("company.id_company"))
    id_role = Column(Integer, ForeignKey("roles.id_role"))
    email = Column(String(150), nullable=False, unique=True)
    password_hash = Column(String(255))
    name = Column(String(100))
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Chamber(Base):
    __tablename__ = "chambers"

    id_chamber = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_company = Column(UUID(as_uuid=True), ForeignKey("company.id_company"))
    name = Column(String(100))
    location = Column(String(200))
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Sensor(Base):
    __tablename__ = "sensors"

    id_sensor = Column(BigInteger, primary_key=True, autoincrement=True)
    id_chamber = Column(UUID(as_uuid=True), ForeignKey("chambers.id_chamber"))
    sensor_type = Column(String(50))
    mqtt_identifier = Column(String(100))
    model = Column(String(50))
    status = Column(String(20), default="active")  # active | inactive | maintenance
    installation_date = Column(DateTime(timezone=True), server_default=func.now())


class SensorData(Base):
    __tablename__ = "sensor_data"

    # PK compuesta (id_data, timestamp): requerida por la hipertabla de TimescaleDB
    id_data = Column(BigInteger, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), primary_key=True, nullable=False)
    id_chamber = Column(UUID(as_uuid=True), ForeignKey("chambers.id_chamber"))
    id_sensor = Column(BigInteger, ForeignKey("sensors.id_sensor"))
    insertion_date = Column(DateTime(timezone=True), server_default=func.now())
    temperature = Column(Numeric(5, 2))
    consumption_kw = Column(Numeric(6, 3))


class IngestionLog(Base):
    __tablename__ = "ingestion_log"

    id_log = Column(BigInteger, primary_key=True, autoincrement=True)
    id_chamber = Column(UUID(as_uuid=True), ForeignKey("chambers.id_chamber"))
    received_payload = Column(Text)
    processing_status = Column(String(20), nullable=False)  # success | error | pending
    error_message = Column(Text)
    reception_date = Column(DateTime(timezone=True), server_default=func.now())

class GeneratedAlert(Base):
    __tablename__ = "generated_alerts"

    id_alert = Column(BigInteger, primary_key=True, autoincrement=True)
    id_chamber = Column(UUID(as_uuid=True), ForeignKey("chambers.id_chamber"))
    # Sin FK porque ingesta no tiene los modelos Prediction ni HaccpRule
    id_prediction = Column(BigInteger)
    id_haccp_rule = Column(BigInteger)
    alert_type = Column(String(50))
    severity = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False, default="active")
    message = Column(Text)
    generation_date = Column(DateTime(timezone=True), server_default=func.now())
    id_user_acknowledged = Column(UUID(as_uuid=True), ForeignKey("users.id_user"))
    acknowledgment_date = Column(DateTime(timezone=True))
    id_user_resolved = Column(UUID(as_uuid=True), ForeignKey("users.id_user"))
    resolution_date = Column(DateTime(timezone=True))

    chamber = relationship("Chamber", lazy="joined")

    @property
    def chamber_name(self):
        return self.chamber.name if self.chamber else None


class AlertAudit(Base):
    __tablename__ = "alert_audit"

    id_audit = Column(BigInteger, primary_key=True, autoincrement=True)
    id_alert = Column(BigInteger, ForeignKey("generated_alerts.id_alert"))
    id_user = Column(UUID(as_uuid=True), ForeignKey("users.id_user"))
    action = Column(String(50))
    detail = Column(Text)
    action_date = Column(DateTime(timezone=True), server_default=func.now())

class HaccpRule(Base):
    __tablename__ = "haccp_rules"

    id_rule = Column(BigInteger, primary_key=True, autoincrement=True)
    id_chamber = Column(UUID(as_uuid=True), ForeignKey("chambers.id_chamber"))
    tolerance_time_min = Column(Integer)
    active = Column(Boolean, default=True)
    review_date = Column(DateTime(timezone=True), server_default=func.now())
    max_absolute_temp = Column(Numeric(5, 2))
    min_absolute_temp = Column(Numeric(5, 2))
    severity = Column(String(20), default="medium")
    id_user_modified = Column(UUID(as_uuid=True), ForeignKey("users.id_user"))


class SavingRecommendation(Base):
    __tablename__ = "saving_recommendation"

    id_recommendation = Column(BigInteger, primary_key=True, autoincrement=True)
    id_chamber = Column(UUID(as_uuid=True), ForeignKey("chambers.id_chamber"))
    id_price = Column(Integer, ForeignKey("energy_price.id_price"))
    action = Column(String(100))
    expected_saving_pct = Column(Numeric(6, 3))
    expected_saving_amount = Column(Numeric(14, 4))
    rationale = Column(Text)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    applied_at = Column(DateTime(timezone=True))