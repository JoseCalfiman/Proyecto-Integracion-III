from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from models import Chamber, GeneratedAlert, SensorData


PERIODO_HORAS = 24
MAX_ALERTAS_RECIENTES = 5


class ChamberNotFoundError(LookupError):
    """La cámara solicitada no existe en CryoMetric."""


def _numero(value, decimales=2):
    if value is None:
        return "sin datos"

    return round(float(value), decimales)


def construir_contexto_24h(
    db: Session,
    camara_id: UUID,
) -> tuple[str, dict]:
    """
    Construye un resumen de las últimas 24 horas para Gemini.

    Fuentes:
    - chambers
    - sensor_data
    - generated_alerts
    """

    # ========================================================
    # 1. VALIDAR CÁMARA
    # ========================================================

    camara = db.get(Chamber, camara_id)

    if camara is None:
        raise ChamberNotFoundError(
            f"La cámara {camara_id} no existe"
        )

    desde = datetime.now(timezone.utc) - timedelta(
        hours=PERIODO_HORAS
    )

    # ========================================================
    # 2. SENSOR_DATA
    # ========================================================

    mediciones_query = db.query(SensorData).filter(
        SensorData.id_chamber == camara_id,
        SensorData.timestamp >= desde,
    )

    mediciones_consideradas = mediciones_query.count()

    metricas = (
        db.query(
            func.avg(SensorData.temperature),
            func.min(SensorData.temperature),
            func.max(SensorData.temperature),
            func.avg(SensorData.consumption_kw),
            func.min(SensorData.consumption_kw),
            func.max(SensorData.consumption_kw),
        )
        .filter(
            SensorData.id_chamber == camara_id,
            SensorData.timestamp >= desde,
        )
        .one()
    )

    (
        temperatura_promedio,
        temperatura_minima,
        temperatura_maxima,
        consumo_promedio,
        consumo_minimo,
        consumo_maximo,
    ) = metricas

    ultima_medicion = (
        mediciones_query
        .order_by(SensorData.timestamp.desc())
        .first()
    )

    # ========================================================
    # 3. GENERATED_ALERTS
    # ========================================================

    alertas_query = db.query(GeneratedAlert).filter(
        GeneratedAlert.id_chamber == camara_id,
        GeneratedAlert.generation_date >= desde,
    )

    alertas_consideradas = alertas_query.count()

    alertas_activas = alertas_query.filter(
        GeneratedAlert.status == "active"
    ).count()

    alertas_reconocidas = alertas_query.filter(
        GeneratedAlert.status == "acknowledged"
    ).count()

    alertas_resueltas = alertas_query.filter(
        GeneratedAlert.status == "resolved"
    ).count()

    alertas_criticas = alertas_query.filter(
        GeneratedAlert.severity == "critical"
    ).count()

    ultimas_alertas = (
        alertas_query
        .order_by(
            GeneratedAlert.generation_date.desc()
        )
        .limit(MAX_ALERTAS_RECIENTES)
        .all()
    )

    # ========================================================
    # 4. CONSTRUIR RESUMEN
    # ========================================================

    lineas = [
        "CONTEXTO REAL DE CRYOMETRIC",
        "",
        f"Cámara: {camara.name or str(camara_id)}",
        f"ID cámara: {camara_id}",
        f"Ubicación: {camara.location or 'sin ubicación registrada'}",
        f"Periodo analizado: últimas {PERIODO_HORAS} horas",
        "",
        "MEDICIONES DE SENSOR_DATA:",
        f"- Cantidad de mediciones: {mediciones_consideradas}",
        f"- Temperatura promedio: {_numero(temperatura_promedio)} °C",
        f"- Temperatura mínima: {_numero(temperatura_minima)} °C",
        f"- Temperatura máxima: {_numero(temperatura_maxima)} °C",
        f"- Consumo promedio: {_numero(consumo_promedio, 3)} kW",
        f"- Consumo mínimo: {_numero(consumo_minimo, 3)} kW",
        f"- Consumo máximo: {_numero(consumo_maximo, 3)} kW",
    ]

    if ultima_medicion is not None:
        lineas.extend(
            [
                "",
                "ÚLTIMA MEDICIÓN:",
                (
                    "- Temperatura: "
                    f"{_numero(ultima_medicion.temperature)} °C"
                ),
                (
                    "- Consumo: "
                    f"{_numero(ultima_medicion.consumption_kw, 3)} kW"
                ),
                (
                    "- Timestamp: "
                    f"{ultima_medicion.timestamp.isoformat()}"
                ),
            ]
        )
    else:
        lineas.extend(
            [
                "",
                "ÚLTIMA MEDICIÓN:",
                "- No existen mediciones durante las últimas 24 horas.",
            ]
        )

    lineas.extend(
        [
            "",
            "ALERTAS DE GENERATED_ALERTS:",
            f"- Total: {alertas_consideradas}",
            f"- Activas: {alertas_activas}",
            f"- Reconocidas: {alertas_reconocidas}",
            f"- Resueltas: {alertas_resueltas}",
            f"- Críticas: {alertas_criticas}",
        ]
    )

    if ultimas_alertas:
        lineas.append("")
        lineas.append("ALERTAS MÁS RECIENTES:")

        for alerta in ultimas_alertas:
            mensaje = (
                alerta.message[:250]
                if alerta.message
                else "sin mensaje"
            )

            lineas.append(
                "- "
                f"severity={alerta.severity}; "
                f"status={alerta.status}; "
                f"fecha={alerta.generation_date}; "
                f"mensaje={mensaje}"
            )

    else:
        lineas.append(
            "- No existen alertas durante las últimas 24 horas."
        )

    # ========================================================
    # 5. METADATA
    # ========================================================

    metadata = {
        "periodo_horas": PERIODO_HORAS,
        "id_chamber": str(camara_id),
        "chamber_name": camara.name,
        "mediciones_consideradas": mediciones_consideradas,
        "alertas_consideradas": alertas_consideradas,
        "alertas_activas": alertas_activas,
        "alertas_criticas": alertas_criticas,
    }

    return "\n".join(lineas), metadata