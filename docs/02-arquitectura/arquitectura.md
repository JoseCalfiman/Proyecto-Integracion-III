# Arquitectura de software

> **Estado:** Borrador
> **Área SWEBOK:** KA2 — Software Architecture
> **Responsable:** Equipo completo
> **Última actualización:** 2026-10-06
> **Documentos relacionados:** [Diagrama de software](diagrama-software.md), [Modelo de datos](../03-diseno/modelo-datos.md)

## 1. Propósito

Documentar la estructura de alto nivel del sistema: componentes, responsabilidades,
interfaces, estilos arquitectónicos y decisiones de diseño, siguiendo las vistas y
puntos de vista de la KA2 de SWEBOK.

## 2. Estilo arquitectónico

- **Microservicios** desplegados con Docker Compose sobre la red `frigorifico-net`.
- **Orientada a eventos** con Apache Kafka como bus asíncrono.
- **Publish/Subscribe** con MQTT (Mosquitto) en el borde (edge).
- **Capas** en el dashboard (presentación React → API REST → servicios).

## 3. Vistas

| Vista (SWEBOK) | Artefacto |
|----------------|-----------|
| Contexto | [`diagrama-software.md`](diagrama-software.md) |
| Componentes y conectores | Tópicos Kafka y flujo MQTT→Kafka→DB |
| Datos | [`../03-diseno/modelo-datos.md`](../03-diseno/modelo-datos.md) |
| Despliegue | [`../06-operaciones/despliegue.md`](../06-operaciones/despliegue.md) |

## 4. Componentes

Ver tabla de componentes y diagrama en
[`diagrama-software.md`](diagrama-software.md).

## 5. Interfaces

| Interfaz | Tecnología | Contrato |
|----------|-----------|----------|
| Dispositivo → Plataforma | MQTT `sensor/raw` | JSON con `chamber_id`, `temperature`, `consumption_kw`, `recorded_at` |
| Ingesta → Bus | Kafka `sensor.raw` | Evento de lectura validada |
| Predictivo → Bus | Kafka `sensor.anomaly` | `chamber_id`, `remaining_time_min`, `temperature` |
| HACCP → Bus | Kafka `haccp.alerts` | Alerta sanitaria validada |
| Optimización → Bus | Kafka `optimization.reports` | Reporte de ahorro |
| Dashboard → API | REST `/api/v1` | JSON (FastAPI + Swagger) |

## 6. Atributos de calidad (ISO/IEC 25010)

Escalabilidad, tolerancia a fallos (los workers continúan si la DB no está
disponible), mantenibilidad por microservicio y seguridad.

## 7. Decisiones de arquitectura (ADR)

| ID | Decisión | Estado |
|----|----------|--------|
| ADR-01 | Usar Kafka en modo KRaft (sin ZooKeeper) | Aceptada |
| ADR-02 | TimescaleDB como base de series de tiempo | Aceptada |
| ADR-03 | Mosquitto como broker MQTT de borde | Aceptada |
| ADR-04 | Prophet para predicción de consumo | Aceptada |

> Las ADR se documentan de forma extendida en `docs/02-arquitectura/adr/`
> (pendiente de crear).

## 8. Evaluación

Evaluación de la arquitectura (escenarios de atributos de calidad, ATAM)
pendiente de completar.
