from __future__ import annotations

import logging
import time

import pandas as pd
from apscheduler.schedulers.background import BackgroundScheduler

import db
from buffer import ReadingsBuffer, get_buffer
from kafka_producer import build_recommendation, publish_report
from optimizer import forecast_daily_consumption
from price import get_current_price

logger = logging.getLogger(__name__)

# Intervalo de ejecucion de la tarea de optimizacion (en horas).
INTERVAL_HOURS = 6

# Dias a predecir hacia adelante con Prophet.
FORECAST_HORIZON = 1

# Ventana horaria de alto costo considerada.
HIGH_COST_WINDOW = ["18:00", "22:00"]


def run_optimization(buffer: ReadingsBuffer | None = None) -> dict | None:
    """Pipeline: buffer -> Prophet -> BD -> Kafka.

    Devuelve el reporte publicado o ``None`` si no hay datos suficientes.
    """
    buf = buffer if buffer is not None else get_buffer()
    df = buf.to_dataframe()

    forecast = forecast_daily_consumption(df, horizon=FORECAST_HORIZON)
    if forecast is None:
        logger.warning(
            "[scheduler] datos insuficientes para Prophet (%d dias); se omite",
            len(df),
        )
        return None

    future = forecast.iloc[-FORECAST_HORIZON:]
    target_date = pd.Timestamp(future["ds"].iloc[-1]).date().isoformat()
    predicted_kwh = float(future["yhat"].iloc[-1])

    report = build_recommendation(
        forecasted_kwh=predicted_kwh,
        forecasted_kwh_lower=float(future["yhat_lower"].iloc[-1]),
        forecasted_kwh_upper=float(future["yhat_upper"].iloc[-1]),
        price_clp_kwh=get_current_price(),
        target_date=target_date,
        high_cost_window=HIGH_COST_WINDOW,
    )

    # Primero persistir, luego publicar.
    db.save_report(report)
    publish_report(report)
    logger.info("[scheduler] reporte publicado para %s", target_date)
    return report


def build_scheduler(buffer: ReadingsBuffer | None = None) -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        run_optimization,
        "interval",
        hours=INTERVAL_HOURS,
        kwargs={"buffer": buffer},
        id="optimization_job",
        replace_existing=True,
    )
    return scheduler


def main() -> None:
    """Inicia el scheduler y mantiene vivo el proceso principal."""
    logging.basicConfig(level=logging.INFO)
    scheduler = build_scheduler()
    scheduler.start()
    logger.info("[scheduler] iniciado, tarea programada cada %s horas", INTERVAL_HOURS)
    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        logger.info("[scheduler] detenido")


if __name__ == "__main__":
    main()
