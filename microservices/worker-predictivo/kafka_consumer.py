import json
import logging
from collections import defaultdict, deque
from datetime import datetime, timedelta
from confluent_kafka import Consumer, Producer, KafkaError
from config import (
    BOOTSTRAP_SERVERS, GROUP_ID, AUTO_OFFSET_RESET,
    TOPIC_RAW, TOPIC_ANOMALY, LIMITE_HACCP_DEFAULT,
    VENTANA_MINUTOS, UMBRAL_ALERTA_MINUTOS,
)
from predictor import evaluar_riesgo
from db import get_session
from haccp_predictions import obtener_regla_haccp_activa, guardar_prediccion

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

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

        self.buffers = defaultdict(deque)

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

    def _parse_timestamp(self, raw_timestamp):
        if isinstance(raw_timestamp, (int, float)):
            return datetime.fromtimestamp(raw_timestamp)
        return datetime.fromisoformat(raw_timestamp.replace("Z", "+00:00"))

    def _actualizar_buffer(self, id_chamber, timestamp, temperature):
        buffer = self.buffers[id_chamber]
        buffer.append({"timestamp": timestamp, "temperature": temperature})

        limite_inferior = timestamp - timedelta(minutes=VENTANA_MINUTOS)
        while buffer and buffer[0]["timestamp"] < limite_inferior:
            buffer.popleft()

        return buffer

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

                data = json.loads(msg.value().decode('utf-8'))
                logging.info(f"Datos recibidos: {data}")

                id_chamber = data.get("id_chamber")
                timestamp = self._parse_timestamp(data.get("timestamp"))
                temperature = data.get("temperature")

                buffer = self._actualizar_buffer(id_chamber, timestamp, temperature)

                with get_session() as session:
                    regla = obtener_regla_haccp_activa(session, chamber_id=id_chamber)

                    if regla is not None:
                        absolute_max_temp = regla["max_absolute_temp"]
                        umbral_alerta = (
                            regla["tolerance_time_min"]
                            if regla["tolerance_time_min"] is not None
                            else UMBRAL_ALERTA_MINUTOS
                        )
                    else:
                        logging.warning(
                            f"Sin regla HACCP activa para id_chamber={id_chamber}; "
                            f"usando valores por defecto de config.py"
                        )
                        absolute_max_temp = LIMITE_HACCP_DEFAULT
                        umbral_alerta = UMBRAL_ALERTA_MINUTOS

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
                            risk_level=resultado["nivel_riesgo"],
                        )
                    except Exception:
                        logging.exception(
                            f"No se pudo guardar la predicción para {id_chamber}"
                        )
                        session.rollback()

                if resultado["hay_riesgo"]:
                    alert_payload = {
                        "id_chamber": id_chamber,
                        "current_temperature": temperature,
                        "slope_per_minute": resultado["pendiente_por_minuto"],
                        "remaining_time_min": resultado["tiempo_restante_min"],
                        "recorded_at": timestamp.isoformat(),
                    }
                    self.send_anomaly_alert(alert_payload)

        except KeyboardInterrupt:
            logging.info("Deteniendo el consumidor...")
        finally:
            self.consumer.close()


if __name__ == "__main__":
    from db import crear_tablas

    crear_tablas()
    worker = PredictiveKafkaWorker()
    worker.start_listening()