"""Prueba manual real: reinicia Mosquitto y verifica recepción tras resuscribirse.

Ejecutar desde la raíz: venv/bin/python microservices/ingesta/tests/check_mqtt_reconnect.py
Requiere Mosquitto levantado con Docker Compose. No escribe en PostgreSQL ni Kafka.
"""

import importlib.util
import os
from pathlib import Path
import queue
import subprocess
import threading
from unittest.mock import MagicMock, patch
import uuid

from dotenv import dotenv_values
import paho.mqtt.client as mqtt


def main():
    root = Path(__file__).resolve().parents[3]
    config = {**dotenv_values(root / ".env"), **os.environ}
    settings = {
        "MQTT_BROKER_HOST": config.get("MQTT_HOST_LOCAL") or "localhost",
        "MQTT_BROKER_PORT": config.get("MQTT_BROKER_PORT") or "1883",
        "MQTT_BROKER_USER": config.get("MQTT_BROKER_USER") or config.get("MQTT_INGESTA_USER") or config.get("MQTT_USER", ""),
        "MQTT_BROKER_PASSWORD": (
            config.get("MQTT_BROKER_PASSWORD", "") if config.get("MQTT_BROKER_USER")
            else config.get("MQTT_INGESTA_PASSWORD", "") if config.get("MQTT_INGESTA_USER")
            else config.get("MQTT_PASSWORD", "")
        ),
    }
    spec = importlib.util.spec_from_file_location("mqtt_reconnect_check", root / "microservices/ingesta/mqtt_client.py")
    module = importlib.util.module_from_spec(spec)
    # La conexión y callbacks MQTT son reales; solo se aíslan BD y Kafka.
    with patch.dict(os.environ, settings), patch.dict("sys.modules", {
        name: MagicMock() for name in ("database", "models", "schemas", "kafka_producer")
    }), patch("dotenv.load_dotenv"):
        spec.loader.exec_module(module)

    subscribed = threading.Event()
    messages = queue.Queue()

    def on_subscribe(client, userdata, mid, reason_codes, properties=None):
        module.on_subscribe(client, userdata, mid, reason_codes, properties)
        if reason_codes and all(not code.is_failure for code in reason_codes):
            subscribed.set()

    module.client.on_subscribe = on_subscribe
    module.client.on_message = lambda client, userdata, msg: messages.put(msg.payload)
    worker = threading.Thread(target=module.start, daemon=True)

    def verify_delivery():
        probe = f"reconnect-check-{uuid.uuid4()}".encode()
        publisher = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        publisher.username_pw_set(config["MQTT_ADMIN_USER"], config["MQTT_ADMIN_PASSWORD"])
        publisher.connect(settings["MQTT_BROKER_HOST"], int(settings["MQTT_BROKER_PORT"]), 60)
        publisher.loop_start()
        try:
            info = publisher.publish("sensor/raw", probe, qos=1)
            info.wait_for_publish(timeout=10)
            while messages.get(timeout=10) != probe:
                pass
        finally:
            publisher.disconnect()
            publisher.loop_stop()

    worker.start()
    try:
        if not subscribed.wait(30):
            raise RuntimeError("No se confirmó la suscripción inicial")
        verify_delivery()
        print("OK: mensaje recibido antes del reinicio", flush=True)
        subscribed.clear()
        subprocess.run(["docker", "compose", "restart", "mosquitto"], cwd=root, check=True)
        if not subscribed.wait(75):
            raise RuntimeError("No se confirmó la resuscripción tras reiniciar Mosquitto")
        verify_delivery()
        print("OK: reconexión, resuscripción y recepción después del reinicio sin reiniciar el cliente", flush=True)
    finally:
        module.client.disconnect()
        worker.join(timeout=5)


if __name__ == "__main__":
    main()
