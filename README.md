# Proyecto Integración III — Monitoreo de Frigorífico Inteligente

Plataforma distribuida (microservicios + IoT) para el monitoreo de temperatura y
consumo eléctrico de cámaras de frío, con analítica predictiva, validación HACCP y
dashboard.

## Documentación

Toda la documentación del proyecto se centraliza en [`docs/`](docs/), organizada
según el estándar **IEEE SWEBOK v4.0** (18 áreas de conocimiento).

➡️ **Índice central de documentación: [`docs/README.md`](docs/README.md)**

## Estructura del repositorio

```
database/          Esquema y datos iniciales (TimescaleDB)
docs/              Documentación (SWEBOK)
kafka/             Configuración de tópicos
microservices/     ingesta, worker-predictivo, worker-haccp,
                   worker-optimizacion, dashboard
mosquitto/         Configuración del broker MQTT
scripts/           Utilidades
tests/             Pruebas transversales
wokwi/             Sketch ESP32
docker-compose.yml Orquestación de servicios
```

## Requisitos previos

- Docker Desktop (en Windows requiere WSL2)
- Python

## Instalación

1. Tener el repositorio para trabajar.
2. Crear tu archivo de variables de entorno (copia el de `.env.example` a tu `.env`
   y completa los valores).
3. Generar las credenciales de Mosquitto (existe de momento un `pwfile` en la
   carpeta `mosquitto`, pero elimínalo y crea el tuyo propio con tus valores).

   El broker exige usuario/contraseña (no permite conexiones anónimas) y tiene un
   control de acceso por tópico (`mosquitto/acl.conf`) con 3 roles: `esp32` (solo
   publica en `sensor/raw`), `ingesta` (solo lee `sensor/raw`) y `admin` (acceso
   total, para pruebas).

   Genera el archivo de contraseñas con `mosquitto_passwd` (no hace falta tener
   Mosquitto instalado, se usa la propia imagen de Docker):

   ```bash
   docker run -it --rm -v "${PWD}/mosquitto:/mosquitto/config" eclipse-mosquitto:2 mosquitto_passwd -c /mosquitto/config/pwfile esp32
   docker run -it --rm -v "${PWD}/mosquitto:/mosquitto/config" eclipse-mosquitto:2 mosquitto_passwd /mosquitto/config/pwfile ingesta
   docker run -it --rm -v "${PWD}/mosquitto:/mosquitto/config" eclipse-mosquitto:2 mosquitto_passwd /mosquitto/config/pwfile admin
   ```

   Te va a pedir la contraseña de cada usuario por teclado. Usa las mismas
   contraseñas que pusiste en las variables `MQTT_ESP32_PASSWORD`,
   `MQTT_INGESTA_PASSWORD` y `MQTT_ADMIN_PASSWORD` de tu `.env`, para que coincidan.
   Si tienes problemas de permisos en Windows pon este comando:

   ```bash
   docker run -it --rm -v "${PWD}/mosquitto:/mosquitto/config" eclipse-mosquitto:2 chmod 644 /mosquitto/config/pwfile
   ```

## Levantar el proyecto

1. Levantar los servicios (los microservicios `ingesta`, `worker-predictivo`,
   `worker-haccp`, `worker-optimizacion` y `dashboard` requieren un `Dockerfile`
   propio dentro de cada carpeta de `microservices`. Si alguno aún no existe, el
   comando fallará solo para ese servicio. Mientras tanto puedes levantar
   únicamente la infraestructura base):

   ```bash
   docker compose up -d
   # o solo la infraestructura base:
   docker compose up -d mosquitto kafka kafka-init timescaledb
   ```

2. Verificar que está corriendo:

   ```bash
   docker compose ps
   ```

3. Confirmar que los 4 tópicos de Kafka se crearon (debería mostrar `sensor.raw`,
   `sensor.anomaly`, `haccp.alerts`, `optimization.reports`):

   ```bash
   docker compose exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list
   ```

## Script de simulación (ESP32 falso)

Publica datos falsos de temperatura y consumo cada 10 segundos, simulando cámaras
reales, para poder probar el sistema sin hardware físico. Corre fuera de Docker,
directo en tu PC, por eso usa `localhost` (variable `MQTT_HOST_LOCAL` del `.env`)
para conectarse al broker, en vez del nombre `mosquitto` que usan los servicios que
sí corren dentro de la red de Docker.

Si faltan las librerías del script:

```bash
pip install paho-mqtt python-dotenv
```

## Comandos útiles

- `docker compose up -d`: levanta todos los servicios en segundo plano.
- `docker compose ps`: muestra el estado de los contenedores.
- `docker compose stop`: detiene los contenedores sin borrarlos.
- `docker compose down`: detiene y elimina los contenedores (los datos persisten).
- `docker compose down -v`: detiene, elimina contenedores y borra los datos/volúmenes.

## Flujo de trabajo Git

Ramas: `main` (estable) → `develop` (integración) → `feature/x-microservicio`
(trabajo individual). Cada persona trabaja en su rama `feature/` y hace Pull Request
hacia `develop` cuando su parte funciona.

Prefijos de commit sugeridos: `feat:`, `fix:`, `docs:`.

```text
feat: agrega endpoint de ingesta
fix: corrige cálculo de pendiente
docs: actualiza README del worker predictivo
```
