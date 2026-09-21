Responsable: Matias Carcamo

Worker en Celery que cada 60 segundos lee el histórico reciente de temperatura desde TimescaleDB, calcula la pendiente con regresión lineal (scikit-learn) y estima el tiempo restante antes de una falla. Si el tiempo restante es ≤ 40 minutos, dispara una alerta.



├── worker-predictivo/             # Worker Predictivo (Matías)
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── main.py                    # Lógica principal (consumer Kafka)
│   │   ├── config.py                  # Configuración desde .env
│   │   ├── models.py                  # Modelos SQLAlchemy
│   │   ├── predictor.py               # Lógica de regresión lineal (scikit-learn)
│   │   ├── kafka_consumer.py          # Consumidor de Kafka
│   │   ├── crud.py                    # Operaciones CRUD en base de datos
│   │   ├── tests/
│   │   │   ├── test_predictor.py
│   │   │   └── test_kafka.py
│   │   └── __init__.py