# Ingesta

Responsable: Diego Curiqueo.

Recibe lecturas por MQTT en `sensor/raw`, valida el payload, lo guarda en
TimescaleDB y publica los campos normalizados en Kafka (`sensor.raw`).
FastAPI inicia automáticamente el cliente MQTT en un hilo al arrancar.

## Configuración MQTT

Las variables unificadas son:

```dotenv
MQTT_BROKER_HOST=mosquitto
MQTT_BROKER_PORT=1883
MQTT_BROKER_USER=ingesta
MQTT_BROKER_PASSWORD=<contraseña de la cuenta ingesta>
```

`mosquitto` es el host dentro de Docker Compose. Para ejecutar directamente
con Python y conectar al puerto publicado en tu equipo, usa `localhost`.
Las credenciales deben coincidir con el archivo de contraseñas de Mosquitto.
La cuenta de Ingesta necesita permiso de lectura sobre `sensor/raw`.

Para mantener compatibilidad con el `.env` existente, si no se define
`MQTT_BROKER_USER`, se usa el par `MQTT_INGESTA_USER`/`MQTT_INGESTA_PASSWORD`;
si tampoco existe, se usa `MQTT_USER`/`MQTT_PASSWORD`. No se mezclan pares.

El cliente reintenta incluso si el broker está caído al arrancar. La espera
entre intentos se duplica desde 1 segundo hasta 60 segundos y vuelve a 1
tras conectarse correctamente. Cada conexión exitosa solicita de nuevo
`sensor/raw`; el log confirma la suscripción cuando llega el SUBACK.
Los mensajes publicados durante el corte sin retención o sesión persistente
no se recuperan mediante esta reconexión.

## Confirmación Kafka

`KAFKA_BOOTSTRAP_SERVERS` identifica el broker (`kafka:9092` dentro de Compose).
El productor mantiene `key=id_chamber`, solicita `acks=all` y habilita
idempotencia para los reintentos del productor. Cada publicación espera el
callback de entrega mediante `flush`: plazo de entrega de 10 segundos y
espera máxima del flush de 11 segundos.

Ingesta registra `success` solo después de guardar la lectura y confirmar su
entrega. Un error de encolado, un callback fallido o la ausencia de confirmación
genera `error` en `ingestion_log`, con el motivo en `error_message`. La lectura
guardada permanece en `sensor_data` y el log conserva el payload original.

Los logs de entrega incluyen `topic`, `partition`, `key` y, al confirmar,
`offset`. Si aún no existe una partición asignada, se muestra `unknown` o `-1`.
El flush de cierre también tiene un plazo y reporta mensajes pendientes.

Esta confirmación no es una transacción atómica entre PostgreSQL y Kafka:
no hay reenvío persistente automático si el proceso muere entre guardar y
publicar. Un timeout indica entrega no confirmada; no demuestra que el broker
no recibió el evento. Un outbox sería necesario para recuperación automática
tras caídas del proceso y una clave de evento para deduplicar reenvíos.

## Pruebas

Desde la raíz del repositorio:

```bash
venv/bin/python -B -m unittest discover -s microservices/ingesta/tests -v
```

Prueba real de reconexión (reinicia el contenedor Mosquitto):

```bash
docker compose up -d mosquitto
venv/bin/python -B microservices/ingesta/tests/check_mqtt_reconnect.py
```

Requiere acceso a Docker y las credenciales `MQTT_ADMIN_USER` y
`MQTT_ADMIN_PASSWORD` en `.env` para publicar mensajes de prueba. Usa
`MQTT_HOST_LOCAL` (por defecto `localhost`) para conectar desde tu equipo.
La prueba usa el cliente y callbacks reales de Ingesta, confirma recepción
antes y después de reiniciar el broker, y aísla PostgreSQL y Kafka.

Para aplicar los cambios al servicio:

```bash
docker compose up -d --no-deps --build --force-recreate ingesta
docker compose logs --since 1m -f ingesta
```

### Historial de mediciones

`GET /api/v1/historial?id_chamber=<UUID>&desde=2026-10-01&hasta=2026-10-24&limit=1000`

- `id_chamber`, `desde` y `hasta` son obligatorios.
- Las fechas aceptan `YYYY-MM-DD` o fecha/hora ISO 8601. Sin zona horaria se interpretan en UTC. Una fecha `hasta` sin hora incluye todo ese día UTC; con hora, incluye ese instante exacto.
- `limit` es opcional (1000 por defecto; entre 1 y 10000). Se devuelven las primeras lecturas del intervalo en orden ascendente por `timestamp`, desempate por `id_data`.
- Respuesta: lista JSON de objetos con `id_data`, `id_chamber`, `timestamp`, `temperature` (°C) y `consumption_kw` (kW). Las mediciones ausentes se representan con `null`; sin resultados devuelve `[]`.
- Filtros inválidos o un intervalo invertido devuelven HTTP 422.

El cliente React `getHistorial({ id_chamber, desde, hasta, limit })` devuelve esta lista directamente. La vista `HistorialView.jsx` todavía representa predicciones y usa el filtro `camara`; necesita una adaptación independiente para mostrar estas mediciones. La exportación CSV/PDF no forma parte de este endpoint.

Pruebas sin PostgreSQL, MQTT ni Kafka:

```bash
venv/bin/python -m unittest discover -s microservices/ingesta/tests -p test_historial.py
```

### APIs de optimización

Ambas rutas responden con listas JSON y aceptan `id_chamber=<UUID>` opcional.
Un UUID inválido devuelve 422; sin resultados devuelven `[]`.

- `GET /api/v1/optimizacion/recommendations`: consulta `saving_recommendation`,
  solo con `status=pending`, ordenada por creación e ID descendentes. Mapea
  `id_recommendation → id`, `action → titulo`, `rationale → descripcion`,
  `expected_saving_pct → porcentaje_ahorro`, `expected_saving_amount → monto_clp`.
  Incluye `id_chamber`, `status` y `created_at`. Los importes y porcentajes son
  números JSON o `null`. No se inventan prioridades ni iconos, que no están persistidos.
- `GET /api/v1/optimizacion/forecast`: consulta `predicted_consumption` y devuelve
  `{ "date": "2026-11-02", "pronostico": 150.0, "historico": null }` por día,
  en orden ascendente. Suma las cámaras cuando no se filtra una. El worker guarda
  consumo diario en kWh en la columna `predicted_consumption_kw`; la API conserva
  ese significado. No calcula nuevos pronósticos ni inventa históricos o bandas
  de confianza. Las filas sin fecha se excluyen.

El cliente usa `/optimizacion/recommendations` (con doble `m`) y el gráfico
`ConsumptionForecastChart` consulta `/optimizacion/forecast` directamente.
La exportación de reportes no forma parte de estas rutas.

Pruebas focalizadas, sin PostgreSQL, Kafka ni MQTT:

```bash
venv/bin/python -m unittest discover -s microservices/ingesta/tests -p test_optimizacion.py
```

### API de predicciones

Consulta los resultados ya persistidos por el worker predictivo en `predictions`.

- `GET /api/v1/predictions/latest?id_chamber=<UUID>`: última predicción de la cámara,
  ordenada por `calculation_date DESC NULLS LAST` y luego `id_prediction DESC`.
  Devuelve 404 si la cámara no existe o todavía no tiene predicciones.
- `GET /api/v1/predictions/history?id_chamber=<UUID>&limit=100&offset=0`:
  historial con el mismo orden. `limit` admite 1–1000 (por defecto 100);
  `offset` debe ser mayor o igual a cero. Una cámara existente sin predicciones
  devuelve `[]`; una cámara inexistente devuelve 404.

El UUID es obligatorio; parámetros inválidos devuelven 422. La respuesta de
`latest` es un objeto y la de `history`, una lista de objetos con este contrato:

```json
{
  "id_prediction": 123,
  "id_chamber": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
  "slope": 0.4,
  "projected_temperature": -12.5,
  "remaining_time_min": 42.25,
  "risk_level": "ALTO",
  "calculation_date": "2026-11-01T14:00:00Z"
}
```

`slope` se obtiene de `calculated_slope` (°C/h), la temperatura se expresa en °C
 y el tiempo en minutos. Los campos numéricos ausentes se devuelven como `null`,
 no como cero. `risk_level` conserva el valor persistido por el worker
 (`SIN_RIESGO`, `BAJO`, `MEDIO`, `ALTO`, `CRITICO` según el esquema de la BD).
 No se recalculan predicciones al consultar estos endpoints.

El cliente `src/api/predicciones.js` del Dashboard expone
`getUltimaPrediccion(idChamber)` y
`getHistorialPredicciones(idChamber, { limit, offset })`. Estos endpoints son
independientes del historial de mediciones de sensores.

Pruebas focalizadas de consultas y contrato, sin servicios externos:

```bash
venv/bin/python -m unittest discover -s microservices/ingesta/tests -p test_predictions.py
```
