
import json
import logging
import os
import signal
import sys
import time
from typing import Optional, Tuple
 
import paho.mqtt.client as mqtt
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
 
from models import Base, Chamber, IngestionLog, SensorData
from schemas import SensorDataCreate
 
# ==================================================================
# Configuración (vía variables de entorno, con defaults razonables)
# ==================================================================
MQTT_BROKER_HOST = os.getenv("MQTT_BROKER_HOST", "localhost")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "sensor/raw")
MQTT_QOS = int(os.getenv("MQTT_QOS", "1"))
MQTT_CLIENT_ID = os.getenv("MQTT_CLIENT_ID", "smart-fridge-backend")
MQTT_USERNAME = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")
MQTT_KEEPALIVE = int(os.getenv("MQTT_KEEPALIVE", "60"))
 
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+psycopg2://user:password@localhost:5432/mer"
)
 
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("mqtt_client")
 
# ==================================================================
# Sesión de base de datos
# ==================================================================
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
 
 
def get_db_session() -> Session:
    """Crea una sesión de DB nueva. Cada mensaje MQTT abre/cierra la suya
    para no compartir estado entre hilos (paho-mqtt corre en su propio
    thread vía loop_start())."""
    return SessionLocal()
 
 
# ==================================================================
# Parseo y validación del payload
# ==================================================================
def parse_and_validate(raw_payload: bytes) -> Tuple[Optional[SensorDataCreate], Optional[str]]:
    """
    Decodifica el payload MQTT (bytes -> JSON) y lo valida contra
    SensorDataCreate.
 
    Retorna (datos_validados, None) si todo está OK,
    o (None, mensaje_de_error) si falla el parseo o la validación.
    """
    try:
        decoded = raw_payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        return None, f"Payload no es UTF-8 válido: {exc}"
 
    try:
        payload_dict = json.loads(decoded)
    except json.JSONDecodeError as exc:
        return None, f"Payload no es JSON válido: {exc}"
 
    if not isinstance(payload_dict, dict):
        return None, "El payload JSON debe ser un objeto (dict)"
 
    try:
        validated = SensorDataCreate(**payload_dict)
    except ValidationError as exc:
        return None, f"Validación fallida: {exc.errors()}"
 
    return validated, None
 
 
# ==================================================================
# Persistencia
# ==================================================================
def persist_reading(db: Session, validated: SensorDataCreate, raw_payload: str) -> None:
    """Guarda la lectura válida en sensor_data y deja constancia en
    ingestion_log con status='success'. Si la cámara no existe, se
    registra el error en ingestion_log en vez de insertar la lectura."""
 
    chamber_exists = (
        db.query(Chamber.id_chamber)
        .filter(Chamber.id_chamber == validated.chamber_id)
        .first()
        is not None
    )
    if not chamber_exists:
        persist_error(
            db,
            raw_payload,
            f"chamber_id {validated.chamber_id} no existe en la base de datos",
        )
        return
 
    reading = SensorData(
        id_chamber=validated.chamber_id,
        timestamp=validated.recorded_at,
        temperature=validated.temperature,
        consumption_kw=validated.consumption_kw,
    )
    db.add(reading)
 
    db.add(
        IngestionLog(
            id_chamber=validated.chamber_id,
            received_payload=raw_payload,
            processing_status="success",
            error_message=None,
        )
    )
    db.commit()
    logger.info(
        "Lectura guardada: chamber=%s temp=%s consumo=%s",
        validated.chamber_id,
        validated.temperature,
        validated.consumption_kw,
    )
 
 
def persist_error(db: Session, raw_payload: str, error_message: str) -> None:
    """Registra en ingestion_log un mensaje que no pudo procesarse."""
    db.add(
        IngestionLog(
            id_chamber=None,
            received_payload=raw_payload,
            processing_status="error",
            error_message=error_message,
        )
    )
    db.commit()
    logger.warning("Mensaje descartado: %s", error_message)
 
 
# ==================================================================
# Callbacks de paho-mqtt
# ==================================================================
def on_connect(client: mqtt.Client, userdata, connect_flags, reason_code, properties=None):
    """Se ejecuta al (re)conectar con el broker. Suscribe al tópico."""
    if reason_code == 0:
        logger.info("Conectado al broker MQTT %s:%s", MQTT_BROKER_HOST, MQTT_BROKER_PORT)
        client.subscribe(MQTT_TOPIC, qos=MQTT_QOS)
        logger.info("Suscrito al tópico '%s' (QoS=%s)", MQTT_TOPIC, MQTT_QOS)
    else:
        logger.error("Fallo al conectar al broker MQTT: %s", reason_code)
 
 
def on_disconnect(client: mqtt.Client, userdata, disconnect_flags, reason_code, properties=None):
    """Se ejecuta al desconectarse. paho-mqtt reintenta solo si
    reconnect_on_failure=True (default) y la desconexión no fue manual."""
    if reason_code != 0:
        logger.warning("Desconexión inesperada del broker MQTT (code=%s)", reason_code)
    else:
        logger.info("Desconectado del broker MQTT")
 
 
def on_message(client: mqtt.Client, userdata, msg: mqtt.MQTTMessage):
    """
    Callback principal: procesa cada mensaje recibido en 'sensor/raw'.
 
    1. Parsea y valida el payload.
    2. Si es válido -> persiste en sensor_data + ingestion_log(success).
    3. Si no es válido -> persiste solo en ingestion_log(error).
    """
    raw_payload_str = msg.payload.decode("utf-8", errors="replace")
    logger.debug("Mensaje recibido en '%s': %s", msg.topic, raw_payload_str)
 
    validated, error_message = parse_and_validate(msg.payload)
 
    db = get_db_session()
    try:
        if validated is not None:
            persist_reading(db, validated, raw_payload_str)
        else:
            persist_error(db, raw_payload_str, error_message)
    except Exception:
        db.rollback()
        logger.exception("Error inesperado procesando mensaje MQTT")
    finally:
        db.close()
 
 
# ==================================================================
# Ciclo de vida del cliente MQTT
# ==================================================================
def build_mqtt_client() -> mqtt.Client:
    """Crea y configura (sin conectar) el cliente MQTT."""
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=MQTT_CLIENT_ID,
    )
 
    if MQTT_USERNAME:
        client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
 
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message
 
    return client
 
 
def start_mqtt() -> mqtt.Client:
    """
    Conecta al broker y arranca el loop de red en un thread en segundo
    plano (no bloqueante). Pensada para llamarse desde el evento de
    'startup' de FastAPI.
 
    Retorna el cliente, para poder detenerlo luego con stop_mqtt().
    """
    client = build_mqtt_client()
    client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, keepalive=MQTT_KEEPALIVE)
    client.loop_start()
    logger.info("Cliente MQTT iniciado (loop en background)")
    return client
 
 
def stop_mqtt(client: mqtt.Client) -> None:
    """Detiene el loop y desconecta limpiamente. Pensada para llamarse
    desde el evento de 'shutdown' de FastAPI."""
    client.loop_stop()
    client.disconnect()
    logger.info("Cliente MQTT detenido")
 
 
# ==================================================================
# Ejemplo de integración con FastAPI (referencia, no se ejecuta acá)
# ==================================================================
"""
# main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from mqtt_client import start_mqtt, stop_mqtt
 
@asynccontextmanager
async def lifespan(app: FastAPI):
    mqtt_client = start_mqtt()      # startup: arranca suscripción activa
    yield
    stop_mqtt(mqtt_client)          # shutdown: cierra conexión
 
app = FastAPI(lifespan=lifespan)
"""
 
 
# ==================================================================
# Ejecución standalone (sin FastAPI) - útil para pruebas manuales
# ==================================================================
def _run_standalone() -> None:
    client = start_mqtt()
 
    def _handle_sigterm(signum, frame):
        logger.info("Señal de apagado recibida, cerrando...")
        stop_mqtt(client)
        sys.exit(0)
 
    signal.signal(signal.SIGINT, _handle_sigterm)
    signal.signal(signal.SIGTERM, _handle_sigterm)
 
    logger.info("Escuchando '%s' en %s:%s. Ctrl+C para salir.", MQTT_TOPIC, MQTT_BROKER_HOST, MQTT_BROKER_PORT)
    while True:
        time.sleep(1)
 
 
if __name__ == "__main__":
    _run_standalone()
