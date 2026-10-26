"""Simulador local de Ingesta: publica lecturas en `sensor.raw` siguiendo el contrato.

Solo para pruebas locales; NO se incluye en la imagen Docker (ver .dockerignore).

Uso:
    KAFKA_BOOTSTRAP_SERVERS=localhost:9092 python tools/simulate_ingesta.py
    python tools/simulate_ingesta.py --interval 10 --start-temp -18 --step 0.3

Por defecto usa las 3 cámaras de database/seeds.sql.
"""
import argparse
import json
import os
import random
import time
from datetime import datetime, timezone

from confluent_kafka import Producer

TOPIC_RAW = "sensor.raw"
SEED_CHAMBERS = [
    "44444444-4444-4444-4444-444444444444",
    "55555555-5555-5555-5555-555555555555",
    "66666666-6666-6666-6666-666666666666",
]


def main():
    parser = argparse.ArgumentParser(description="Simulador de sensor.raw")
    parser.add_argument("--bootstrap", default=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"))
    parser.add_argument("--chambers", nargs="*", default=SEED_CHAMBERS, help="UUIDs de cámaras")
    parser.add_argument("--interval", type=float, default=10.0, help="segundos entre lecturas")
    parser.add_argument("--start-temp", type=float, default=-18.0)
    parser.add_argument("--step", type=float, default=0.3, help="°C máx. de subida por lectura")
    args = parser.parse_args()

    producer = Producer({"bootstrap.servers": args.bootstrap})
    temps = {c: args.start_temp for c in args.chambers}
    print(f"Publicando en '{TOPIC_RAW}' ({args.bootstrap}) cada {args.interval}s. Ctrl+C para detener.")

    try:
        while True:
            for chamber in args.chambers:
                temps[chamber] += random.uniform(0.0, args.step)
                payload = {
                    "id_chamber": chamber,
                    "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                    "temperature": round(temps[chamber], 2),
                    "consumption_kw": round(random.uniform(0.8, 1.5), 3),
                }
                # key = id_chamber: cada cámara siempre en la misma partición
                producer.produce(TOPIC_RAW, key=chamber, value=json.dumps(payload))
                print(f"Enviado: {payload}")
            producer.flush()
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nSimulador detenido.")


if __name__ == "__main__":
    main()
