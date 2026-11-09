# Reglas de validación HACCP

Este documento describe los criterios implementados por el módulo `haccp_validator.py` del worker HACCP. Los valores son parámetros técnicos del proyecto; deben contrastarse con los requisitos sanitarios aplicables al producto y a la cámara antes de usarse como límites operativos definitivos.

## Health endpoint del Worker

El proceso de `kafka_consumer.py` inicia un servidor HTTP concurrente con el
consumidor Kafka. El puerto predeterminado es `8080`, configurable mediante
`HEALTH_PORT`; el contenedor expone ese puerto. El endpoint `GET /health`
devuelve JSON y HTTP `200` sólo cuando el loop del consumidor está operativo y
una comprobación efectiva de Kafka mediante `AdminClient.list_topics()` tuvo
éxito. La conectividad se comprueba en un hilo independiente cada 5 segundos,
con timeout de 3 segundos, de forma que la comprobación HTTP y la consulta de
metadata no bloqueen el procesamiento de mensajes.

Campos de `GET /health`:

| Campo | Significado |
|---|---|
| `status` | `starting` antes de que consumidor y chequeo de Kafka estén listos; `healthy` cuando ambos están operativos; `unhealthy` si el consumidor se detuvo, Kafka se detecta inaccesible o el consumidor devuelve un error Kafka no recuperado por un poll posterior. |
| `kafka_connected` | Resultado del último chequeo de metadata Kafka; inicia como `false`, y no se infiere de la creación del consumidor. |
| `last_processed_at` | Último procesamiento completado y offset confirmado, en UTC ISO 8601 (`Z`); `null` al iniciar. No requiere eventos recientes para mantener el estado healthy. |
| `consumer_operational` | Indica que el consumidor fue creado, suscrito y mantiene su loop activo. |

`/health` devuelve HTTP `503` durante el inicio o si el Worker no está
disponible, y `200` cuando está healthy. Un mensaje inválido/rechazado o un
fallo de procesamiento no actualizan `last_processed_at`. Un evento procesado
correctamente sí la actualiza después de que el manejador confirme su offset
sincrónicamente; los mensajes válidos sin infracción también cuentan como
procesados. Si falla una publicación Kafka, el evento no se considera terminado
y el timestamp no avanza.

También existe `GET /live`, independiente de la conectividad a Kafka: devuelve
HTTP `200` (`{"status":"alive","consumer_operational":true}`) mientras el loop
del consumidor sigue vivo, incluso durante una desconexión temporal del broker.
Devuelve `503` mientras inicia o si el consumidor se detuvo. No expone
credenciales ni detalles de configuración.

Ejemplo healthy:

```json
{
  "status": "healthy",
  "kafka_connected": true,
  "last_processed_at": "2026-10-24T23:36:13.918000Z",
  "consumer_operational": true
}
```

Ejemplo iniciando o sin disponibilidad:

```json
{
  "status": "starting",
  "kafka_connected": false,
  "last_processed_at": null,
  "consumer_operational": false
}
```

Prueba local (con las variables de configuración del Worker disponibles):

```powershell
$env:HEALTH_PORT = "8080"
python kafka_consumer.py
```

En otra terminal, consulta `http://localhost:8080/health` y
`http://localhost:8080/live`. Con Docker, publica el puerto además de configurar
las variables de base de datos y Kafka:

```powershell
docker run --rm --env-file .env -p 8080:8080 worker-haccp
```

Recomendación para una futura configuración Kubernetes (los manifiestos no son
modificados ni validados como despliegue por esta tarea):

- `readinessProbe`: `GET /health`, puerto `8080`; una desconexión Kafka retira
  al Worker del tráfico/disponibilidad sin reiniciarlo.
- `startupProbe` y `livenessProbe`: `GET /live`, puerto `8080`. Dar margen de
  inicio con `failureThreshold × periodSeconds`; la liveness no debe depender de
  Kafka para evitar reinicios repetidos por una caída temporal del broker.

## Umbrales predeterminados del validador

| Parámetro | Valor predeterminado | Significado |
| --- | ---: | --- |
| `max_temp_c` | 4 °C | Límite superior. Una lectura solo lo supera si es estrictamente mayor que 4 °C. |
| `min_temp_c` | -30 °C | Límite inferior. Una lectura solo queda por debajo si es estrictamente menor que -30 °C. |
| `warning_duration_seconds` | 900 s (15 min) | Duración mínima fuera del rango para declarar una alerta/violación. |
| `critical_duration_seconds` | 1800 s (30 min) | Duración desde la que la severidad se clasifica como crítica. |
| `critical_temp_c` | 6 °C | Temperatura desde la que una alerta puntual se clasifica como crítica. |
| `sample_interval_seconds` | 10 s | Intervalo predeterminado entre muestras al evaluar series. |

Los parámetros se encuentran en `DEFAULT_HACCP_RULE`. Los evaluadores permiten sobrescribirlos con un diccionario `rule`; `validar_haccp` también adapta una regla ORM o un diccionario de la base de datos.

## Evaluación de una lectura y su duración

`evaluate_temperature_rule(temperature_c, duration_seconds, rule)` considera fuera de rango una lectura mayor que el máximo o menor que el mínimo y aplica estas condiciones:

1. Si la temperatura está dentro del rango inclusivo [-30 °C, 4 °C], el resultado es `normal` y no hay alerta.
2. Si está fuera del rango pero la duración es inferior a 900 segundos, la severidad informativa es `warning`, aunque `is_alert` permanece en `false`.
3. Si permanece fuera del rango durante al menos 900 segundos, `is_alert` pasa a `true`.
4. Una alerta puntual se clasifica como `critical` si la temperatura alcanza 6 °C o si la duración alcanza 1800 segundos; de lo contrario es `warning`.

Con estos defaults, puede emitirse una alerta `warning` entre los 15 y 30 minutos si la temperatura es inferior a 6 °C. Una temperatura de 6 °C o más genera una alerta crítica al alcanzar los 15 minutos.

| Temperatura | Duración | Resultado predeterminado |
| ---: | ---: | --- |
| 4.0 °C o -30.0 °C | Cualquier duración | `normal`; ambos límites se incluyen en el rango |
| 4.1 °C | 899 s | Sin alerta; severidad `warning` |
| 4.1 °C | 900 s | Alerta `warning` |
| 6.0 °C | 900 s | Alerta `critical` por temperatura |
| -30.1 °C | 900 s | Alerta `warning` por estar debajo del mínimo |
| 4.1 °C | 1800 s | Alerta `critical` por duración |

## Evaluación de una serie de lecturas

`evaluate_temperature_series(temperatures, sample_interval_seconds, rule)` recorre las lecturas en orden y considera fuera de rango cada valor mayor que `max_temp_c` o menor que `min_temp_c`. Un valor dentro del rango cierra la secuencia fuera de rango actual. Para cada secuencia de `n` lecturas consecutivas fuera de rango, la duración calculada por la implementación es `(n + 1) × intervalo_de_muestreo`.

La duración de las secuencias detectadas se suma, incluso si se separan por lecturas dentro del rango. Si el total es menor que 900 s, `has_violation` es `false` y la severidad es `normal`; al alcanzar 900 s, `has_violation` es `true`. La severidad se marca crítica desde 1800 s de total. Este evaluador no usa `critical_temp_c`: la clasificación de la serie depende del tiempo total, no de la temperatura máxima.

El intervalo efectivo es el argumento `sample_interval_seconds` (10 s por defecto en la firma). Debe pasarse explícitamente cuando la cadencia de los datos sea distinta; si se pasa un valor falsy, el módulo recurre al intervalo configurado en la regla.

## Valores de la regla persistida en base de datos

El worker define una regla predeterminada para `haccp_rules` en `crud.py`. `validar_haccp` traduce sus campos `max_absolute_temp` y `min_absolute_temp` a los límites del validador, y convierte `tolerance_time_min` a segundos para `warning_duration_seconds`:

| Campo de base de datos | Valor predeterminado | Uso previsto |
| --- | ---: | --- |
| `max_absolute_temp` | 4.00 °C | Temperatura máxima absoluta de la cámara |
| `min_absolute_temp` | -30.00 °C | Temperatura mínima absoluta de la cámara |
| `tolerance_time_min` | 15 min | Tiempo de tolerancia de la regla |
| `severity` | `medium` | Severidad compatible con `haccp_rules` y `generated_alerts` |
| `active` | `true` | Indica que la regla está activa |

La evaluación legacy de lecturas y series convierte `tolerance_time_min` a una duración mínima en segundos. La decisión predictiva descrita abajo usa directamente la tolerancia en minutos y no convierte el tiempo restante en duración de exposición.

### Fallback cuando no existe regla activa

Si la consulta de reglas para una cámara termina correctamente y no devuelve una
regla activa, el Worker evalúa el evento con la configuración determinista de
`DEFAULT_RULE_VALUES`: `min_absolute_temp = -30.00 °C`,
`max_absolute_temp = 4.00 °C`, `tolerance_time_min = 15` y `severity = medium`.
La regla se usa sólo en memoria: no se inserta una fila en `haccp_rules` ni se
inventa un `id_rule`. Si hay infracción, la alerta se persiste con
`id_haccp_rule = NULL`, el `id_prediction` original, la severidad predeterminada
y su auditoría `created`; después sigue el flujo normal de publicación. Si no
hay infracción, no se persiste ni publica. En ambos casos se confirma el offset
y el consumidor continúa; antes de evaluar se registra un `WARNING` que incluye
el `id_chamber` y deja explícito el uso de la regla predeterminada.

Este fallback sólo aplica al resultado `None` de una consulta completada. Los
errores de conexión/SQLAlchemy siguen el tratamiento de errores de base de datos
y una regla activa inválida sigue siendo un error de configuración: ninguno de
esos casos se oculta ni se sustituye por defaults.

## Estado de integración

El consumidor valida el contrato de `sensor.anomaly` y obtiene la regla HACCP
activa para la cámara o utiliza el fallback predeterminado documentado si no la
hay. La decisión predictiva genera una alerta si se cumple
cualquiera de estas condiciones:

- `temperature < min_absolute_temp`
- `temperature > max_absolute_temp`
- `remaining_time_min <= tolerance_time_min`

Los límites de temperatura son inclusivos para el estado normal: una lectura
igual al mínimo o máximo no constituye por sí sola una infracción. El tiempo
restante igual a la tolerancia sí genera alerta. Si no se cumple ninguna
condición, no se persiste ni publica una alerta.

`remaining_time_min` es una predicción de tiempo hasta alcanzar el límite, no
una duración de exposición. Esta decisión no lo transforma en
`duration_seconds`. Los evaluadores legacy `evaluate_temperature_rule`,
`evaluate_temperature_series` y `validar_haccp` conservan su semántica para
lecturas/series y siguen trabajando con temperatura y duración.

La decisión utiliza los límites y tolerancia de la regla activa de la cámara o
los defaults sólo ante ausencia confirmada de una regla activa. Una regla activa
con parámetros requeridos nulos, no finitos, incompatibles, rango
invertido o tolerancia negativa se trata como error de configuración: el offset
no se confirma y el procesamiento se detiene para evitar un ciclo de reintentos
sin límite. La severidad persistida y publicada procede de la regla activa o del
fallback `medium`, valores admitidos por PostgreSQL.

## Contrato de `sensor.anomaly`

El evento contiene estos siete campos obligatorios:

| Campo | Tipo y restricción |
|---|---|
| `id_chamber` | UUID serializado como string; se normaliza a UUID |
| `id_prediction` | Entero BIGINT positivo de `predictions.id_prediction` |
| `temperature` | Número JSON finito; se normaliza a `float` |
| `remaining_time_min` | Número JSON finito no negativo; se normaliza a `float` |
| `severity` | `low`, `medium`, `high` o `critical`; se recortan espacios y normaliza a minúsculas |
| `risk_level` | `SIN_RIESGO`, `CRITICO`, `ALTO`, `MEDIO` o `BAJO`; se recortan espacios y normaliza a mayúsculas |
| `recorded_at` | Fecha y hora ISO 8601 parseable con separador `T`; se normaliza con `datetime.isoformat()` |

`id_prediction` debe ser un entero JSON, no booleano ni string, entre `1` y
`2**63 - 1`. Los campos numéricos no admiten booleanos, strings ni valores no
finitos (`NaN` o infinitos); `remaining_time_min` tampoco puede ser negativo.
El contrato no impone un rango físico adicional a `temperature`: la regla HACCP
activa determina si su valor constituye una infracción. `recorded_at` debe incluir
una fecha y hora real; si termina en `Z`, se representa como `+00:00` al
normalizarlo.

Ejemplo:

```json
{
  "id_chamber": "44444444-4444-4444-4444-444444444444",
  "id_prediction": 42,
  "temperature": 5.0,
  "remaining_time_min": 10.0,
  "severity": "medium",
  "risk_level": "MEDIO",
  "recorded_at": "2025-01-02T03:04:05+00:00"
}
```

El productor también conserva `chamber_id` como alias de compatibilidad. El
consumidor acepta `chamber_id` temporalmente cuando falta `id_chamber`, y
normaliza el identificador al campo interno `id_chamber`. Si se reciben ambos,
deben representar el mismo UUID; un `id_chamber` inválido no se sustituye con el
alias y dos identificadores distintos invalidan el mensaje.

El Worker Predictivo, mantenido por otro integrante, actualmente publica
`chamber_id` pero no incluye `id_prediction`. El consumidor requiere un
`id_prediction` BIGINT positivo, por lo que los eventos de ese productor siguen
siendo rechazados hasta coordinar e implementar esa compatibilidad en el
microservicio Predictivo. Esta tarea no modifica ese productor.

El consumidor registra con nivel `WARNING` los mensajes malformados o con
contrato incompleto/inválido, incluyendo el campo o motivo específico, los
descarta y confirma esos offsets según la política existente. No genera alertas
ni detiene el consumo por esos mensajes. No inventa `id_prediction`, no lo
sustituye por `None` ni busca otra predicción. Un evento válido se evalúa con
`temperature` y `remaining_time_min`; los errores de configuración de una regla
activa quedan sin confirmar para que puedan corregirse y reprocesarse.

## Referencias del código

- `microservices/worker-haccp/haccp_validator.py`: decisión predictiva en `evaluate_predictive_event`, umbrales predeterminados y evaluadores legacy.
- `microservices/worker-haccp/tests/test_haccp.py`: casos probados para el límite, la duración, la sobrescritura de reglas y series temporales.
- `microservices/worker-haccp/crud.py`: valores predeterminados de las reglas persistidas.
- `microservices/worker-haccp/models.py`: estructura de `HaccpRule`.
- `microservices/worker-haccp/kafka_consumer.py`: integración del worker con Kafka y la regla activa.

## Publicación de `haccp.alerts` (tarea 52)

Cada alerta persistida se publica con key igual a `id_chamber` (UUID canónico
codificado en UTF-8). El valor es JSON UTF-8 con estos campos:

| Campo | Tipo / origen |
|---|---|
| `id_alert` | Entero generado en `generated_alerts` |
| `id_chamber` | UUID como string |
| `id_prediction` | Entero de la predicción |
| `severity` | Severidad persistida de la regla activa |
| `status` | Estado persistido, inicialmente `active` |
| `message` | Mensaje de la decisión HACCP persistida |
| `generation_date` | Misma fecha persistida, ISO 8601 UTC con sufijo `Z` |
| `alert_type` | `haccp_violation`, conservado por compatibilidad |

El payload se obtiene de la alerta después de `flush` y antes de que el commit
expire el objeto ORM. La fecha procede del valor asignado a la alerta, nunca de
una fecha adicional del evento entrante ni de un reloj independiente al publicar.
La alerta y su auditoría `created` se confirman juntas en PostgreSQL antes de
intentar publicar. Los descartes no generan publicaciones.

El productor espera la entrega mediante callback y `flush` con un timeout explícito
de 10 segundos. Solo retorna con éxito si recibe un callback sin error y no quedan
mensajes pendientes. Un error inmediato, error de callback, timeout, ausencia de
confirmación o fallo de `flush` propaga `HaccpAlertPublicationError`. El consumidor
se detiene sin confirmar el offset de `sensor.anomaly`; no reintenta automáticamente
la persistencia por un fallo Kafka. El orden exitoso es: commit PostgreSQL,
confirmación Kafka y commit síncrono del offset.

No existe una transacción atómica entre PostgreSQL y Kafka. Si PostgreSQL confirma
y Kafka falla, la alerta y auditoría quedan persistidas. Al reiniciar, reprocesar el
evento puede crear otra alerta con otro ID. También puede repetirse una publicación
si Kafka entrega y el proceso cae antes del commit del offset. La key no deduplica.
Esta tarea no incorpora outbox, idempotencia ni cambios de esquema.

Las pruebas unitarias del productor simulan callbacks, mensajes pendientes y errores;
las de procesamiento verifican contrato, fecha, descartes y orden de confirmación.
SQLite en memoria sigue siendo únicamente el sustituto de las pruebas existentes.
Las comprobaciones adicionales de entrega y offsets reales requieren autorización
para usar el entorno Docker aislado con Kafka y PostgreSQL/TimescaleDB. La evidencia
previa informada se registra en la sección de persistencia siguiente.


## Persistencia de `generated_alerts` (tarea 51)

El despliegue utiliza PostgreSQL/TimescaleDB. SQLite en memoria se limita a pruebas
unitarias y no sustituye la base real. `_persist_generated_alert` guarda:

| Campo | Origen y validación |
|---|---|
| `id_chamber` | UUID del evento, validado y normalizado |
| `id_prediction` | Entero positivo hasta `2**63 - 1`, obligatorio en el contrato |
| `id_haccp_rule` | `id_rule` de la regla activa; `NULL` si se usó el fallback en memoria |
| `alert_type` | Valor fijo `haccp_violation` |
| `severity` | Regla aplicada, con valor `low`, `medium`, `high` o `critical` |
| `status` | Valor inicial `active` |
| `message` | Mensaje de `evaluate_predictive_event` |
| `generation_date` | `datetime.now(timezone.utc)` asignado al objeto insertado |

`flush` inserta la alerta y obtiene `id_alert`; `_persist_audit` agrega la auditoría
`created`. El commit confirma ambos registros juntos. La instantánea para Kafka se
construye desde el objeto insertado antes de que expire por el commit, conservando
su fecha como ISO 8601 UTC. Después del commit se publica en Kafka y, solo tras la
confirmación de entrega, se confirma el offset. Un fallo anterior al commit revierte
la transacción pendiente al cerrar la sesión y no publica en Kafka.

Las FK PostgreSQL verifican la existencia de `chambers.id_chamber`,
`predictions.id_prediction` y `haccp_rules.id_rule`. No se consulta previamente la
existencia de la predicción ni se comprueba que pertenezca a la misma cámara.
La regla se obtiene filtrando por cámara y estado activo. Las pruebas SQLite no
habilitan FK ni se presentan como evidencia de integridad referencial real.

### Política de errores vigente

| Resultado o error | Comportamiento y offset |
|---|---|
| Contrato inválido, UUID incorrecto o campo obligatorio ausente | Registra y descarta; confirma offset |
| Sin regla activa | Emite `WARNING` con `id_chamber`, evalúa con defaults y continúa |
| Sin infracción, incluso con regla predeterminada | No persiste ni publica; confirma offset |
| Regla activa inválida | Registra y propaga; no confirma |
| `IntegrityError` o `DataError` | Registra y descarta; confirma offset sin publicar |
| `DisconnectionError`, `InterfaceError`, `OperationalError`, timeout SQLAlchemy | Hasta tres intentos, con esperas de 1 y 2 segundos; agotamiento propaga `TransientDatabaseError` sin confirmar |
| Otros errores SQLAlchemy | Registra y propaga; no confirma |
| Error de publicación Kafka | Propaga; no confirma; la transacción PostgreSQL ya está confirmada |

La clasificación no distingue las causas particulares de `IntegrityError`: una FK
faltante se descarta aunque provenga de una predicción todavía no confirmada por el
productor. La publicación debe realizarse después de confirmar esa predicción.
Los reintentos no aseguran ausencia de duplicados si PostgreSQL confirmó pero se
perdió la respuesta del commit. Se mantienen además los riesgos PostgreSQL–Kafka
descritos en la tarea 52; no se incorporan outbox ni idempotencia.

### Cobertura y validaciones externas pendientes

Las pruebas negativas inyectan `IntegrityError`, `DataError` y errores SQLAlchemy en
el flush de la alerta, la inserción de auditoría o el commit. Verifican ausencia de
confirmación parcial y publicación, logs y la política de offsets. También simulan
un fallo transitorio antes del commit seguido de recuperación. Estas pruebas
verifican control transaccional y tratamiento de excepciones, no errores reales de
FK PostgreSQL ni commits de resultado incierto.

Queda pendiente validar en PostgreSQL aislado el rechazo de una predicción
inexistente y de referencias eliminadas concurrentemente. No se han ejecutado estos
casos negativos reales durante este cierre.

### Evidencia real previa informada por el usuario

La validación de la tarea 52 en Docker con Kafka y PostgreSQL/TimescaleDB generó
ALT-5: `id_alert=5`, `id_prediction=2`, `id_haccp_rule=2`,
`id_chamber=55555555-5555-5555-5555-555555555555`, `severity=medium`, `status=active`.
El usuario confirmó su publicación en `haccp.alerts` y visualización en CryoMetric.
Se registra como antecedente de integración exitosa; no como una nueva ejecución
real realizada durante esta intervención.
