#!/bin/bash
set -e

BOOTSTRAP_SERVER="kafka:9092"
TOPICS=("sensor.raw" "sensor.anomaly" "haccp.alerts" "optimization.reports")

echo "Esperando a que Kafka esté disponible en $BOOTSTRAP_SERVER..."
until /opt/kafka/bin/kafka-broker-api-versions.sh --bootstrap-server "$BOOTSTRAP_SERVER" > /dev/null 2>&1; do
  echo "Kafka aún no responde, reintentando en 5 segundos..."
  sleep 5
done

echo "Kafka disponible. Creando tópicos..."

for TOPIC in "${TOPICS[@]}"; do
  /opt/kafka/bin/kafka-topics.sh --bootstrap-server "$BOOTSTRAP_SERVER" \
    --create --if-not-exists \
    --topic "$TOPIC" \
    --partitions 1 \
    --replication-factor 1
  echo "Tópico '$TOPIC' listo."
done

echo "Todos los tópicos fueron creados/verificados."