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
el buffer compartido. En cada ciclo, el scheduler toma el consumo diario real de
los últimos 7 días desde `sensor_data`, convierte cada lectura de kW a kWh usando
el intervalo de 10 segundos y usa el buffer si la consulta no devuelve historial.
Después ejecuta la optimización periódicamente.
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
| `DB_HOST` / `DB_PORT` | `localhost` / `5432` | Conexión a la base de datos (en Docker Compose, `DB_HOST=timescaledb`) |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` | `frigorifico` / `admin` / `admin123` | Credenciales PostgreSQL |
| `OPTIMIZATION_CHAMBER_ID` | `44444444-4444-4444-4444-444444444444` | Cámara asociada a las recomendaciones (FK del esquema) |
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
- `predicted_consumption`: inserta el consumo diario predicho (`id_chamber`,
  `prediction_date`, `predicted_consumption_kw`).
- `saving_recommendation`: inserta recomendaciones con las columnas oficiales
  (`id_chamber`, `id_price`, `action`, `expected_saving_pct`,
  `expected_saving_amount`, `rationale`, `status`).

La cámara se toma de `OPTIMIZATION_CHAMBER_ID` y debe ser un UUID existente en
`chambers.id_chamber` (el valor predeterminado corresponde a los seeds del proyecto).
Antes de calcular, el worker valida que la conexión funcione, que las columnas
consultadas/escritas existan en las tablas oficiales y que el UUID de cámara exista.
Si alguna comprobación falla, omite el cálculo y registra el error en el log.

## Evento Kafka `optimization.reports`

El productor publica el UUID de cámara como clave Kafka (UTF-8) y un JSON con
`id_chamber`, `prediction_date`, `predicted_kwh`, `price_kwh`, `recommendations`
y `generated_at` (UTC ISO 8601). También incluye intervalos de predicción y
resumen de ahorros. El productor espera el callback de entrega hasta 10 segundos;
si Kafka informa un error o vence el tiempo, la publicación falla explícitamente.

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

## Demostración E2E local

Desde la raíz del repositorio, levanta los servicios implicados:

```bash
docker compose up -d --build timescaledb kafka kafka-init ingesta worker-optimizacion dashboard
```

En una terminal, deja un consumidor esperando el siguiente evento (no uses
`--from-beginning`, para observar el reporte recién generado):

```bash
docker compose exec kafka /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic optimization.reports \
  --max-messages 1
```

En otra terminal, dispara una optimización inmediata en el contenedor del worker:

```bash
docker compose exec worker-optimizacion python -c "import scheduler; scheduler.run_optimization()"
```

La salida del consumidor debe incluir `type: optimization_report`, la predicción,
`price_kwh`, el total de `estimated_savings` y la lista de `recommendations`.
Comprueba además la escritura en las tablas y las respuestas HTTP:

```bash
docker compose exec timescaledb sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT prediction_date, predicted_consumption_kw FROM predicted_consumption ORDER BY generation_date DESC LIMIT 1"'
docker compose exec timescaledb sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT action, expected_saving_pct, expected_saving_amount AS ahorro_clp, rationale, status FROM saving_recommendation ORDER BY created_at DESC, id_recommendation DESC LIMIT 5"'
curl http://localhost:8001/api/v1/dashboard/live
curl http://localhost:8001/api/v1/optimizacion/recomendaciones
```

La API de recomendaciones entrega los registros pendientes de la optimización más
reciente. Para comprobar la presentación, inicia sesión como gerente en
`http://localhost:8501/ahorro`: el total y cada tarjeta de recomendación deben
coincidir con los montos CLP devueltos por la API. El dashboard general muestra
el mismo total en la tarjeta “Ahorro Estimado”.
