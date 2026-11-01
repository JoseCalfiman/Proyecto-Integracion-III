import os
import threading
from typing import Iterable, Tuple

from confluent_kafka.admin import AdminClient

from health_checker import CheckResult, layered_check

DEFAULT_TOPICS = "sensor.raw,sensor.anomaly,haccp.alerts,optimization.reports"

_admin = None
_admin_lock = threading.Lock()


def required_topics() -> list:
    raw = os.getenv("KAFKA_REQUIRED_TOPICS", DEFAULT_TOPICS)
    return [t.strip() for t in raw.split(",") if t.strip()]


def bootstrap_servers() -> str:
    return os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka-service:9092")


def _get_admin() -> AdminClient:
    global _admin
    with _admin_lock:
        if _admin is None:
            _admin = AdminClient(
                {"bootstrap.servers": bootstrap_servers(), "socket.timeout.ms": 3000}
            )
        return _admin


def evaluate_metadata(md, required: Iterable[str]) -> Tuple[bool, str]:
    """Interpreta los metadatos del clúster. Función pura: fácil de probar."""
    required = list(required)
    brokers = len(md.brokers)
    if brokers == 0:
        return False, "Sin brokers disponibles"

    missing = [t for t in required if t not in md.topics or md.topics[t].error is not None]
    if missing:
        return False, f"Faltan tópicos: {', '.join(missing)}"

    total_partitions = 0
    leaderless = []
    for name in required:
        partitions = md.topics[name].partitions
        total_partitions += len(partitions)
        if not partitions or any(p.leader < 0 or p.error is not None for p in partitions.values()):
            leaderless.append(name)
    if leaderless:
        return False, f"Particiones sin líder en: {', '.join(leaderless)}"

    broker_text = "Broker OK" if brokers == 1 else f"{brokers} brokers OK"
    return True, f"{broker_text}; {len(required)}/{len(required)} tópicos; {total_partitions} particiones"


def _deep(timeout: float) -> Tuple[bool, str]:
    md = _get_admin().list_topics(timeout=timeout)
    return evaluate_metadata(md, required_topics())


async def check() -> CheckResult:
    host, _, port = bootstrap_servers().split(",")[0].strip().partition(":")
    return await layered_check(host, int(port or 9092), timeout=3.0, deep=_deep)
