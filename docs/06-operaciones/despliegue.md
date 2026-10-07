# Operaciones y despliegue

> **Estado:** Pendiente
> **Área SWEBOK:** KA6 — Software Engineering Operations
> **Responsable:** José Calfimán
> **Última actualización:** 2026-10-06
> **Documentos relacionados:** [Manual técnico](../04-construccion/manual-tecnico.md)

## 1. Propósito

Documentar el despliegue, la operación, el monitoreo y la infraestructura como
código del sistema (DevOps).

## 2. Servicios (`docker-compose.yml`)

| Servicio | Imagen / build | Puerto | Volumen |
|----------|----------------|:------:|---------|
| mosquitto | eclipse-mosquitto:2 | 1883 | mosquitto_data/log |
| kafka | apache/kafka (KRaft) | 9092 | kafka_data |
| kafka-init | apache/kafka | — | topics-setup.sh |
| timescaledb | timescale/timescaledb:pg16 | 5432 | timescaledb_data |
| ingesta | build ./microservices/ingesta | 8001→8000 | — |
| worker-predictivo | build | — | — |
| worker-haccp | build | — | — |
| worker-optimizacion | build | — | — |
| dashboard | build | 80 | — |

Red: `frigorifico-net` (bridge).

## 3. Infraestructura como código

- Docker Compose como definición de infraestructura.
- Carpeta `microservices/dashboard/kubernetes` (Kubernetes) — Borrador.

## 4. Operación

- Levantar: `docker compose up --build -d`.
- Logs: `docker compose logs -f <servicio>`.
- Detener: `docker compose down`.

## 5. Monitoreo y salud (Pendiente)

Health checks por servicio, endpoint `/health`, métricas y alertas operativas
(rol del **Could have** en MoSCoW).

## 6. CI/CD (Pendiente)

Pipeline de build, test y publicación de imágenes.
