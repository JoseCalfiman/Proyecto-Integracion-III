import json
import random
import threading
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt


MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
MQTT_TOPIC = "sensor/raw"

CAMERAS = [
    "44444444-4444-4444-4444-444444444444",
    "55555555-5555-5555-5555-555555555555",
    "66666666-6666-6666-6666-666666666666",
]

NUM_SIMULATED_CAMERAS = 30

# 1 mensaje por segundo por cámara lógica
INTERVAL_SECONDS = 1.0


def create_client(index: int):
    client_id = f"cryometric-load-{index:02d}-{random.randint(1000, 9999)}"

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=client_id,
    )

    client.connect(
        MQTT_BROKER,
        MQTT_PORT,
        keepalive=60,
    )

    client.loop_start()

    return client


def simulate_camera(index: int):
    chamber_id = CAMERAS[index % len(CAMERAS)]

    client = create_client(index)

    print(
        f"[SIM-{index + 1:02d}] conectado "
        f"→ {chamber_id}"
    )

    try:
        while True:
            if index % 3 == 0:
                temperature = random.uniform(3.0, 10.0)

            elif index % 3 == 1:
                temperature = random.uniform(1.0, 5.0)

            else:
                temperature = random.uniform(-7.0, -2.0)

            consumption_kw = random.uniform(
                0.5,
                3.5,
            )

            payload = {
                "id_chamber": chamber_id,
                "temperature": round(
                    temperature,
                    2,
                ),
                "consumption_kw": round(
                    consumption_kw,
                    2,
                ),
                "timestamp": datetime.now(
                    timezone.utc
                ).isoformat(),
            }

            info = client.publish(
                MQTT_TOPIC,
                json.dumps(payload),
                qos=0,
            )

            if info.rc == mqtt.MQTT_ERR_SUCCESS:
                print(
                    f"[SIM-{index + 1:02d}] "
                    f"OK | "
                    f"{chamber_id[:8]} | "
                    f"T={payload['temperature']} C | "
                    f"P={payload['consumption_kw']} kW"
                )

            else:
                print(
                    f"[SIM-{index + 1:02d}] "
                    f"ERROR MQTT rc={info.rc}"
                )

            time.sleep(
                INTERVAL_SECONDS
            )

    except Exception as exc:
        print(
            f"[SIM-{index + 1:02d}] "
            f"ERROR: {exc}"
        )

    finally:
        client.loop_stop()
        client.disconnect()


def main():
    print("=" * 60)
    print("CryoMetric - PRUEBA DE CARGA")
    print(f"Camaras simuladas: {NUM_SIMULATED_CAMERAS}")
    print(f"Broker: {MQTT_BROKER}:{MQTT_PORT}")
    print(f"Topic: {MQTT_TOPIC}")
    print(
        f"Carga aproximada: "
        f"{NUM_SIMULATED_CAMERAS / INTERVAL_SECONDS:.0f} msg/s"
    )
    print("=" * 60)

    threads = []

    for index in range(
        NUM_SIMULATED_CAMERAS
    ):
        thread = threading.Thread(
            target=simulate_camera,
            args=(index,),
            daemon=True,
        )

        thread.start()
        threads.append(thread)

        # Evita abrir las 30 conexiones exactamente al mismo instante
        time.sleep(0.05)

    try:
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nPrueba detenida por el usuario.")


if __name__ == "__main__":
    main()