import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

import sqlalchemy as sa
from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Empresa
# ---------------------------------------------------------------------------
class Empresa(Base):
    __tablename__ = "empresa"

    id_empresa: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    rut: Mapped[str] = mapped_column(String(12), nullable=False, unique=True)
    nombre: Mapped[Optional[str]] = mapped_column(String(150))
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=sa.true())
    created_at: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    usuarios: Mapped[List["Usuario"]] = relationship(back_populates="empresa")
    camaras: Mapped[List["Camara"]] = relationship(back_populates="empresa")
    reportes: Mapped[List["Reporte"]] = relationship(back_populates="empresa")


# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------
class Rol(Base):
    __tablename__ = "roles"

    id_rol: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre_rol: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)

    usuarios: Mapped[List["Usuario"]] = relationship(back_populates="rol")


# ---------------------------------------------------------------------------
# Usuarios
# ---------------------------------------------------------------------------
class Usuario(Base):
    __tablename__ = "usuarios"

    id_usuario: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    id_empresa: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("empresa.id_empresa", ondelete="CASCADE")
    )
    id_rol: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("roles.id_rol", ondelete="RESTRICT"))
    email: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255))
    nombre: Mapped[Optional[str]] = mapped_column(String(100))
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=sa.true())
    created_at: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    empresa: Mapped[Optional["Empresa"]] = relationship(back_populates="usuarios")
    rol: Mapped[Optional["Rol"]] = relationship(back_populates="usuarios")

    conversaciones: Mapped[List["Conversacion"]] = relationship(back_populates="usuario")
    reportes: Mapped[List["Reporte"]] = relationship(back_populates="usuario")
    auditorias: Mapped[List["AuditoriaAlerta"]] = relationship(back_populates="usuario")
    tokens_revocados: Mapped[List["TokenRevocado"]] = relationship(back_populates="usuario")

    alertas_reconocidas: Mapped[List["AlertaGenerada"]] = relationship(
        back_populates="usuario_reconocio",
        foreign_keys="AlertaGenerada.id_usuario_reconocio",
    )
    alertas_resueltas: Mapped[List["AlertaGenerada"]] = relationship(
        back_populates="usuario_resolvio",
        foreign_keys="AlertaGenerada.id_usuario_resolvio",
    )


class TokenRevocado(Base):
    __tablename__ = "tokens_revocados"

    id_token: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    id_usuario: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id_usuario", ondelete="CASCADE")
    )
    token_jti: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    fecha_revocacion: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True), server_default=func.now())
    fecha_expiracion_original: Mapped[Optional[datetime]] = mapped_column(sa.TIMESTAMP(timezone=True))

    usuario: Mapped[Optional["Usuario"]] = relationship(back_populates="tokens_revocados")


# ---------------------------------------------------------------------------
# Camaras (cámaras de frío / almacenamiento)
# ---------------------------------------------------------------------------
class Camara(Base):
    __tablename__ = "camaras"

    id_camara: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    id_empresa: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("empresa.id_empresa", ondelete="CASCADE")
    )
    nombre: Mapped[Optional[str]] = mapped_column(String(100))
    ubicacion: Mapped[Optional[str]] = mapped_column(String(200))
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=sa.true())
    created_at: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    empresa: Mapped[Optional["Empresa"]] = relationship(back_populates="camaras")

    conversaciones: Mapped[List["Conversacion"]] = relationship(back_populates="camara")
    logs_ingesta: Mapped[List["LogIngesta"]] = relationship(back_populates="camara")
    alertas: Mapped[List["AlertaGenerada"]] = relationship(back_populates="camara")
    sensores: Mapped[List["Sensor"]] = relationship(back_populates="camara")
    consumos_predichos: Mapped[List["ConsumoPredicho"]] = relationship(back_populates="camara")
    reglas_haccp: Mapped[List["ReglaHaccp"]] = relationship(back_populates="camara")
    recomendaciones_ahorro: Mapped[List["SavingRecommendation"]] = relationship(back_populates="camara")
    predicciones: Mapped[List["Prediccion"]] = relationship(back_populates="camara")
    datos_sensor: Mapped[List["SensorData"]] = relationship(back_populates="camara")


# ---------------------------------------------------------------------------
# Conversaciones / Mensajes IA
# ---------------------------------------------------------------------------
class Conversacion(Base):
    __tablename__ = "conversaciones"

    id_conversacion: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    id_usuario: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id_usuario", ondelete="CASCADE")
    )
    id_camara: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("camaras.id_camara", ondelete="CASCADE")
    )
    fecha_inicio: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True), server_default=func.now())
    fecha_ultima_actividad: Mapped[datetime] = mapped_column(
        sa.TIMESTAMP(timezone=True), server_default=func.now()
    )
    fecha_terminada: Mapped[Optional[datetime]] = mapped_column(sa.TIMESTAMP(timezone=True))

    usuario: Mapped[Optional["Usuario"]] = relationship(back_populates="conversaciones")
    camara: Mapped[Optional["Camara"]] = relationship(back_populates="conversaciones")
    mensajes: Mapped[List["MensajeIA"]] = relationship(back_populates="conversacion")


class MensajeIA(Base):
    __tablename__ = "mensajes_ia"
    __table_args__ = (
        CheckConstraint("remitente IN ('usuario', 'asistente', 'sistema')", name="ck_mensajes_ia_remitente"),
    )

    id_mensaje: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    id_conversacion: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("conversaciones.id_conversacion", ondelete="CASCADE")
    )
    remitente: Mapped[str] = mapped_column(String(20), nullable=False)
    contenido: Mapped[Optional[str]] = mapped_column(Text)
    fecha_envio: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True), server_default=func.now())

    conversacion: Mapped[Optional["Conversacion"]] = relationship(back_populates="mensajes")


# ---------------------------------------------------------------------------
# Reportes
# ---------------------------------------------------------------------------
class Reporte(Base):
    __tablename__ = "reportes"

    id_reporte: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    id_empresa: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("empresa.id_empresa", ondelete="CASCADE")
    )
    id_usuario: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id_usuario", ondelete="SET NULL")
    )
    tipo_reporte: Mapped[Optional[str]] = mapped_column(String(50))
    formato: Mapped[Optional[str]] = mapped_column(String(20))
    fecha_inicio_rango: Mapped[Optional[date]] = mapped_column(Date)
    fecha_fin_rango: Mapped[Optional[date]] = mapped_column(Date)
    ruta_archivo: Mapped[Optional[str]] = mapped_column(String(255))
    fecha_generacion: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True), server_default=func.now())

    empresa: Mapped[Optional["Empresa"]] = relationship(back_populates="reportes")
    usuario: Mapped[Optional["Usuario"]] = relationship(back_populates="reportes")


# ---------------------------------------------------------------------------
# Ingesta / Sensores
# ---------------------------------------------------------------------------
class LogIngesta(Base):
    __tablename__ = "log_ingesta"
    __table_args__ = (
        CheckConstraint(
            "estado_procesamiento IN ('recibido', 'procesado', 'error', 'descartado')",
            name="ck_log_ingesta_estado",
        ),
    )

    id_log: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    id_camara: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("camaras.id_camara", ondelete="CASCADE")
    )
    payload_recibido: Mapped[Optional[str]] = mapped_column(Text)
    estado_procesamiento: Mapped[str] = mapped_column(String(20), nullable=False)
    mensaje_error: Mapped[Optional[str]] = mapped_column(Text)
    fecha_recepcion: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True), server_default=func.now())

    camara: Mapped[Optional["Camara"]] = relationship(back_populates="logs_ingesta")


class Sensor(Base):
    __tablename__ = "sensores"
    __table_args__ = (
        CheckConstraint("estado IN ('activo', 'inactivo', 'mantenimiento', 'averiado')", name="ck_sensores_estado"),
    )

    id_sensor: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    id_camara: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("camaras.id_camara", ondelete="CASCADE")
    )
    tipo_sensor: Mapped[Optional[str]] = mapped_column(String(50))
    identificador_mqtt: Mapped[Optional[str]] = mapped_column(String(100))
    modelo: Mapped[Optional[str]] = mapped_column(String(50))
    estado: Mapped[str] = mapped_column(String(20), nullable=False, server_default="activo")
    fecha_instalacion: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True), server_default=func.now())

    camara: Mapped[Optional["Camara"]] = relationship(back_populates="sensores")
    datos: Mapped[List["SensorData"]] = relationship(back_populates="sensor")


class SensorData(Base):
    """
    Tabla pensada como hypertable de TimescaleDB.
    PK compuesta (timestamp, id_dato) porque Timescale exige que la columna
    de tiempo particione/forme parte de la clave.
    """

    __tablename__ = "sensor_data"

    timestamp: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True), primary_key=True)
    id_dato: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    id_camara: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("camaras.id_camara", ondelete="CASCADE")
    )
    id_sensor: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("sensores.id_sensor", ondelete="CASCADE")
    )
    fecha_insercion: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True), server_default=func.now())
    temperatura: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    consumo_kw: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 3))

    camara: Mapped[Optional["Camara"]] = relationship(back_populates="datos_sensor")
    sensor: Mapped[Optional["Sensor"]] = relationship(back_populates="datos")


# ---------------------------------------------------------------------------
# Predicciones / Alertas / HACCP
# ---------------------------------------------------------------------------
class Prediccion(Base):
    __tablename__ = "predicciones"
    __table_args__ = (
        CheckConstraint("nivel_riesgo IN ('bajo', 'medio', 'alto', 'critico')", name="ck_predicciones_nivel_riesgo"),
    )

    id_prediccion: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    id_camara: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("camaras.id_camara", ondelete="CASCADE")
    )
    pendiente_calculada: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))
    temperatura_proyectada: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    tiempo_restante_min: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2))
    nivel_riesgo: Mapped[str] = mapped_column(String(20), nullable=False)
    fecha_calculo: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True), server_default=func.now())
    id_worker: Mapped[Optional[str]] = mapped_column(String(50))

    camara: Mapped[Optional["Camara"]] = relationship(back_populates="predicciones")
    alertas: Mapped[List["AlertaGenerada"]] = relationship(back_populates="prediccion")


class ReglaHaccp(Base):
    __tablename__ = "reglas_haccp"

    id_regla: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    id_camara: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("camaras.id_camara", ondelete="CASCADE")
    )
    tiempo_tolerancia_min: Mapped[Optional[int]] = mapped_column(Integer)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=sa.true())
    fecha_revision: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True), server_default=func.now())
    temp_max_absoluta: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    temp_min_absoluta: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))

    camara: Mapped[Optional["Camara"]] = relationship(back_populates="reglas_haccp")
    alertas: Mapped[List["AlertaGenerada"]] = relationship(back_populates="regla_haccp")


class AlertaGenerada(Base):
    __tablename__ = "alertas_generadas"
    __table_args__ = (
        CheckConstraint("severidad IN ('baja', 'media', 'alta', 'critica')", name="ck_alertas_severidad"),
        CheckConstraint(
            "estado IN ('activa', 'reconocida', 'resuelta', 'descartada')", name="ck_alertas_estado"
        ),
    )

    id_alerta: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    id_camara: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("camaras.id_camara", ondelete="CASCADE")
    )
    id_prediccion: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("predicciones.id_prediccion", ondelete="SET NULL")
    )
    id_regla_haccp: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("reglas_haccp.id_regla", ondelete="SET NULL")
    )
    tipo_alerta: Mapped[Optional[str]] = mapped_column(String(50))
    severidad: Mapped[str] = mapped_column(String(20), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, server_default="activa")
    mensaje: Mapped[Optional[str]] = mapped_column(Text)
    fecha_generacion: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True), server_default=func.now())
    id_usuario_reconocio: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id_usuario", ondelete="SET NULL")
    )
    fecha_reconocimiento: Mapped[Optional[datetime]] = mapped_column(sa.TIMESTAMP(timezone=True))
    id_usuario_resolvio: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id_usuario", ondelete="SET NULL")
    )
    fecha_resolucion: Mapped[Optional[datetime]] = mapped_column(sa.TIMESTAMP(timezone=True))

    camara: Mapped[Optional["Camara"]] = relationship(back_populates="alertas")
    prediccion: Mapped[Optional["Prediccion"]] = relationship(back_populates="alertas")
    regla_haccp: Mapped[Optional["ReglaHaccp"]] = relationship(back_populates="alertas")
    usuario_reconocio: Mapped[Optional["Usuario"]] = relationship(
        back_populates="alertas_reconocidas", foreign_keys=[id_usuario_reconocio]
    )
    usuario_resolvio: Mapped[Optional["Usuario"]] = relationship(
        back_populates="alertas_resueltas", foreign_keys=[id_usuario_resolvio]
    )
    auditorias: Mapped[List["AuditoriaAlerta"]] = relationship(back_populates="alerta")


class AuditoriaAlerta(Base):
    __tablename__ = "auditoria_alertas"

    id_auditoria: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    id_alerta: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("alertas_generadas.id_alerta", ondelete="CASCADE")
    )
    id_usuario: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("usuarios.id_usuario", ondelete="SET NULL")
    )
    accion: Mapped[Optional[str]] = mapped_column(String(50))
    detalle: Mapped[Optional[str]] = mapped_column(Text)
    fecha_accion: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True), server_default=func.now())

    alerta: Mapped[Optional["AlertaGenerada"]] = relationship(back_populates="auditorias")
    usuario: Mapped[Optional["Usuario"]] = relationship(back_populates="auditorias")


# ---------------------------------------------------------------------------
# Energía / Ahorro
# ---------------------------------------------------------------------------
class PrecioEnergia(Base):
    __tablename__ = "precio_energia"

    id_precio: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    precio_kwh: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    fuente: Mapped[Optional[str]] = mapped_column(String(100))
    fecha_consulta: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True), server_default=func.now())

    recomendaciones: Mapped[List["SavingRecommendation"]] = relationship(back_populates="precio")


class ConsumoPredicho(Base):
    __tablename__ = "consumo_predicho"

    id_prediccion_consumo: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    id_camara: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("camaras.id_camara", ondelete="CASCADE")
    )
    fecha_prediccion: Mapped[Optional[date]] = mapped_column(Date)
    consumo_predicho_kw: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 3))
    fecha_generacion: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True), server_default=func.now())

    camara: Mapped[Optional["Camara"]] = relationship(back_populates="consumos_predichos")


class SavingRecommendation(Base):
    __tablename__ = "saving_recommendation"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pendiente', 'aplicada', 'descartada', 'expirada')", name="ck_saving_recommendation_status"
        ),
    )

    id_recomendacion: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    id_camara: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("camaras.id_camara", ondelete="CASCADE")
    )
    id_precio: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("precio_energia.id_precio", ondelete="SET NULL")
    )
    action: Mapped[Optional[str]] = mapped_column(String(100))
    expected_saving_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 3))
    expected_saving_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 4))
    rationale: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="pendiente")
    created_at: Mapped[datetime] = mapped_column(sa.TIMESTAMP(timezone=True), server_default=func.now())
    applied_at: Mapped[Optional[datetime]] = mapped_column(sa.TIMESTAMP(timezone=True))

    camara: Mapped[Optional["Camara"]] = relationship(back_populates="recomendaciones_ahorro")
    precio: Mapped[Optional["PrecioEnergia"]] = relationship(back_populates="recomendaciones")