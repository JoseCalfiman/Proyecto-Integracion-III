import json
import time
import random
from confluent_kafka import Producer
from config import BOOTSTRAP_SERVERS, TOPIC_RAW

def delivery_report(err, msg):
    if err is not None:
        print(f"Error al enviar mensaje: {err}")
    else:
        print(f"Mensaje enviado a {msg.topic()} [{msg.partition()}]")

def main():
    producer = Producer({'bootstrap.servers': BOOTSTRAP_SERVERS})
    print(f"Enviando datos a '{TOPIC_RAW}'...")

    temp = 4.0
    fridge_id = "FRIDGE_001"

    try:
        while True:
            temp += random.uniform(0.1, 0.5)
            
            payload = {
                "fridge_id": fridge_id,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "temperature": round(temp, 2),
                "kw": round(random.uniform(0.8, 1.5), 2)
            }

            producer.produce(
                TOPIC_RAW,
                key=fridge_id,
                value=json.dumps(payload),
                callback=delivery_report
            )
            producer.flush()

            print(f"Enviado: {payload}")
            time.sleep(3)

    except KeyboardInterrupt:
        print("\nSimulador detenido.")

if __name__ == "__main__":
    main()