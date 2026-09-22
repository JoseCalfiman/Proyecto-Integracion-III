# worker-optimizacion

Responsable: Ricardo Aravena

Worker (APScheduler) que consume las lecturas de sensores desde Kafka, predice el
gasto eléctrico del día siguiente con Prophet y calcula cuánto se ahorraría
apagando equipos no críticos en horas de alto costo. El resultado se guarda en la
base de datos y luego se publica en Kafka.

## Flujo

```
sensor.raw (Kafka)
      │
      ▼
kafka_consumer.py  ──►  buffer.py (buffer thread-safe en memoria)
                              │
                              ▼
                     scheduler.py  (cada 6 horas)
                              │
                              ▼
                     optimizer.py  (Prophet real sobre consumo diario)
                              │
                              ▼
                     price.py  (precio kWh desde energy_price / precio_cne.csv)
                              │
                              ▼
              db.py  (persiste predicted_consumption y saving_recommendation)
                              │
                              ▼
              kafka_producer.py  ──►  optimization.reports (Kafka)
```

`main.py` levanta todo en un solo proceso: el consumer corre en un hilo y alimenta
el buffer compartido, mientras el scheduler ejecuta la optimización periódicamente.

## Archivos

| Archivo | Rol |
|---------|-----|
| `main.py` | Entrypoint: consumer (hilo) + scheduler en un proceso |
| `kafka_consumer.py` | Lee `sensor.raw`, normaliza y guarda en el buffer |
| `buffer.py` | Buffer thread-safe de lecturas y agregación diaria de consumo |
| `scheduler.py` | Orquesta el pipeline cada 6 horas |
| `optimizer.py` | Pronóstico de consumo diario con Prophet |
| `price.py` | Precio del kWh desde `energy_price`, `precio_cne.csv` o respaldo |
| `ahorro.py` | Cálculo del ahorro potencial |
| `db.py` | Persistencia en PostgreSQL/TimescaleDB (psycopg2) |
| `kafka_producer.py` | Construye y publica el reporte en Kafka |

## Variables de entorno

| Variable | Default | Descripción |
|----------|---------|-------------|
| `KAFKA_BOOTSTRAP_SERVERS` | `kafka:9092` | Brokers de Kafka |
| `KAFKA_TOPIC` | `sensor.raw` | Tópico de lecturas de sensores |
| `KAFKA_REPORT_TOPIC` | `optimization.reports` | Tópico de salida |
| `KAFKA_GROUP_ID` | `worker-optimizacion` | Grupo de consumo |
| `DB_HOST` / `DB_PORT` | `localhost` / `5432` | Conexión a la base de datos |
| `DB_NAME` / `DB_USER` / `DB_PASS` | `postgres` / `postgres` / — | Credenciales |
| `PRECIO_CLP_KWH` | `145.0` | Precio de respaldo si no hay BD ni CSV |
| `PRECIO_CNE_CSV` | `precio_cne.csv` | Ruta del CSV de precios CNE |

Si la base de datos no está disponible, el worker continúa y solo omite la
persistencia (registra un warning).

## Base de datos

El esquema se crea con `database/init.sql`:

- `energy_price`: precio del kWh (CLP) por timestamp.
- `predicted_consumption`: consumo diario predicho por Prophet.
- `saving_recommendation`: recomendaciones de ahorro por equipo.

## Ejecución

Local:

```bash
pip install -r requirements.txt
python main.py
```

Docker (desde `microservices/worker-optimizacion`):

```bash
docker build -t worker-optimizacion .
docker run --env-file ../../.env worker-optimizacion
```

Tests:

```bash
python -m pytest
```
