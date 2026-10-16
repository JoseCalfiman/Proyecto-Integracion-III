# Worker HACCP

Responsable: Eduardo Domínguez

Worker que consume alertas predictivas desde Kafka en el tópico `sensor.anomaly`,
las valida contra la regla HACCP activa de cada cámara y, si cumplen las
condiciones, publica la alerta final en `haccp.alerts` y la persiste en la
tabla `generated_alerts` junto con la auditoría correspondiente en
`alert_audit`.

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

1. El consumidor escucha `sensor.anomaly`.
2. Por cada mensaje, obtiene la regla activa con `get_active_rule(id_chamber)`.
3. Ejecuta `validar_haccp(alerta_predictiva, regla_camara)`.
4. Si la validación pasa:
   - guarda la alerta en `generated_alerts`
   - publica el evento en `haccp.alerts`
   - registra la acción en `alert_audit`
5. Si la validación falla, no se genera una alerta.

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
