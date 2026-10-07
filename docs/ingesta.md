# Ingesta

**Responsable:** Diego Curiqueo
**Ubicación en el repo:** `microservices/ingesta/`

## 1. Propósito

El microservicio de ingesta cumple dos funciones:

1. **Recibir las lecturas de los sensores** (temperatura y consumo eléctrico) por MQTT, validarlas y guardarlas en TimescaleDB (tabla `sensor_data`).
2. **Exponer la API REST (FastAPI)** que consume el dashboard: cámaras, alertas, reglas HACCP, métricas en vivo, etc. Nginx, en el contenedor del dashboard, reenvía las peticiones `/api/` a este servicio.

Los workers (predictivo, HACCP, optimización) no se comunican con ingesta por HTTP: trabajan a través de Kafka y de la base de datos compartida.

## 2. Arquitectura y flujo

```
Sensores ──MQTT (sensor/raw)──► mqtt_client.py ──► TimescaleDB (sensor_data)
                                      │
                                      └──(pendiente)──► Kafka (sensor.raw) ──► workers

Navegador ──► Nginx (dashboard) ──/api/v1/*──► FastAPI (ingesta) ──► PostgreSQL / TimescaleDB
```

Flujo de una lectura:

1. El sensor publica un JSON en el tópico MQTT `sensor/raw`.
2. `mqtt_client.py` lo decodifica y lo valida con `SensorDataCreate`.
3. Si es válido, inserta una fila en `sensor_data`.
4. Si el JSON o la validación fallan, la lectura se descarta y se imprime el error.

## 3. Estructura de archivos

| Archivo | Rol | Estado |
|---|---|---|
| `main.py` | Aplicación FastAPI (CORS y `/health`) | Implementado; faltan los routers |
| `database.py` | Conexión SQLAlchemy y dependencia `get_db` | Implementado |
| `models.py` | Modelos SQLAlchemy | Implementado; faltan modelos de alertas, reglas HACCP y recomendaciones |
| `schemas.py` | Schemas Pydantic de validación | Implementado para sensores; faltan los de cámaras, alertas, HACCP y dashboard |
| `mqtt_client.py` | Suscriptor MQTT y guardado en BD | Implementado |
| `kafka_propducer.py` | Productor Kafka (tópico `sensor.raw`) | Implementado, pero no se usa (ver sección 10) |
| `routes/chambers.py` | CRUD de cámaras | Diseñado |
| `routes/alerts.py` | Alertas HACCP | Diseñado |
| `routes/haccp.py` | Reglas HACCP | Diseñado |
| `routes/dashboard.py` | Métricas en vivo | Diseñado |
| `routes/auth.py`, `sensors.py`, `optimization.py`, `history.py`, `users.py` | Resto de la API | Pendiente |
| `Dockerfile` | Imagen del servicio (Python 3.12, `uvicorn main:app`, puerto 8000) | Implementado |

## 4. Configuración

Las variables se leen del entorno o de un archivo `.env` (`python-dotenv`).

| Variable | Valor por defecto | Descripción |
|---|---|---|
| `DATABASE_URL` | — | URL completa de la BD. Si existe, tiene prioridad sobre las `PG*` |
| `PGUSER` / `POSTGRES_USER` | — | Usuario de la BD |
| `PGPASSWORD` / `POSTGRES_PASSWORD` | — | Contraseña de la BD |
| `PGHOST` | `localhost` | Servidor de la BD |
| `PGPORT` | `5432` | Puerto de la BD |
| `PGDATABASE` / `POSTGRES_DB` | — | Nombre de la BD |
| `MQTT_BROKER_HOST` | `test.mosquitto.org` | Broker MQTT |
| `MQTT_BROKER_PORT` | `1883` | Puerto del broker |
| `MQTT_USER` / `MQTT_PASSWORD` | vacío | Credenciales del broker (opcionales) |
| `KAFKA_BROKER` | `localhost:9092` | Broker Kafka del productor |

## 5. Ingesta MQTT

**Tópico:** `sensor/raw`

**Formato del mensaje:**

```json
{
  "id_chamber": "22222222-2222-2222-2222-222222222222",
  "temperature": -18.5,
  "consumption_kw": 2.34,
  "timestamp": "2026-09-28T21:00:00+00:00"
}
```

**Validaciones** (`SensorDataCreate`):

| Campo | Tipo | Regla |
|---|---|---|
| `id_chamber` | UUID | Obligatorio |
| `temperature` | número | Entre -50 y 50 °C |
| `consumption_kw` | número | Entre 0 y 999.999 kW |
| `timestamp` | fecha y hora | Obligatorio |

**Funciones de `mqtt_client.py`:**

- `on_connect`: al conectar, se suscribe a `sensor/raw`.
- `on_message`: decodifica el mensaje; si no es JSON válido, lo descarta.
- `procesar_payload`: llama a `save_sensor_data` y captura los errores para que un mensaje malo no detenga el suscriptor.
- `save_sensor_data`: valida con Pydantic e inserta en `sensor_data` (con `commit`, o `rollback` si falla).
- `start`: conecta al broker y entra en `loop_forever`.

## 6. Modelo de datos

Los modelos de `models.py` siguen el esquema de `database/init.sql`.

| Tabla | Uso en ingesta |
|---|---|
| `company`, `roles`, `users` | Base de usuarios (la API de usuarios y el login están pendientes) |
| `chambers` | CRUD de cámaras |
| `sensors` | Inventario de sensores (pendiente) |
| `sensor_data` | Hipertabla de TimescaleDB, clave primaria compuesta `(id_data, timestamp)`. Aquí se guardan las lecturas |
| `ingestion_log` | Modelo definido, pero aún no se escribe desde `mqtt_client.py` |
| `generated_alerts`, `alert_audit` | Lectura y cambio de estado de alertas |
| `haccp_rules` | Lectura y edición de reglas |
| `saving_recommendation` | Lectura para la métrica de ahorro del dashboard |

## 7. API REST

**Prefijo:** `/api/v1` (se registra en `main.py` con `app.include_router(router, prefix="/api/v1")`).
**Documentación interactiva:** `/docs` (Swagger de FastAPI).

| Método | Ruta | Descripción | Permiso previsto |
|---|---|---|---|
| GET | `/health` | Estado del servicio (sin prefijo `/api/v1`) | Público |
| GET | `/chambers` | Lista cámaras activas (`?include_inactive=true` incluye las desactivadas) | Técnico, gerente |
| GET | `/chambers/{id_chamber}` | Detalle de una cámara | Técnico, gerente |
| POST | `/chambers` | Crea una cámara | Gerente |
| PUT | `/chambers/{id_chamber}` | Actualiza campos de una cámara | Gerente |
| DELETE | `/chambers/{id_chamber}` | Desactiva la cámara (borrado lógico) | Gerente |
| GET | `/alerts` | Lista alertas. Filtros: `id_chamber`, `severity`, `status`, `limit`, `offset` | Técnico, gerente |
| GET | `/alerts/{id_alert}` | Detalle de una alerta | Técnico, gerente |
| GET | `/alerts/{id_alert}/audit` | Historial de acciones de la alerta | Técnico, gerente |
| PUT | `/alerts/{id_alert}/acknowledge` | Reconoce una alerta (`active` → `acknowledged`) | Técnico |
| PUT | `/alerts/{id_alert}/resolve` | Resuelve una alerta (`acknowledged` → `resolved`) | Técnico |
| GET | `/haccp/rules` | Cámaras activas con su regla (o valores por defecto) | Técnico, gerente |
| GET | `/haccp/rules/{id_chamber}` | Regla de una cámara | Técnico, gerente |
| PUT | `/haccp/rules/{id_chamber}` | Actualiza la regla; si no existe, la crea | Técnico, gerente |
| GET | `/dashboard/live` | Métricas en vivo para las tarjetas del dashboard | Técnico, gerente |

### 7.1 Convenciones

- Los campos de la API usan los nombres en inglés de la base de datos (`id_chamber`, `max_absolute_temp`, etc.).
- Los identificadores de cámara, usuario y empresa son UUID. El de alerta es numérico.
- **Borrado lógico:** las cámaras no se eliminan, se desactivan, porque las tablas dependientes tienen `ON DELETE CASCADE` y borrar una cámara eliminaría todo su historial.
- Errores: 404 si el recurso no existe, 409 si el cambio de estado no es válido, 422 si el cuerpo no cumple las validaciones.

### 7.2 Estados de una alerta

| Estado | Significado |
|---|---|
| `active` | Generada y sin atender |
| `acknowledged` | Reconocida por un técnico |
| `resolved` | Resuelta por un técnico |

Solo se permite el orden `active → acknowledged → resolved`. Cada cambio guarda quién y cuándo, y agrega una fila en `alert_audit`.

Severidades válidas (restricción de la BD): `low`, `medium`, `high`, `critical`.

### 7.3 Reglas HACCP

| Campo | Rango o valores | Valor por defecto |
|---|---|---|
| `max_absolute_temp` | -50 a 50 °C | 4.0 |
| `min_absolute_temp` | -50 a 50 °C (debe ser menor que el máximo) | -30.0 |
| `tolerance_time_min` | 1 a 1440 min | 15 |
| `severity` | `low`, `medium`, `high`, `critical` | `medium` |
| `active` | verdadero o falso | verdadero |

Al guardar, `review_date` se actualiza a la fecha y hora actuales. Una cámara debería tener una sola regla.

### 7.4 Métricas en vivo (`/dashboard/live`)

| Campo | Cómo se calcula |
|---|---|
| `active_chambers` | Cámaras con `active = true` |
| `active_alerts` | Alertas con estado `active` |
| `total_consumption_kw` | Suma de la última lectura de cada cámara en el último minuto (potencia actual). Las cámaras sin lecturas en ese minuto no cuentan |
| `estimated_savings_clp` | Suma de `expected_saving_amount` de la tanda más reciente de recomendaciones `pending` |

## 8. Autenticación y permisos

Aún no está implementada. El plan es un login en `routes/auth.py` que emita un JWT (`pyjwt`, contraseñas con `passlib`/bcrypt) y una dependencia que valide el rol (`gerente` o `tecnico`). Mientras tanto:

- Los endpoints no validan rol; cada uno indica el permiso previsto en un comentario.
- `acknowledge` y `resolve` reciben `id_user` en el cuerpo; deberá salir del token.
- `POST /chambers` recibe `id_company` en el cuerpo; deberá salir del token.
- El login del dashboard es una simulación (`AuthContext.jsx`) y no usa este servicio.

## 9. Ejecución

**Local** (desde `microservices/ingesta`):

```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8000     # API
python mqtt_client.py                     # suscriptor MQTT (proceso aparte)
```

**Docker:**

```bash
docker build -t ingesta .
docker run --env-file ../../.env -p 8000:8000 ingesta
```

Para que el dashboard lo encuentre, el servicio debe llamarse `ingesta-service` en la red de Docker (así está definido en `nginx.conf` del dashboard).

## 10. Pendientes e inconsistencias conocidas

1. **El suscriptor MQTT no se inicia en el contenedor.** El `Dockerfile` solo ejecuta `uvicorn main:app`; `mqtt_client.py` hay que correrlo como proceso aparte o iniciarlo desde `main.py`.
2. **Las lecturas no llegan a Kafka.** `mqtt_client.py` guarda en la BD pero no llama a `publish_sensor_data`, así que los workers no reciben datos en `sensor.raw`.
3. **El archivo del productor tiene un error de escritura:** se llama `kafka_propducer.py`. El README lo llama `kafka_producer.py`.
4. **Los nombres de campos no coinciden entre servicios.** El productor Kafka usa `chamber_id` y `recorded_at` (incluso `data["chamber_id"]`), mientras que el schema MQTT y `worker-predictivo` usan `id_chamber` y `timestamp`. Hay que unificarlos.
5. **El README de ingesta menciona Redis** (evento `nuevos_datos`), pero el código usa Kafka.
6. **`ingestion_log` no se usa.** Las lecturas inválidas solo se imprimen; deberían registrarse en esa tabla.
7. **Valores incompatibles con la BD:**
   - `worker-haccp` guarda severidades como `warning`, pero la tabla solo acepta `low`, `medium`, `high`, `critical`.
   - `worker-predictivo` guarda `risk_level` en mayúsculas (`CRITICO`, `ALTO`, etc.), que la tabla `predictions` también rechaza.
8. **`worker-optimizacion/db.py` no coincide con `init.sql`.** Usa `saving_recommendations`, `chamber_id`, `recorded_at` y `price_id`, pero el esquema define `saving_recommendation`, `id_chamber`, `timestamp` e `id_price`. Mientras no se alinee, la métrica de ahorro quedará en 0.
9. **`models.py` desactualizado:** `Sensor` no tiene `mcu_id`, `firmware` ni `last_calibration`.
10. **Restricción de unicidad:** falta `UNIQUE (id_chamber)` en `haccp_rules` (el modelo de `worker-haccp` sí lo declara).
11. **CORS:** `main.py` permite cualquier origen con credenciales. Conviene limitarlo a los orígenes reales antes de producción.
12. **Rutas que el dashboard usa y no están en el README:** `/panel/*` (panel técnico) y `/gemini/chat`.
13. **Pruebas:** el README prevé `tests/test_api.py` y `tests/test_mqtt.py`; aún no están.