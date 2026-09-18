import uuid
 
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    BigInteger,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship
 
Base = declarative_base()
 
 
# ==================================================================
# 1. Tablas de configuración
# ==================================================================
class Company(Base):
    __tablename__ = "company"
 
    id_company = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tax_id = Column(String(12), nullable=False, unique=True)
    name = Column(String(150))
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
 
    users = relationship("User", back_populates="company")
    chambers = relationship("Chamber", back_populates="company")
 
    def __repr__(self):
        return f"<Company id={self.id_company} name={self.name!r}>"
 
 
class Role(Base):
    __tablename__ = "roles"
 
    id_role = Column(Integer, primary_key=True, autoincrement=True)
    role_name = Column(String(30), nullable=False, unique=True)
 
    users = relationship("User", back_populates="role")
 
    def __repr__(self):
        return f"<Role id={self.id_role} name={self.role_name!r}>"
 
 
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
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
 
    company = relationship("Company", back_populates="users")
    role = relationship("Role", back_populates="users")
 
    def __repr__(self):
        return f"<User id={self.id_user} email={self.email!r}>"
 
 
class Chamber(Base):
    __tablename__ = "chambers"
 
    id_chamber = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    id_company = Column(UUID(as_uuid=True), ForeignKey("company.id_company"))
    name = Column(String(100))
    location = Column(String(200))
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
 
    company = relationship("Company", back_populates="chambers")
    sensors = relationship("Sensor", back_populates="chamber")
    sensor_data = relationship("SensorData", back_populates="chamber")
    ingestion_logs = relationship("IngestionLog", back_populates="chamber")
 
    def __repr__(self):
        return f"<Chamber id={self.id_chamber} name={self.name!r}>"
 
 
class Sensor(Base):
    __tablename__ = "sensors"
 
    id_sensor = Column(BigInteger, primary_key=True, autoincrement=True)
    id_chamber = Column(UUID(as_uuid=True), ForeignKey("chambers.id_chamber"))
    sensor_type = Column(String(50))
    mqtt_identifier = Column(String(100))
    model = Column(String(50))
    status = Column(String(20), default="active")
    installation_date = Column(DateTime(timezone=True), server_default=func.now())
 
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'inactive', 'maintenance')",
            name="ck_sensors_status",
        ),
    )
 
    chamber = relationship("Chamber", back_populates="sensors")
    sensor_data = relationship("SensorData", back_populates="sensor")
 
    def __repr__(self):
        return f"<Sensor id={self.id_sensor} type={self.sensor_type!r}>"
 
 
# ==================================================================
# 2. Series de tiempo (TimescaleDB) - tabla principal de lecturas
# ==================================================================
class SensorData(Base):
    __tablename__ = "sensor_data"
 
    # En una hipertabla TimescaleDB, la PK compuesta (id_data, timestamp)
    # es requerida porque la partición se hace sobre la columna de tiempo.
    id_data = Column(BigInteger, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), primary_key=True, nullable=False)
    id_chamber = Column(UUID(as_uuid=True), ForeignKey("chambers.id_chamber"))
    id_sensor = Column(BigInteger, ForeignKey("sensors.id_sensor"))
    insertion_date = Column(DateTime(timezone=True), server_default=func.now())
    temperature = Column(Numeric(5, 2))
    consumption_kw = Column(Numeric(6, 3))
 
    chamber = relationship("Chamber", back_populates="sensor_data")
    sensor = relationship("Sensor", back_populates="sensor_data")
 
    def __repr__(self):
        return (
            f"<SensorData id={self.id_data} chamber={self.id_chamber} "
            f"ts={self.timestamp} temp={self.temperature}>"
        )
 
 
# ==================================================================
# 10. Log de ingesta
# ==================================================================
class IngestionLog(Base):
    __tablename__ = "ingestion_log"
 
    id_log = Column(BigInteger, primary_key=True, autoincrement=True)
    id_chamber = Column(UUID(as_uuid=True), ForeignKey("chambers.id_chamber"))
    received_payload = Column(Text)
    processing_status = Column(String(20), nullable=False)
    error_message = Column(Text)
    reception_date = Column(DateTime(timezone=True), server_default=func.now())
 
    __table_args__ = (
        CheckConstraint(
            "processing_status IN ('success', 'error', 'pending')",
            name="ck_ingestion_log_status",
        ),
    )
 
    chamber = relationship("Chamber", back_populates="ingestion_logs")
 
    def __repr__(self):
        return (
            f"<IngestionLog id={self.id_log} chamber={self.id_chamber} "
            f"status={self.processing_status!r}>"
        )
 
