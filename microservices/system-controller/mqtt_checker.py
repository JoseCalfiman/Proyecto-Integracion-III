import os

from health_checker import CheckResult, check_tcp


async def check() -> CheckResult:
    host = os.getenv("MQTT_BROKER_HOST", "mosquitto-service")
    port = int(os.getenv("MQTT_BROKER_PORT", "1883"))
    return await check_tcp(host, port, timeout=3.0)
