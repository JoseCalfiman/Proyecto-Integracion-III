# Worker HACCP

Responsable: Eduardo Domínguez

Worker que consume alertas predictivas desde Kafka en el tópico `sensor.anomaly`,
las valida contra la regla HACCP activa de cada cámara y, si cumplen las
condiciones, publica la alerta final en `haccp.alerts` y la persiste en la
tabla `generated_alerts` junto con la auditoría correspondiente en
`alert_audit_log`.

## Reglas HACCP y MER oficial

El módulo usa los nombres oficiales del esquema:

- `max_absolute_temp` y `min_absolute_temp`
- `id_chamber`, `id_user_modified`, `id_rule`
- `active` en lugar de `is_active`

Estas convenciones se aplican en `haccp_validator.py`, `crud.py` y `models.py`.

## Flujo del worker

1. El consumidor escucha `sensor.anomaly`.
2. Por cada mensaje, obtiene la regla activa con `get_active_rule(id_chamber)`.
3. Ejecuta `validar_haccp(alerta_predictiva, regla_camara)`.
4. Si la validación pasa:
   - guarda la alerta en `generated_alerts`
   - publica el evento en `haccp.alerts`
   - registra la acción en `alert_audit_log`

Al iniciar el consumidor, SQLAlchemy crea `alert_audit_log` en PostgreSQL si no
existe. La tabla guarda `audit_id`, `alert_id`, `user_id`, `action`, `detail` y
`action_at`; las referencias de alerta y usuario apuntan a `generated_alerts` y
`users`.

También crea `generated_alerts` si no existe. Cada alerta persiste `alert_id`,
`chamber_id`, `prediction_id`, `haccp_rule_id`, `alert_type`, `severity`, `status`,
`message` y `generated_at`.
5. Si la validación falla, se registra como `falso positivo`.

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
docker run --rm worker-haccp
```

## Dependencias

```txt
confluent-kafka==2.15.0
sqlalchemy==2.0.30
psycopg2-binary==2.9.9
python-dotenv==1.0.1
```




