import json
import time
import logging
import threading
from collections import defaultdict, deque
from confluent_kafka import Consumer, Producer, KafkaError
from http.server import HTTPServer, BaseHTTPRequestHandler

from config import (
    BOOTSTRAP_SERVERS, GROUP_ID, AUTO_OFFSET_RESET,
    TOPIC_RAW, TOPIC_ANOMALY, LIMITE_HACCP_DEFAULT,
    VENTANA_MINUTOS, MAX_MEDICIONES_VENTANA, UMBRAL_ALERTA_MINUTOS, SEVERITY_DEFAULT,
)
from contract import ContractError, parse_sensor_reading
from predictor import evaluar_riesgo
from window import actualizar_ventana
from db import get_session
from haccp_predictions import obtener_regla_haccp_activa, guardar_prediccion

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

RISK_LEVEL_DB = {
    "SIN_RIESGO": "low",
    "BAJO": "low",
    "MEDIO": "medium",
    "ALTO": "high",
    "CRITICO": "critical",
    "CRÍTICO": "critical",
}

def mapear_risk_level(nivel_riesgo):
    """Convierte el nivel interno del predictor al vocabulario del CHECK de la tabla predictions."""
    nivel = RISK_LEVEL_DB.get(str(nivel_riesgo).upper())
    if nivel is None:
        logging.warning(f"Nivel de riesgo desconocido '{nivel_riesgo}', se guarda como 'low'")
        return "low"
    return nivel

class PredictiveKafkaWorker:
    def __init__(self):
        consumer_conf = {
            'bootstrap.servers': BOOTSTRAP_SERVERS,
            'group.id': GROUP_ID,
            'auto.offset.reset': AUTO_OFFSET_RESET,
        }
        self.consumer = Consumer(consumer_conf)

        producer_conf = {'bootstrap.servers': BOOTSTRAP_SERVERS}
        self.producer = Producer(producer_conf)

        self.buffers = defaultdict(lambda: deque(maxlen=MAX_MEDICIONES_VENTANA))

    def delivery_report(self, err, msg):
        if err is not None:
            logging.error(f"Error al entregar mensaje: {err}")
        else:
            logging.info(f"Alerta publicada en {msg.topic()} [{msg.partition()}]")

    def send_anomaly_alert(self, alert_payload):
        self.producer.produce(
            TOPIC_ANOMALY,
            key=str(alert_payload.get("id_chamber")),
            value=json.dumps(alert_payload),
            callback=self.delivery_report,
        )
        self.producer.flush()

    def _actualizar_buffer(self, id_chamber, timestamp, temperature):
        buffer = self.buffers[id_chamber]
        agregado = actualizar_ventana(buffer, timestamp, temperature, VENTANA_MINUTOS)
        return buffer, agregado

    def _procesar_mensaje(self, msg):
        try:
            data = json.loads(msg.value().decode("utf-8"))
            lectura = parse_sensor_reading(data)
        except (ValueError, UnicodeDecodeError, ContractError) as e:
            logging.warning(f"Mensaje descartado en {msg.topic()} [{msg.partition()}]: {e}")
            return

        id_chamber = lectura.id_chamber
        timestamp = lectura.timestamp
        temperature = lectura.temperature
        logging.debug(f"Lectura recibida: {lectura}")

        buffer, agregado = self._actualizar_buffer(id_chamber, timestamp, temperature)
        if not agregado:
            logging.debug(f"[{id_chamber}] lectura repetida o desordenada, se ignora")
            return

        with get_session() as session:
            regla = obtener_regla_haccp_activa(session, chamber_id=id_chamber)

            if regla is not None:
                absolute_max_temp = regla["max_absolute_temp"]
                umbral_alerta = (
                    regla["tolerance_time_min"]
                    if regla["tolerance_time_min"] is not None
                    else UMBRAL_ALERTA_MINUTOS
                )
                severity = regla["severity"]
            else:
                logging.warning(
                    f"Sin regla HACCP activa para id_chamber={id_chamber}; "
                    f"usando valores por defecto de config.py"
                )
                absolute_max_temp = LIMITE_HACCP_DEFAULT
                umbral_alerta = UMBRAL_ALERTA_MINUTOS
                severity = SEVERITY_DEFAULT

            resultado = evaluar_riesgo(
                buffer=list(buffer),
                absolute_max_temp=absolute_max_temp,
                umbral_alerta_minutos=umbral_alerta,
            )

            logging.info(
                f"[{id_chamber}] pendiente={resultado['pendiente_por_minuto']} "
                f"tiempo_restante_min={resultado['tiempo_restante_min']} "
                f"nivel_riesgo={resultado['nivel_riesgo']}"
            )
            projected_temperature = (
                absolute_max_temp
                if resultado["tiempo_restante_min"] is not None
                else None
            )

            try:
                guardar_prediccion(
                    session,
                    chamber_id=id_chamber,
                    calculated_slope=resultado["pendiente_por_minuto"],
                    projected_temperature=projected_temperature,
                    remaining_time_min=resultado["tiempo_restante_min"],
                    risk_level=mapear_risk_level(resultado["nivel_riesgo"]),
                )
            except Exception:
                logging.exception(f"No se pudo guardar la predicción para {id_chamber}")
                session.rollback()

        if resultado["hay_riesgo"]:
            alert_payload = {
                "id_chamber": id_chamber,
                "remaining_time_min": resultado["tiempo_restante_min"],
                "temperature": temperature,
                "severity": severity,
                "risk_level": resultado["nivel_riesgo"],
                "slope_per_minute": resultado["pendiente_por_minuto"],
                "recorded_at": timestamp.isoformat(),
            }
            self.send_anomaly_alert(alert_payload)

    def start_listening(self):
        self.consumer.subscribe([TOPIC_RAW])
        logging.info(f"Escuchando '{TOPIC_RAW}' con el grupo '{GROUP_ID}'...")

        try:
            while True:
                msg = self.consumer.poll(timeout=1.0)
                if msg is None:
                    continue
                if msg.error():
                    if msg.error().code() in (KafkaError._PARTITION_EOF, KafkaError.UNKNOWN_TOPIC_OR_PART):
                        continue
                    logging.error(f"Error de Kafka: {msg.error()}")
                    continue

                try:
                    self._procesar_mensaje(msg)
                except Exception:
                    logging.exception("Error procesando mensaje; se continúa con el siguiente")

        except KeyboardInterrupt:
            logging.info("Deteniendo el consumidor...")
        finally:
            self.consumer.close()