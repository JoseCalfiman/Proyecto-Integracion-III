# Diagrama de software

> **Estado:** Borrador
> **Área SWEBOK:** KA2 — Software Architecture
> **Responsable:** Equipo completo
> **Última actualización:** 2026-10-06
> **Documentos relacionados:** [Arquitectura](arquitectura.md)

## Vista general de la arquitectura

```mermaid
flowchart LR
    subgraph EXTERNO[Fuentes externas]
        SENSORES[Sensores / ESP32 / Wokwi]
        USUARIO[Gerente o tecnico]
        GEMINI[Google Gemini]
    end

    subgraph PLATAFORMA[Plataforma frigorifico]
        MQTT[Broker MQTT\nMosquitto\n1883]
        INGESTA[Ingesta + API REST\nFastAPI + Paho MQTT\n:8000]
        KAFKA[Apache Kafka\n9092]
        KINIT[kafka-init\nCrea topics]

        subgraph WORKERS[Procesamiento en segundo plano]
            PRED[Worker predictivo\nRegresion / alertas]
            HACCP[Worker HACCP\nValidacion de reglas]
            OPT[Worker optimizacion\nBuffer + Prophet + scheduler]
        end

        DASH[Dashboard React + Vite\nNginx en produccion\n:80]
        DB[(TimescaleDB / PostgreSQL\n5432)]
    end

    SENSORES -->|MQTT sensor/raw| MQTT
    MQTT -->|Suscripcion y validacion JSON| INGESTA
    INGESTA -->|Lecturas validas y logs| DB
    INGESTA -.->|Eventos sensor.raw\n(si se publica)| KAFKA

    KINIT --> KAFKA
    KAFKA -->|sensor.raw| PRED
    KAFKA -->|sensor.raw / alertas| HACCP
    KAFKA -->|sensor.raw| OPT

    PRED -->|Alertas y resultados| DB
    HACCP -->|Alertas HACCP y logs| DB
    OPT -->|Reportes y recomendaciones| DB
    OPT -->|optimization.reports| KAFKA
    USUARIO -->|HTTPS / HTTP| DASH
    DASH -->|REST /api/v1| INGESTA
    INGESTA -->|Consultas y escrituras| DB
    INGESTA -->|Contexto para chat| GEMINI
    GEMINI -->|Respuesta IA| INGESTA
```

## Componentes

| Componente | Responsabilidad | Tecnologia |
|---|---|---|
| Sensores / Wokwi | Generar mediciones de temperatura y consumo | ESP32 / MQTT |
| Mosquitto | Recibir y distribuir telemetria | MQTT, puerto 1883 |
| Ingesta | Validar payloads y guardar lecturas y errores | Python, FastAPI, Paho MQTT |
| Kafka | Transporte asincrono de eventos | Apache Kafka, puerto 9092 |
| Worker predictivo | Analizar tendencias y anticipar fallas | Python, regresion lineal |
| Worker HACCP | Validar limites y registrar alertas | Python, reglas HACCP |
| Worker optimizacion | Predecir consumo y generar recomendaciones | Python, Prophet, APScheduler |
| TimescaleDB | Persistir lecturas, alertas, usuarios y reportes | PostgreSQL + TimescaleDB |
| API REST | Exponer autenticacion, historial, alertas, HACCP y optimizacion | FastAPI dentro de ingesta |
| Dashboard | Interfaz web para gerentes y tecnicos | React, Vite, Axios |

## Topics Kafka

- `sensor.raw`: lecturas de sensores.
- `sensor.anomaly`: anomalias detectadas.
- `haccp.alerts`: alertas HACCP.
- `optimization.reports`: reportes de optimizacion.

## Despliegue

El archivo `docker-compose.yml` define los contenedores de Mosquitto, Kafka,
`kafka-init`, TimescaleDB, ingesta, los workers y el dashboard dentro de la
red `frigorifico-net`. Los puertos publicados son `80`, `1883`, `5432`,
`8001` y `9092`.

## Observaciones del estado actual

- El flujo MQTT hacia TimescaleDB esta implementado en `ingesta/mqtt_client.py`.
- El worker de optimizacion consume `sensor.raw`, persiste el reporte y publica
  `optimization.reports`.
- El repositorio no contiene un archivo `.env`; es necesario configurarlo antes
  de levantar todo el `docker-compose.yml`.
- El `Dockerfile` del dashboard esta vacio, por lo que el servicio dashboard no
  puede construirse con Docker hasta completarlo.
- El README del worker HACCP menciona Redis, pero Redis no aparece definido en
  `docker-compose.yml`; el diagrama representa Kafka, que es el broker definido
  actualmente en la composicion.
