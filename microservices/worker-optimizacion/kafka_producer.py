from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from confluent_kafka import Producer
from ahorro import Action, calcular_ahorro_action

REPORT_TOPIC = os.getenv("KAFKA_REPORT_TOPIC", "optimization.reports")
BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")

# Ventana horaria de alto costo por defecto.
DEFAULT_HIGH_COST_WINDOW = ["18:00", "22:00"]

# Costo diario estimado para el mensaje de prueba sin una prediccion.
DEFAULT_PROJECTED_DAILY_COST = 580.0
DELIVERY_TIMEOUT_SECONDS = 10.0

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


def build_recommendation(
    *,
    id_chamber: str,
    prediction_date: str,
    price_kwh: float,
    predicted_kwh: float | None = None,
    high_cost_window: list[str] | None = None,
    predicted_kwh_lower: float | None = None,
    predicted_kwh_upper: float | None = None,
    id_price: int | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    """Construye el evento con el contrato de ``optimization.reports``."""
    try:
        chamber_key = str(UUID(id_chamber))
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError("id_chamber debe ser un UUID válido") from exc

    recommendations: list[dict[str, Any]] = []
    total_savings = 0.0

    if predicted_kwh is not None:
        projected_daily_cost = predicted_kwh * price_kwh
    else:
        projected_daily_cost = DEFAULT_PROJECTED_DAILY_COST

    remaining_budget = max(projected_daily_cost, 0.0)

    for action in ACTIONS:
        potencia_kw = EQUIPMENT_POWER_KW[action.equipment]

        raw_savings = calcular_ahorro_action(
            action,
            potencia_kw,
            price_kwh,
        )

        # Una recomendación nunca puede ahorrar más que
        # el costo diario total proyectado.
        savings = min(raw_savings, remaining_budget)

        savings_percentage = (
            round((savings / projected_daily_cost) * 100, 2)
            if projected_daily_cost > 0
            else 0.0
        )

        # Protección adicional para el contrato y PostgreSQL.
        savings_percentage = min(max(savings_percentage, 0.0), 100.0)

        remaining_budget = max(remaining_budget - savings, 0.0)
        total_savings += savings

        recommendations.append(
            {
                "equipment": action.equipment,
                "action": action.action,
                "window": list(action.window),
                "hours": action.hours,
                "estimated_savings": savings,
                "savings_percentage": savings_percentage,
            }
        )
    report: dict[str, Any] = {
        "type": "optimization_report",
        "id_chamber": chamber_key,
        "prediction_date": prediction_date,
        "predicted_kwh": predicted_kwh,
        "predicted_kwh_lower": predicted_kwh_lower,
        "predicted_kwh_upper": predicted_kwh_upper,
        "price_kwh": price_kwh,
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "projected_daily_cost": projected_daily_cost,
        "high_cost_window": high_cost_window or DEFAULT_HIGH_COST_WINDOW,
        "estimated_savings": total_savings,
        "recommendations": recommendations,
    }
    if id_price is not None:
        report["id_price"] = id_price
    return report

"""Callback de entrega de Confluent Kafka."""
def on_delivery(err, msg) -> None:
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
) -> bool:
    """Publica con clave de cámara y espera el callback de entrega de Kafka."""
    chamber_id = report.get("id_chamber")
    if not chamber_id:
        raise ValueError("el reporte debe incluir id_chamber para usarlo como key")

    if producer is None:
        producer = build_producer()

    payload = json.dumps(report, ensure_ascii=False)
    delivery: dict[str, Any] = {"called": False, "error": None}

    def delivery_callback(err, msg) -> None:
        on_delivery(err, msg)
        delivery["called"] = True
        delivery["error"] = err

    producer.produce(
        topic,
        key=str(chamber_id).encode("utf-8"),
        value=payload.encode("utf-8"),
        callback=delivery_callback,
    )
    producer.poll(0)
    pending = producer.flush(DELIVERY_TIMEOUT_SECONDS)
    if pending:
        raise TimeoutError(
            f"Kafka no confirmó la entrega del reporte; quedan {pending} mensaje(s)"
        )
    if not delivery["called"]:
        raise RuntimeError("Kafka terminó el flush sin invocar el callback de entrega")
    if delivery["error"] is not None:
        raise RuntimeError(f"Kafka no entregó el reporte: {delivery['error']}")
    return True

"""Encola y envía un mensaje de prueba con datos de ejemplo."""
def main() -> None:
    from db import ID_CHAMBER
    from price import get_current_quote

    quote = get_current_quote()
    if quote is None:
        print("[kafka_producer] no hay precio en energy_price; no se publica")
        return
    publish_report(
        build_recommendation(
            id_chamber=ID_CHAMBER,
            prediction_date=datetime.now(timezone.utc).date().isoformat(),
            price_kwh=float(quote["price_kwh"]),
            id_price=quote["id_price"] if quote["id_price"] is not None else None,
        )
    )
    print(f"[kafka_producer] entrega confirmada en {REPORT_TOPIC}")

if __name__ == "__main__":
    main()
