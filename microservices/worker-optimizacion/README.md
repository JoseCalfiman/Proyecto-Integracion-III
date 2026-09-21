Responsable: Ricardo Aravena

Worker en Celery que, cada cierto número de horas, consulta la API de CNE Chile para obtener el costo del kWh, usa Prophet para predecir el gasto eléctrico del día siguiente y calcula cuánto se ahorraría apagando equipos no críticos en horas de alto costo.



├── worker-optimizacion/           # Worker de Optimización (Ricardo)
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── main.py                    # Lógica principal (consumer Kafka + scheduler)
│   │   ├── config.py                  # Configuración desde .env
│   │   ├── models.py                  # Modelos SQLAlchemy
│   │   ├── optimizer.py               # Lógica de Prophet y scraping CNE
│   │   ├── scraper.py                 # Web scraping de precios CNE
│   │   ├── kafka_consumer.py          # Consumidor de Kafka
│   │   ├── kafka_producer.py          # Productor de Kafka (para reportes)
│   │   ├── crud.py                    # Operaciones CRUD en base de datos
│   │   ├── tests/
│   │   │   ├── test_optimizer.py
│   │   │   └── test_kafka.py
│   │   └── __init__.py