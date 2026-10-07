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

## Puesta en marcha

```bash
cp .env.example .env
docker compose up --build
```

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
