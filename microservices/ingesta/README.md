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
