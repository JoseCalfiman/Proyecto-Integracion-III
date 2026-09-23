import os

# Kafka
BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
TOPIC_RAW = "sensor.raw"
TOPIC_ANOMALY = "sensor.anomaly"

GROUP_ID = "predictive-worker-group"
AUTO_OFFSET_RESET = "earliest"

# Base de datos (para guardar predicciones)
DB_HOST = os.getenv("DB_HOST", "timescaledb")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "frigorifico")
DB_USER = os.getenv("DB_USER", "admin")
DB_PASSWORD = os.getenv("DB_PASSWORD", "admin")

# HACCP
LIMITE_HACCP_DEFAULT = 4.0  # °C
VENTANA_MINUTOS = 5
MAX_MEDICIONES_VENTANA = 30
UMBRAL_ALERTA_MINUTOS = 40.0
SEVERITY_DEFAULT = "medium"