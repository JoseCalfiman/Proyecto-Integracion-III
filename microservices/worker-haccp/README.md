Responsable: Eduardo Dominguez

Microservicio que escucha los eventos de riesgo (alerta_tecnica) publicados en Redis, aplica las reglas HACCP definidas (por ejemplo, temperatura > 4°C por más de 2 minutos) y envía la notificación correspondiente al bot de Telegram. Además, guarda un log de cada alerta en la base de datos.



├── worker-haccp/                  # Worker HACCP y Alertas (Eduardo)
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── main.py                    # Lógica principal (consumer Kafka)
│   │   ├── config.py                  # Configuración desde .env
│   │   ├── models.py                  # Modelos SQLAlchemy
│   │   ├── haccp_validator.py         # Validación de reglas HACCP
│   │   ├── kafka_consumer.py          # Consumidor de Kafka
│   │   ├── crud.py                    # Operaciones CRUD en base de datos
│   │   ├── tests/
│   │   │   ├── test_haccp.py
│   │   │   └── test_kafka.py
│   │   └── __init__.py