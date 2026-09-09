from __future__ import annotations
import logging
import time
from apscheduler.schedulers.background import BackgroundScheduler
from kafka_producer import build_recommendation, publish_report

logger = logging.getLogger(__name__)

# Intervalo de ejecución de la tarea de optimización (en horas).
INTERVAL_HOURS = 6

def run_optimization() -> dict:
    report = build_recommendation()
    publish_report(report)
    logger.info("[scheduler] reporte publicado: %s", report["type"])
    return report


def build_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        run_optimization,
        "interval",
        hours=INTERVAL_HOURS,
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
