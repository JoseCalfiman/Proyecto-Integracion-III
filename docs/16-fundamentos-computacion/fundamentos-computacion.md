# Fundamentos de computación

> **Estado:** Borrador
> **Área SWEBOK:** KA16 — Computing Foundations
> **Responsable:** Equipo completo
> **Última actualización:** 2026-10-06
> **Documentos relacionados:** [Arquitectura](../02-arquitectura/arquitectura.md), [Modelo de datos](../03-diseno/modelo-datos.md)

## 1. Propósito

Registrar los fundamentos computacionales sobre los que se construye el sistema.

## 2. Temas y aplicación

| Tema (SWEBOK) | Aplicación en el proyecto |
|---------------|---------------------------|
| Arquitectura y organización | ESP32, contenedores, sistema distribuido |
| Estructuras y algoritmos | Buffer thread-safe, cálculo de pendiente, ventana deslizante |
| Fundamentos de programación | Python (backend/workers), JavaScript/React (frontend) |
| Sistemas operativos | Contenedores Linux/Docker |
| Gestión de bases de datos | PostgreSQL/TimescaleDB, SQLAlchemy, hypertables |
| Redes y comunicaciones | MQTT, HTTP/REST, red Docker |
| Factores humanos | UI/UX del dashboard |
| IA y ML | Regresión lineal, Prophet, asistente Gemini |

## 3. Redes y protocolos

- **MQTT** (Mosquitto, puerto 1883) para telemetría IoT.
- **Kafka** (protocolo binario, puerto 9092) para eventos.
- **HTTP/REST** (FastAPI, puerto 8001) hacia el dashboard.
- **PostgreSQL** (puerto 5432) para persistencia.

## 4. Notas

Detalles de algoritmos y estructuras por módulo quedan pendientes de ampliar.
