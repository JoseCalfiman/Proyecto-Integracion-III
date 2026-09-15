Responsable: Eduardo Dominguez

Microservicio que escucha los eventos de riesgo (alerta_tecnica) publicados en Redis, aplica las reglas HACCP definidas (por ejemplo, temperatura > 4°C por más de 2 minutos). Además, guarda un log de cada alerta en la base de datos.

## Reglas HACCP

La tabla `haccp_rules` mantiene una regla activa por cámara con estos campos:

| Campo | Uso | Valor por defecto |
| --- | --- | ---: |
| `rule_id` | Identificador de la regla | generado por la base de datos |
| `chamber_id` | Cámara a la que aplica | obligatorio |
| `absolute_max_temp` | Temperatura máxima absoluta (°C) | `4.00` |
| `absolute_min_temp` | Temperatura mínima absoluta (°C) | `-30.00` |
| `tolerance_time_min` | Tiempo tolerado fuera de rango | `15` minutos |
| `is_active` | Indica si la regla se aplica | `TRUE` |
| `created_at` | Fecha de creación | fecha actual |
| `modified_by_user_id` | Usuario que modificó la regla | `NULL` para reglas iniciales |

`create_default_rules_for_all_chambers(session)` inserta una regla por cada
cámara que todavía no tenga una regla. Es idempotente y conserva las reglas
existentes. La función debe ejecutarse después de que existan las cámaras y
las tablas `chambers`, `users` y `haccp_rules`.

`validar_haccp(alerta_predictiva, regla_camara)` devuelve `True` cuando la
temperatura prevista supera `absolute_max_temp` o cuando
`remaining_time_min` es menor que `tolerance_time_min`. La regla se recibe
como argumento para que cada cámara pueda tener límites diferentes.



├── worker-haccp/                  # Worker HACCP y Alertas (Eduardo)
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── main.py                    # Lógica principal (consumer Kafka)
│   │   ├── config.py                  # Configuración desde .env
│   │   ├── models.py                  # Modelos SQLAlchemy
│   │   ├── haccp_validator.py         # Validación de reglas HACCP
│   │   ├── kafka_consumer.py          # Consumidor de Kafka
│   │   ├── crud.py                    # Operaciones CRUD en base de datos
│   │   ├── tests/
│   │   │   ├── test_haccp.py
│   │   │   └── test_kafka.py
│   │   └── __init__.py

Arreglar:


================================================================================
2. LO QUE TE FALTA
================================================================================
 Ajustes al MER       -> Nombres de columnas en haccp_validator.py y crud.py
kafka_consumer.py    -> Suscrito a "sensor.anomaly"
kafka_producer.py    -> Publica en "haccp.alerts"
Guardar alertas      -> Insertar en "generated_alerts"
Guardar auditoría    -> Insertar en "alert_audit"
Dockerfile           -> Para levantar el worker en Docker
README.md            -> Documentación del módulo


================================================================================
3. MER OFICIAL
================================================================================

+-----------------------------+-----------------------------+
| EN TU CÓDIGO (mal)          | EN EL MER OFICIAL (bien)    |
+-----------------------------+-----------------------------+
| absolute_max_temp           | max_absolute_temp           |
| absolute_min_temp           | min_absolute_temp           |
| chamber_id                  | id_chamber                  |
| modified_by_user_id         | id_user_modified            |
| is_active                   | active                      |
| rule_id                     | id_rule                     |
+-----------------------------+-----------------------------+

--------------------------------------------------------------------------------
3.1. Ajustes en haccp_validator.py
--------------------------------------------------------------------------------

Cambiar en validar_haccp():

    # ANTES:
    if _get_value(regla_camara, "is_active") is False:
        return False
    absolute_max_temp = _get_value(regla_camara, "absolute_max_temp")

    # DESPUÉS:
    if _get_value(regla_camara, "active") is False:
        return False
    absolute_max_temp = _get_value(regla_camara, "max_absolute_temp")


Cambiar en _normalize_rule():

    # ANTES:
    if "absolute_max_temp" in rule:
        normalized["max_temp_c"] = float(rule["absolute_max_temp"])
    if "absolute_min_temp" in rule:
        normalized["min_temp_c"] = float(rule["absolute_min_temp"])

    # DESPUÉS:
    if "max_absolute_temp" in rule:
        normalized["max_temp_c"] = float(rule["max_absolute_temp"])
    if "min_absolute_temp" in rule:
        normalized["min_temp_c"] = float(rule["min_absolute_temp"])


--------------------------------------------------------------------------------
3.2. Ajustes en crud.py
--------------------------------------------------------------------------------

Cambiar DEFAULT_RULE_VALUES:

    # ANTES:
    DEFAULT_RULE_VALUES = {
        "absolute_max_temp": Decimal("4.00"),
        "absolute_min_temp": Decimal("-30.00"),
        "tolerance_time_min": 15,
        "is_active": True,
    }

    # DESPUÉS:
    DEFAULT_RULE_VALUES = {
        "max_absolute_temp": Decimal("4.00"),
        "min_absolute_temp": Decimal("-30.00"),
        "tolerance_time_min": 15,
        "active": True,
    }


Cambiar create_default_rules_for_all_chambers():

    # ANTES:
    chamber_ids = session.scalars(select(Chamber.chamber_id)).all()
    existing_ids = set(
        session.scalars(
            select(HaccpRule.chamber_id).where(HaccpRule.chamber_id.in_(chamber_ids))
        ).all()
    )
    new_rules = [
        HaccpRule(
            chamber_id=chamber_id,
            modified_by_user_id=modified_by_user_id,
            **DEFAULT_RULE_VALUES,
        )
        ...
    ]

    # DESPUÉS:
    chamber_ids = session.scalars(select(Chamber.id_chamber)).all()
    existing_ids = set(
        session.scalars(
            select(HaccpRule.id_chamber).where(HaccpRule.id_chamber.in_(chamber_ids))
        ).all()
    )
    new_rules = [
        HaccpRule(
            id_chamber=chamber_id,
            id_user_modified=modified_by_user_id,
            **DEFAULT_RULE_VALUES,
        )
        ...
    ]


Cambiar get_active_rule():

    # ANTES:
    return session.scalar(
        select(HaccpRule).where(
            HaccpRule.chamber_id == chamber_id,
            HaccpRule.is_active.is_(True),
        )
    )

    # DESPUÉS:
    return session.scalar(
        select(HaccpRule).where(
            HaccpRule.id_chamber == chamber_id,
            HaccpRule.active.is_(True),
        )
    )


--------------------------------------------------------------------------------
3.3. Ajustes en models.py
--------------------------------------------------------------------------------

Verificar que los modelos tengan los nombres del MER oficial:

    class HaccpRule(Base):
        __tablename__ = "haccp_rules"
        id_rule = Column(BigInteger, primary_key=True)
        id_chamber = Column(UUID, ForeignKey("chambers.id_chamber"))
        tolerance_time_min = Column(Integer)
        active = Column(Boolean, default=True)
        review_date = Column(DateTime(timezone=True))
        max_absolute_temp = Column(Numeric(5, 2))
        min_absolute_temp = Column(Numeric(5, 2))
        id_user_modified = Column(UUID, ForeignKey("users.id_user"))


    class GeneratedAlert(Base):
        __tablename__ = "generated_alerts"
        id_alert = Column(BigInteger, primary_key=True)
        id_chamber = Column(UUID, ForeignKey("chambers.id_chamber"))
        id_prediction = Column(BigInteger, ForeignKey("predictions.id_prediction"))
        id_haccp_rule = Column(BigInteger, ForeignKey("haccp_rules.id_rule"))
        alert_type = Column(String(50))
        severity = Column(String(20), nullable=False)
        status = Column(String(20), nullable=False, default="active")
        message = Column(Text)
        generation_date = Column(DateTime(timezone=True))
        id_user_acknowledged = Column(UUID, ForeignKey("users.id_user"))
        acknowledgment_date = Column(DateTime(timezone=True))
        id_user_resolved = Column(UUID, ForeignKey("users.id_user"))
        resolution_date = Column(DateTime(timezone=True))


    class AlertAudit(Base):
        __tablename__ = "alert_audit"
        id_audit = Column(BigInteger, primary_key=True)
        id_alert = Column(BigInteger, ForeignKey("generated_alerts.id_alert"))
        id_user = Column(UUID, ForeignKey("users.id_user"))
        action = Column(String(50))
        detail = Column(Text)
        action_date = Column(DateTime(timezone=True))


================================================================================
4. LO QUE DEBES CREAR
================================================================================


--------------------------------------------------------------------------------
4.1. kafka_consumer.py
--------------------------------------------------------------------------------

Debe:
- Suscribirse al tópico "sensor.anomaly"
- Por cada alerta predictiva:
    1. Consultar la regla HACCP de la cámara (con get_active_rule)
    2. Llamar a validar_haccp()
    3. Si cumple:
        a. Guardar la alerta en "generated_alerts"
        b. Publicar en "haccp.alerts"
        c. Guardar auditoría en "alert_audit"
    4. Si no cumple:
        - Registrar en logs como "falso positivo"

Estructura sugerida:

    import os
    import json
    import logging
    from confluent_kafka import Consumer, Producer, KafkaError
    from haccp_validator import validar_haccp
    from crud import get_active_rule
    from models import GeneratedAlert, AlertAudit

    TOPIC_ANOMALY = "sensor.anomaly"
    TOPIC_ALERTS = "haccp.alerts"
    GROUP_ID = "haccp-worker-group"
    BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")


--------------------------------------------------------------------------------
4.2. kafka_producer.py
--------------------------------------------------------------------------------

Debe:
- Publicar en el tópico "haccp.alerts"
- El payload debe incluir:
    {
        "id_chamber": "...",
        "id_prediction": ...,
        "alert_type": "haccp_violation",
        "severity": "critical|warning",
        "status": "active",
        "message": "...",
        "generation_date": "2026-09-14T10:30:00Z"
    }


--------------------------------------------------------------------------------
4.3. Dockerfile
--------------------------------------------------------------------------------

FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "kafka_consumer.py"]


--------------------------------------------------------------------------------
4.4. requirements.txt
--------------------------------------------------------------------------------

confluent-kafka==2.15.0
sqlalchemy==2.0.30
psycopg2-binary==2.9.9
python-dotenv==1.0.1


--------------------------------------------------------------------------------
4.5. README.md
--------------------------------------------------------------------------------

# Worker HACCP

Responsable: Eduardo Domínguez

Worker que consume alertas predictivas desde Kafka ("sensor.anomaly"),
las valida contra las reglas HACCP de cada cámara, y si cumplen, publica
una alerta final en "haccp.alerts" y la guarda en la tabla "generated_alerts".


================================================================================
5. FLUJO COMPLETO DEL WORKER HACCP
================================================================================

[Kafka: sensor.anomaly]
       ↓ (consume)
[kafka_consumer.py]
       ↓ (por cada alerta)
[get_active_rule(id_chamber)]
       ↓ (obtiene regla HACCP)
[validar_haccp(alerta, regla)]
       ↓
   ¿Cumple?
   ├── SÍ → [Guardar en generated_alerts]
   │         ↓
   │        [Publicar en haccp.alerts]
   │         ↓
   │        [Guardar en alert_audit]
   │
   └── NO → [Registrar log: "falso positivo"]




