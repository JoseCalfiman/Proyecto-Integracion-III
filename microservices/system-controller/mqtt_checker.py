import os
import threading
import uuid
from typing import Tuple

import paho.mqtt.client as mqtt

from health_checker import CheckResult, layered_check


def _deep(timeout: float, host: str, port: int) -> Tuple[bool, str]:
    user = os.getenv("MQTT_CONTROLLER_USER")
    password = os.getenv("MQTT_CONTROLLER_PASSWORD")
    if not user or not password:
        return False, "Credenciales MQTT del Controller no configuradas"

    answered = threading.Event()
    outcome = {}

    def on_connect(client, userdata, flags, reason_code, properties=None):
        outcome["rc"] = reason_code
        answered.set()

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2, client_id=f"system-controller-{uuid.uuid4().hex[:8]}"
    )
    client.username_pw_set(user, password)
    client.on_connect = on_connect
    try:
        client.connect(host, port, keepalive=10)
        client.loop_start()
        if not answered.wait(timeout):
            return False, "El broker no respondió al CONNECT"
        rc = outcome["rc"]
        if rc.is_failure:
            return False, f"Conexión rechazada: {rc}"
        return True, "Conexión y autenticación OK"
    finally:
        try:
            client.disconnect()
        except Exception:
            pass
        client.loop_stop()


async def check() -> CheckResult:
    host = os.getenv("MQTT_BROKER_HOST", "mosquitto-service")
    port = int(os.getenv("MQTT_BROKER_PORT", "1883"))
    return await layered_check(host, port, timeout=3.0, deep=lambda t: _deep(t, host, port))
