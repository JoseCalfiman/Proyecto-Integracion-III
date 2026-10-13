# Manual técnico

> **Estado:** Borrador
> **Área SWEBOK:** KA4 — Software Construction
> **Responsable:** Equipo completo
> **Última actualización:** 2026-10-06
> **Documentos relacionados:** [Operaciones](../06-operaciones/despliegue.md), [Arquitectura](../02-arquitectura/arquitectura.md)

## 1. Propósito

Explicar cómo está construido el sistema, cómo se levanta y cómo se trabaja en él.

## 2. Stack tecnológico

| Capa | Tecnología |
|------|-----------|
| IoT | ESP32 + MQTT (Wokwi) |
| Ingesta / API | Python 3, FastAPI, Paho MQTT, Pydantic, SQLAlchemy |
| Mensajería | Apache Kafka (KRaft), Mosquitto |
| Workers | Python, scikit-learn, Prophet, APScheduler |
| Persistencia | TimescaleDB / PostgreSQL 16 |
| Frontend | React, Vite, Tailwind, Axios |
| Contenedores | Docker, Docker Compose |

## 3. Estructura del repositorio

```
Proyecto-Integracion-III/
├── database/            # init.sql, seeds.sql, migrations/
├── docs/                # Documentación SWEBOK (este directorio)
├── kafka/               # topics-setup.sh
├── microservices/       # ingesta, worker-predictivo, worker-haccp,
│                        # worker-optimizacion, dashboard
├── mosquitto/           # mosquitto.conf, pwfile, acl.conf
├── scripts/             # utilidades
├── tests/               # pruebas transversales
├── wokwi/               # sketch ESP32
├── docker-compose.yml
├── Makefile
└── README.md
```

## 4. Puesta en marcha

```bash
# 1. Configurar variables de entorno
cp .env.example .env

# 2. Levantar la plataforma
docker compose up --build
```

Servicios publicados: dashboard `:80`, ingesta `:8001`, TimescaleDB `:5432`,
Mosquitto `:1883`, Kafka `:9092`.

## 5. Convenciones de código

- Sin comentarios salvo que aporten contexto no evidente.
- Estilo Python (PEP 8) y ESLint/Oxlint para el frontend.
- Un microservicio por responsable, con su propio `Dockerfile` y `requirements.txt`.
- Commits con prefijos (`feat:`, `fix:`, `docs:`).

## 6. Pruebas

- Backend: `pytest` (ver [`../05-pruebas/plan-de-pruebas.md`](../05-pruebas/plan-de-pruebas.md)).
- Frontend: pruebas de componentes y API (pendiente).

## 7. Problemas conocidos

Ver "Observaciones del estado actual" en
[`../02-arquitectura/diagrama-software.md`](../02-arquitectura/diagrama-software.md)
(`.env` ausente, Dockerfile del dashboard vacío, menciones a Redis sin definir).
