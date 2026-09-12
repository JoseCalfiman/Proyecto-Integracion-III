import json
import logging
from collections import defaultdict, deque
from datetime import datetime, timedelta
from confluent_kafka import Consumer, Producer, KafkaError
from config import BOOTSTRAP_SERVERS, GROUP_ID, AUTO_OFFSET_RESET, TOPIC_RAW, TOPIC_ANOMALY
from predictor import evaluar_riesgo

LIMITE_HACCP_DEFAULT = -10.0

# Ventana de análisis
VENTANA_MINUTOS = 5

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class PredictiveKafkaWorker:
    def __init__(self):
        consumer_conf = {
            'bootstrap.servers': BOOTSTRAP_SERVERS,
            'group.id': GROUP_ID,
            'auto.offset.reset': AUTO_OFFSET_RESET
        }
        self.consumer = Consumer(consumer_conf)

        producer_conf = {
            'bootstrap.servers': BOOTSTRAP_SERVERS
        }
        self.producer = Producer(producer_conf)

        self.buffers = defaultdict(deque)

#Callback de confirmación al publicar en sensor.anomaly
    def delivery_report(self, err, msg):
        if err is not None:
            logging.error(f"Error al entregar mensaje en {msg.topic()}: {err}")
        else:
            logging.info(f"Alerta publicada en {msg.topic()} [{msg.partition()}] offset: {msg.offset()}")

#Publica un evento de anomalía hacia sensor.anomaly
    def send_anomaly_alert(self, alert_payload):
        self.producer.produce(
            TOPIC_ANOMALY,
            key=str(alert_payload.get("fridge_id")),
            value=json.dumps(alert_payload),
            callback=self.delivery_report
        )
        self.producer.flush()

    def _parse_timestamp(self, raw_timestamp):
        if isinstance(raw_timestamp, (int, float)):
            return datetime.fromtimestamp(raw_timestamp)
        return datetime.fromisoformat(raw_timestamp)

    def _actualizar_buffer(self, fridge_id, timestamp, temperatura):
        buffer = self.buffers[fridge_id]
        buffer.append({"timestamp": timestamp, "temperatura": temperatura})

        limite_inferior = timestamp - timedelta(minutes=VENTANA_MINUTOS)
        while buffer and buffer[0]["timestamp"] < limite_inferior:
            buffer.popleft()

        return buffer

#Bucle principal en tiempo real
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
                    else:
                        logging.error(f"Error de Kafka: {msg.error()}")
                        continue

                data = json.loads(msg.value().decode('utf-8'))
                logging.info(f"Datos recibidos de sensor.raw: {data}")
                fridge_id = data.get("fridge_id")
                timestamp = self._parse_timestamp(data.get("timestamp"))
                temperatura = data.get("temperatura")

                buffer = self._actualizar_buffer(fridge_id, timestamp, temperatura)

                resultado = evaluar_riesgo(
                    buffer=list(buffer),
                    limite_haccp=LIMITE_HACCP_DEFAULT,
                )

                logging.info(
                    f"[{fridge_id}] pendiente={resultado['pendiente_por_minuto']} "
                    f"tiempo_restante_min={resultado['tiempo_restante_min']}"
                )

                if resultado["hay_riesgo"]:
                    alert_payload = {
                        "fridge_id": fridge_id,
                        "temperatura_actual": temperatura,
                        "pendiente_por_minuto": resultado["pendiente_por_minuto"],
                        "tiempo_restante_min": resultado["tiempo_restante_min"],
                        "timestamp": timestamp.isoformat(),
                    }
                    self.send_anomaly_alert(alert_payload)

        except KeyboardInterrupt:
            logging.info("Deteniendo el consumidor...")
        finally:
            self.consumer.close()

if __name__ == "__main__":
    worker = PredictiveKafkaWorker()
    worker.start_listening()