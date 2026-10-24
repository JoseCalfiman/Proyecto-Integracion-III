# Worker Predictivo

Responsable: Matías Cárcamo

Worker que consume lecturas de sensores desde el tópico Kafka `sensor.raw`,
mantiene una ventana deslizante de temperaturas por cámara, calcula la pendiente
de calentamiento mediante regresión lineal, evalúa el riesgo, persiste las
predicciones en la base de datos y emite alertas predictivas a `sensor.anomaly`.

## Flujo del worker

1. `main.py` levanta primero el servidor de salud (`GET /health`, puerto 8000)
   y luego importa el resto del proyecto y arranca el consumidor.
2. El consumidor escucha el tópico `sensor.raw` y valida el contrato del mensaje.
   Los mensajes inválidos se descartan con un warning.
3. Actualiza la ventana deslizante temporal por cámara, ignorando lecturas
   repetidas o desordenadas.
4. Consulta la regla HACCP activa de la cámara. Si no existe, usa los valores
   por defecto de `config.py`.
5. Ejecuta el modelo predictivo: calcula la pendiente (°C/min) y el tiempo
   restante hasta `max_absolute_temp`.
6. Guarda la predicción generada en la tabla `predictions`.
7. Si detecta riesgo (tiempo restante dentro del umbral de alerta), publica el
   evento en el tópico `sensor.anomaly`.

```
sensor.raw ──► validación ──► ventana deslizante ──► regla HACCP activa
                                                          │
                                                          ▼
sensor.anomaly ◄── (si hay riesgo) ◄── predictor ──► predictions (BD)
```

## Niveles de riesgo

El nivel se calcula según el tiempo restante frente al umbral de alerta
(`tolerance_time_min` de la regla, o 40 min por defecto):

| Condición | Nivel |
|---|---|
| Sin calentamiento o datos insuficientes | `SIN_RIESGO` |
| Tiempo restante > umbral | `BAJO` |
| Tiempo restante ≤ umbral | `MEDIO` |
| Tiempo restante ≤ 60 % del umbral | `ALTO` |
| Tiempo restante ≤ 25 % del umbral | `CRITICO` |

Solo `MEDIO`, `ALTO` y `CRITICO` generan alerta en `sensor.anomaly`. Al guardar
en `predictions`, los niveles se traducen al vocabulario del `CHECK` de la tabla
(`low`, `medium`, `high`, `critical`); el payload publicado conserva los nombres
originales.

## Contrato de la alerta (`sensor.anomaly`)

```json
{
  "id_chamber": "uuid",
  "remaining_time_min": 18.5,
  "temperature": -12.4,
  "severity": "medium",
  "risk_level": "ALTO",
  "slope_per_minute": 0.31,
  "recorded_at": "2026-10-24T05:34:58+00:00"
}
```

## Salud del servicio

`GET /health` en el puerto 8000 responde `{"status": "healthy", "service": "worker-predictivo"}`.
Se usa en las probes de Kubernetes (`startupProbe`, `livenessProbe` y
`readinessProbe`). El servidor arranca antes de cargar el resto del código para
que el pod no sea reiniciado mientras inicia.

## Archivos clave

- `main.py`: punto de entrada; levanta el servidor de salud y el bucle de reintentos del worker.
- `kafka_consumer.py`: suscripción a Kafka, gestión de búferes y orquestación del flujo.
- `predictor.py`: regresión lineal con `scikit-learn`, estimación de tiempo restante y niveles de riesgo.
- `window.py`: lógica de la ventana deslizante temporal y filtrado de duplicados o desordenados.
- `haccp_predictions.py`: consulta de reglas HACCP y persistencia de predicciones vía SQLAlchemy.
- `models.py`: definición del modelo ORM para las predicciones.
- `contract.py`: validación estricta y normalización del contrato de datos de los sensores.
- `db.py`: sesión y creación de tablas.
- `config.py`: configuración del worker (Kafka, ventana, umbrales y valores por defecto).

## Ejecutar con Docker

```bash
docker build -t worker-predictivo .
docker run --rm -p 8000:8000 worker-predictivo
```

## Despliegue en Kubernetes

El manifiesto está en `k8s/worker-predictivo/deployment.yaml`. Espera a
TimescaleDB con un initContainer y toma su configuración del ConfigMap
`app-config`.

## Dependencias

```txt
confluent-kafka==2.15.0
scikit-learn==1.5.0
numpy==1.26.4
sqlalchemy==2.0.30
psycopg2-binary==2.9.9
python-dotenv==1.0.1
pytest==8.3.3
```