Responsable: Diego Curiqueo

Microservicio que recibe los datos de los sensores (temperatura/consumo), los valida y los guarda en TimescaleDB. Al recibir un dato nuevo, publica un evento nuevos_datos en Redis para que el worker predictivo lo procese.


infra ingesta:

ingesta/ # Microservicio de ingesta (Diego) - FastAPI

│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── app.py                     # Punto de entrada (FastAPI)
│   │   ├── main.py                    # Lógica principal
│   │   ├── config.py                  # Configuración desde .env
│   │   ├── models.py                  # Modelos SQLAlchemy
│   │   ├── schemas.py                 # Schemas Pydantic (validación)
│   │   ├── mqtt_client.py             # Cliente MQTT (suscriptor)
│   │   ├── kafka_producer.py          # Productor de Kafka
│   │   ├── crud.py                    # Operaciones CRUD en base de datos
│   │   ├── routes/                    # Endpoints de la API
│   │   │   ├── auth.py                # Login, logout, refresh token
│   │   │   ├── alertas.py             # Endpoints de alertas
│   │   │   ├── camaras.py             # Endpoints de cámaras
│   │   │   ├── haccp.py               # Endpoints de reglas HACCP
│   │   │   ├── optimizacion.py        # Endpoints de recomendaciones de ahorro
│   │   │   ├── historial.py           # Endpoints de historial
│   │   │   └── usuarios.py            # Endpoints de usuarios
│   │   ├── tests/
│   │   │   ├── test_api.py
│   │   │   └── test_mqtt.py
│   │   └── __init__.py