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

from ahorro import Action, calcular_ahorro_action

REPORT_TOPIC = os.getenv("KAFKA_REPORT_TOPIC", "optimization.reports")
BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

# Precio del kWh en CLP (precio_clp_kwh) usado para el cálculo de ahorro.
PRECIO_CLP_KWH = 145.0

# Potencia nominal (kW) de los equipos candidatos.
EQUIPMENT_POWER_KW = {
    "camaras_2_y_3": 5.0,
    "eq_climatizacion_zona_b": 3.5,
}

# Acciones de optimización candidatas.
ACTIONS = [
    Action(
        equipment="camaras_2_y_3",
        action="apagar",
        hours=2,
        window=["18:00", "22:00"],
    ),
    Action(
        equipment="eq_climatizacion_zona_b",
        action="reducir_carga",
        hours=2,
        window=["18:00", "22:00"],
    ),
]


def build_recommendation() -> dict[str, Any]:
    """Construye el resumen de la recomendación a publicar.

    Aplica las acciones definidas en ``ACTIONS`` y calcula el ahorro
    potencial en CLP con :func:`calcular_ahorro_action`.

    Returns:
        Diccionario con los datos de la recomendación: fecha objetivo,
        costo estimado del kWh, gasto proyectado, ahorro estimado y
        equipos sugeridos a apagar.
    """
    recommendations: list[dict[str, Any]] = []
    total_savings = 0.0

    for action in ACTIONS:
        potencia_kw = EQUIPMENT_POWER_KW[action.equipment]
        savings = calcular_ahorro_action(action, potencia_kw, PRECIO_CLP_KWH)
        total_savings += savings
        recommendations.append(
            {
                "equipment": action.equipment,
                "action": action.action,
                "window": list(action.window),
                "hours": action.hours,
                "estimated_savings": savings,
            }
        )

    return {
        "type": "optimization_report",
        "target_date": "2024-01-08",
        "forecasted_kwh_cost": PRECIO_CLP_KWH,
        "projected_daily_cost": 580.0,
        "high_cost_window": ["18:00", "22:00"],
        "estimated_savings": total_savings,
        "recommendations": recommendations,
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
