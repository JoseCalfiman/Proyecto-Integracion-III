import json
import logging
from confluent_kafka import Consumer, Producer, KafkaError
from config import BOOTSTRAP_SERVERS, GROUP_ID, AUTO_OFFSET_RESET, TOPIC_RAW, TOPIC_ANOMALY

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

                #Aquí irán los datos a predictor.py para el cálculo de regresión.

        except KeyboardInterrupt:
            logging.info("Deteniendo el consumidor...")
        finally:
            self.consumer.close()

if __name__ == "__main__":
    worker = PredictiveKafkaWorker()
    worker.start_listening()