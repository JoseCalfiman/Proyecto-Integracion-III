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
El job corre cada 6 horas y admite como máximo una ejecución simultánea. Con
`OPTIMIZATION_RUN_ON_START=true`, el primer disparo del mismo job es inmediato;
no se crea un job adicional para el inicio.

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
| `OPTIMIZATION_CHAMBER_ID` | `1` | Cámara asociada a las recomendaciones (FK del esquema) |
| `OPTIMIZATION_COMPANY_ID` | `1` | Empresa asociada a las recomendaciones (FK del esquema) |
| `OPTIMIZATION_RUN_ON_START` | `false` | Con `true`, ejecuta el primer ciclo al iniciar; activado para el Deployment de demo |
| `PRECIO_CNE_CSV` | `precio_cne.csv` | CSV solo si `energy_price` nunca respondió |
| `HEALTH_PORT` | `8080` | Puerto de `GET /health` |

Si la base de datos no está disponible, el worker continúa y solo omite la
persistencia (registra un warning).

## Salud

`GET /health` (puerto `8080`) lo consultan Kubernetes (`worker-optimizacion-service`)
y el System Controller:

```json
{
  "status": "ok",
  "consumer_alive": true,
  "scheduler_running": true,
  "last_optimization_at": "2026-10-17T15:00:00+00:00"
}
```

`status` es `ok` solo si el consumer sigue vivo y el scheduler está activo.
Responde `503` si alguno no lo está. `last_optimization_at` es el último cálculo
realizado, o `null` si todavía no hubo uno.

## Base de datos

El esquema del proyecto se define en `database/init.sql`. El worker escribe en:

- `energy_price`: lee el último `id_price` y `price_kwh` por `queried_at`.
  Si la lectura falla, reutiliza el último precio y deja un WARNING. No hay precio fijo.
- `predicted_consumption`: inserta el consumo diario predicho (`chamber_id`,
  `prediction_date`, `predicted_consumption_kw`).
- `saving_recommendations`: inserta las recomendaciones (`company_id`,
  `chamber_id`, `price_id`, `action`, `savings_percentage`, `amount_clp`,
  `justification`, `status`).

La cámara y la empresa se toman de `OPTIMIZATION_CHAMBER_ID` y
`OPTIMIZATION_COMPANY_ID` (por defecto `1`).

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
