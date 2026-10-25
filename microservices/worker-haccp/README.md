# Worker HACCP

Responsable: Eduardo Domínguez

Worker que consume alertas predictivas desde Kafka en el tópico `sensor.anomaly`,
las valida contra la regla HACCP activa de cada cámara y, si cumplen las
condiciones, persiste la alerta en `generated_alerts` junto con su auditoría
en `alert_audit`, confirma PostgreSQL y publica la alerta final en `haccp.alerts`.

## Conexión a PostgreSQL/TimescaleDB

El Worker requiere PostgreSQL/TimescaleDB y acepta estas variables:

- `DATABASE_URL`, si está definida, tiene prioridad.
- Si no, se construye la conexión con `DB_HOST`, `DB_PORT`, `DB_NAME`,
  `DB_USER` y `DB_PASSWORD`.

Si no hay una URL o faltan variables `DB_*`, el Worker informa el problema y no
inicia el consumidor. Las credenciales deben proporcionarse mediante la
configuración del entorno; no deben escribirse en el código.

## Esquema compartido

El Worker utiliza las tablas existentes `chambers`, `users`, `haccp_rules`,
`predictions`, `generated_alerts` y `alert_audit`, definidas en
`database/init.sql`. Los identificadores de cámaras y usuarios son UUID; los
identificadores de reglas, predicciones, alertas y auditorías son BIGINT.
El Worker no crea tablas ni ejecuta migraciones: el esquema debe estar
provisionado antes de iniciarlo.

Las reglas activas se filtran por `active` y, si hay varias para una cámara, se
selecciona la de `review_date` más reciente, igual que el criterio de consulta
de reglas de Ingesta. Si dos reglas activas empatan en `review_date`, el orden
elegido por la base de datos no está definido; un criterio de desempate sigue
pendiente de decisión de negocio. Para persistir una alerta se utiliza la severidad
configurada en la regla activa, compatible con los valores admitidos por
PostgreSQL (`low`, `medium`, `high`, `critical`).

Los mensajes inválidos y los rechazos permanentes de datos o restricciones de
PostgreSQL se registran, se descartan y se confirma su offset para evitar que
bloqueen el grupo. Los fallos transitorios de base de datos reciben hasta tres
intentos con espera incremental; si persisten, el proceso se detiene sin
confirmar el offset para que el mensaje pueda entregarse de nuevo. Otros errores
de SQLAlchemy no clasificados como transitorios se propagan sin confirmar el
offset.

## Flujo del worker

1. El consumidor escucha `sensor.anomaly` y valida su contrato.
2. Obtiene la regla activa para la cámara mediante `get_active_rule`.
3. Ejecuta `evaluate_predictive_event(payload, rule)`.
4. Si hay infracción, inserta la alerta y agrega la auditoría `created` en la misma transacción.
5. Confirma ambos registros mediante commit de PostgreSQL.
6. Publica en `haccp.alerts` y espera confirmación de entrega Kafka.
7. Confirma el offset de entrada de forma síncrona.

Sin regla activa o sin infracción, no persiste ni publica y confirma el offset.
Una regla activa inválida detiene el procesamiento sin confirmar el offset.

## Persistencia de `generated_alerts` (tarea 51)

| Campo | Valor persistido |
|---|---|
| `id_chamber` | UUID normalizado del evento |
| `id_prediction` | Entero positivo dentro del rango BIGINT |
| `id_haccp_rule` | `id_rule` de la regla activa aplicada a esa cámara |
| `alert_type` | `haccp_violation` |
| `severity` | Severidad de la regla aplicada: `low`, `medium`, `high` o `critical` |
| `status` | `active` |
| `message` | Mensaje de la decisión HACCP |
| `generation_date` | Fecha UTC asignada al insertar; se reutiliza al publicar |

PostgreSQL/TimescaleDB es la base de despliegue. SQLite en memoria se utiliza
exclusivamente como sustituto en pruebas unitarias; no es una alternativa de despliegue.
El Worker valida el formato UUID y el tipo/rango del ID de predicción. La existencia
de cámara, predicción y regla se garantiza mediante las claves foráneas de PostgreSQL,
sin consultas previas adicionales a predicciones. No se comprueba que la predicción
pertenezca a la misma cámara; las FK independientes no garantizan esa relación.

El manejador considera `IntegrityError` y `DataError` rechazos permanentes: registra,
descarta y confirma el offset, sin publicar. `DisconnectionError`, `InterfaceError`,
`OperationalError` y timeout SQLAlchemy reciben hasta tres intentos con esperas de
1 y 2 segundos. Si se agotan, se propaga `TransientDatabaseError` sin confirmar.
Los demás errores SQLAlchemy se registran y propagan sin confirmar. Al cerrar la
sesión se revierte la transacción pendiente; alerta y auditoría no se confirman por separado.
Un fallo Kafka se propaga sin confirmar el offset y no activa los reintentos de BD.

PostgreSQL y Kafka no comparten una transacción atómica. Si PostgreSQL confirma y
Kafka falla, reprocesar puede crear otra alerta. También puede duplicarse tras una
entrega Kafka seguida de un fallo al confirmar el offset, o si se pierde la respuesta
del commit PostgreSQL y se reintenta un commit cuyo resultado era incierto. No hay
outbox ni idempotencia. Una FK faltante se descarta incluso si su causa fuera que
el productor publicó antes de confirmar la predicción.

Las pruebas negativas inyectan errores para verificar transacciones, descarte,
reintentos, propagación y ausencia de publicación. No acreditan integridad referencial
real en SQLite. Quedan pendientes los casos negativos de FK en PostgreSQL aislado.

## Evidencia de integración real informada

El usuario reportó la validación de ALT-5 en Docker con PostgreSQL/TimescaleDB y Kafka:
`id_alert=5`, `id_prediction=2`, `id_haccp_rule=2`,
`id_chamber=55555555-5555-5555-5555-555555555555`, `severity=medium`, `status=active`.
La alerta fue publicada en `haccp.alerts` y visualizada en CryoMetric.
Este antecedente corresponde a la validación previa de la tarea 52; no es una
prueba de integración ejecutada durante el cierre documental de la tarea 51.

## Archivos clave

- `kafka_consumer.py`: suscripción y procesamiento del tópico `sensor.anomaly`
- `kafka_producer.py`: publicación del evento final en `haccp.alerts`
- `haccp_validator.py`: lógica de validación HACCP
- `crud.py`: acceso a reglas HACCP y creación por defecto
- `models.py`: modelos SQLAlchemy con el MER oficial
- `Dockerfile`: levantado del worker en contenedor

## Ejecutar con Docker

```bash
docker build -t worker-haccp .
docker run --rm --env-file .env worker-haccp
```

## Dependencias

```txt
confluent-kafka==2.15.0
sqlalchemy==2.0.30
psycopg2-binary==2.9.9
python-dotenv==1.0.1
```
