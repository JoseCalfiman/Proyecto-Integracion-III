import os

from health_checker import CheckResult, check_tcp


async def check() -> CheckResult:
    host, _, port = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka-service:9092").split(",")[0].strip().partition(":")
    return await check_tcp(host, int(port or 9092), timeout=3.0)
