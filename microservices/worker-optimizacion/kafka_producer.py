"""Publica un resumen con los datos de la recomendación en el tópico
``optimization.reports``. La recomendación describe cuánto se ahorraría
apagando equipos no críticos en horas de alto costo, según la predicción
de gasto eléctrico generada con Prophet.
"""
from __future__ import annotations

import json
import os
from typing import Any

from confluent_kafka import Producer

REPORT_TOPIC = os.getenv("KAFKA_REPORT_TOPIC", "optimization.reports")
BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")


def build_recommendation() -> dict[str, Any]:
    """Construye el resumen de la recomendación a publicar (mock inicial).

    Returns:
        Diccionario con los datos de la recomendación: fecha objetivo,
        costo estimado del kWh, gasto proyectado, ahorro estimado y
        equipos sugeridos a apagar.
    """
    return {
        "type": "optimization_report",
        "target_date": "2024-01-08",
        "forecasted_kwh_cost": 0.145,
        "projected_daily_cost": 580.0,
        "high_cost_window": ["18:00", "22:00"],
        "estimated_savings": 92.5,
        "recommendations": [
            {"equipment": "camaras_2_y_3", "action": "apagar", "window": ["18:00", "22:00"]},
            {"equipment": "eq_climatizacion_zona_b", "action": "reducir_carga", "window": ["18:00", "22:00"]},
        ],
    }


def on_delivery(err, msg) -> None:
    """Callback de entrega de Confluent Kafka."""
    if err is not None:
        print(f"[kafka_producer] error al publicar en {msg.topic()}: {err}")
        return
    print(
        f"[kafka_producer] publicado en {msg.topic()} "
        f"particion {msg.partition()} offset {msg.offset()}"
    )


def build_producer() -> Producer:
    return Producer({"bootstrap.servers": BOOTSTRAP_SERVERS})


def publish_report(
    report: dict[str, Any],
    producer: Producer | None = None,
    topic: str = REPORT_TOPIC,
) -> Producer:
    """Publica el resumen de la recomendación en ``optimization.reports``.

    Args:
        report: Diccionario con los datos de la recomendación
            (ver :func:`build_recommendation`).
        producer: Productor ya construido; si es None se crea uno nuevo.
        topic: Tópico destino (por defecto ``optimization.reports``).

    Returns:
        El productor usado, con el mensaje encolado para su envío.
    """
    if producer is None:
        producer = build_producer()

    payload = json.dumps(report, ensure_ascii=False)
    producer.produce(topic, value=payload.encode("utf-8"), callback=on_delivery)
    producer.poll(0)
    return producer


def main() -> None:
    """Encola y envía un mensaje de prueba con datos de ejemplo."""
    producer = publish_report(build_recommendation())
    producer.flush()
    print(f"[kafka_producer] flush completado en {REPORT_TOPIC}")


if __name__ == "__main__":
    main()
