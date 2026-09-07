import os

# Configuración del Broker de Kafka
BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

# Tópicos
TOPIC_RAW = "sensor.raw"
TOPIC_ANOMALY = "sensor.anomaly"

# Configuración del Consumidor
GROUP_ID = "predictive-worker-group"
AUTO_OFFSET_RESET = "earliest"