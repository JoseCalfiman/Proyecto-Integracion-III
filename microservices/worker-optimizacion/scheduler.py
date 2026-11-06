from __future__ import annotations

import logging
import os
import time
from datetime import datetime

import pandas as pd
from apscheduler.schedulers.background import BackgroundScheduler

import db
from buffer import ReadingsBuffer, get_buffer
from health import health
from kafka_producer import build_recommendation, publish_report
from optimizer import forecast_daily_consumption
from price import get_current_quote

logger = logging.getLogger(__name__)

# Intervalo de ejecucion de la tarea de optimizacion (en horas).
INTERVAL_HOURS = 6

# Dias a predecir hacia adelante con Prophet.
FORECAST_HORIZON = 1

# Ventana horaria de alto costo considerada.
HIGH_COST_WINDOW = ["18:00", "22:00"]


def run_optimization(buffer: ReadingsBuffer | None = None) -> dict | None:
    """Pipeline: historial de 7 días en BD (o buffer) -> Prophet -> BD -> Kafka.

    Devuelve el reporte publicado o ``None`` si no hay datos suficientes.
    """

    buf = buffer if buffer is not None else get_buffer()

    if not db.validate_schema():
        logger.error(
            "[scheduler] base de datos o esquema incompatible; "
            "se omite la optimización"
        )
        return None

    history = db.get_consumption_history(days=7)

    if history:
        df = pd.DataFrame(
            {
                "ds": [row["date"] for row in history],
                "y": [row["consumption_kwh"] for row in history],
            }
        )

        logger.info(
            "[scheduler] usando historial real de consumo "
            "de los últimos 7 días"
        )

    else:
        df = buf.to_dataframe()

        logger.info(
            "[scheduler] historial de BD vacío; "
            "se usa el buffer de lecturas"
        )

    forecast = forecast_daily_consumption(
        df,
        horizon=FORECAST_HORIZON,
    )

    if forecast is None:
        logger.warning(
            "[scheduler] datos insuficientes para Prophet "
            "(%d dias); se omite",
            len(df),
        )
        return None

    quote = get_current_quote()

    if quote is None:
        logger.warning(
            "[scheduler] sin precio de energia; "
            "se omite la optimizacion"
        )
        return None

    future = forecast.iloc[-FORECAST_HORIZON:]

    prediction_date = (
        pd.Timestamp(future["ds"].iloc[-1])
        .date()
        .isoformat()
    )

    # Prophet puede generar valores negativos en el intervalo
    # de confianza. Como el consumo energetico no puede ser
    # negativo, se limita el valor minimo a 0.
    predicted_kwh = max(
        0.0,
        float(future["yhat"].iloc[-1]),
    )

    predicted_kwh_lower = max(
        0.0,
        float(future["yhat_lower"].iloc[-1]),
    )

    predicted_kwh_upper = max(
        0.0,
        float(future["yhat_upper"].iloc[-1]),
    )

    id_price = quote["id_price"]

    report = build_recommendation(
        id_chamber=db.ID_CHAMBER,
        prediction_date=prediction_date,
        predicted_kwh=predicted_kwh,
        predicted_kwh_lower=predicted_kwh_lower,
        predicted_kwh_upper=predicted_kwh_upper,
        price_kwh=float(quote["price_kwh"]),
        high_cost_window=HIGH_COST_WINDOW,
        id_price=int(id_price) if id_price is not None else None,
    )

    # Primero persistir, luego publicar.
    db.save_report(report)

    publish_report(report)

    health.mark_optimization()

    logger.info(
        "[scheduler] reporte publicado para %s",
        prediction_date,
    )

    return report


def build_scheduler(
    buffer: ReadingsBuffer | None = None,
) -> BackgroundScheduler:

    scheduler = BackgroundScheduler()

    run_on_start = (
        os.getenv(
            "OPTIMIZATION_RUN_ON_START",
            "false",
        )
        .strip()
        .lower()
        in {
            "1",
            "true",
            "yes",
            "on",
        }
    )

    startup_options = (
        {"next_run_time": datetime.now()}
        if run_on_start
        else {}
    )

    scheduler.add_job(
        run_optimization,
        "interval",
        hours=INTERVAL_HOURS,
        kwargs={"buffer": buffer},
        id="optimization_job",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        **startup_options,
    )

    return scheduler


def main() -> None:
    """Inicia el scheduler y mantiene vivo el proceso principal."""

    logging.basicConfig(
        level=logging.INFO
    )

    scheduler = build_scheduler()

    scheduler.start()

    logger.info(
        "[scheduler] iniciado, tarea programada cada %s horas",
        INTERVAL_HOURS,
    )

    try:
        while True:
            time.sleep(1)

    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()

        logger.info(
            "[scheduler] detenido"
        )


if __name__ == "__main__":
    main()