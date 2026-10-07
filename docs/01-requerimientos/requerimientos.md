# Requerimientos del software

> **Estado:** Borrador (priorización MoSCoW completa; especificación detallada pendiente)
> **Área SWEBOK:** KA1 — Software Requirements
> **Responsable:** Equipo completo
> **Última actualización:** 2026-10-06
> **Documentos relacionados:** [Casos de uso](casos-de-uso.md), [Arquitectura](../02-arquitectura/arquitectura.md)

## 1. Propósito

Definir, priorizar y gestionar los requisitos del sistema de monitoreo de
frigorífico inteligente. Sigue las actividades de SWEBOK: elicitación, análisis,
especificación, validación y gestión de requisitos.

## 2. Alcance

Cubre los requisitos funcionales y no funcionales derivados de los seis módulos
del proyecto (ingesta, worker predictivo, worker HACCP, worker optimización,
dashboard e IoT) y su priorización con la técnica **MoSCoW**.

## 3. Requisitos funcionales

| ID | Requisito | Módulo |
|----|-----------|--------|
| RF-01 | El dispositivo ESP32 debe publicar telemetría (temperatura y consumo) por MQTT en `sensor/raw` cada 10 s. | IoT |
| RF-02 | La ingesta debe validar el payload (Pydantic) con `chamber_id`, `temperature`, `consumption_kw` y `recorded_at`. | Ingesta |
| RF-03 | La ingesta debe persistir las lecturas válidas en TimescaleDB y registrar errores en `ingestion_log`. | Ingesta |
| RF-04 | La ingesta debe publicar el evento `sensor.raw` en Kafka. | Ingesta |
| RF-05 | El worker predictivo debe calcular la pendiente de temperatura y el tiempo restante, y publicar alertas en `sensor.anomaly`. | Predictivo |
| RF-06 | El worker HACCP debe validar la alerta contra `haccp_rules` y publicar en `haccp.alerts`. | HACCP |
| RF-07 | El worker de optimización debe pronosticar consumo (Prophet), calcular ahorro y publicar en `optimization.reports`. | Optimización |
| RF-08 | El dashboard debe mostrar gráficos de temperatura/consumo en tiempo real y alertas históricas. | Dashboard |
| RF-09 | La API debe exponer autenticación, historial, alertas, HACCP y optimización. | Ingesta/API |
| RF-10 | El sistema debe ofrecer un asistente IA (Gemini) para consultar el estado de las cámaras. | Dashboard |

## 4. Requisitos no funcionales

| ID | Requisito | Categoría | Criterio |
|----|-----------|-----------|----------|
| RNF-01 | Latencia de ingesta extremo a extremo | Desempeño | < 5 s desde MQTT hasta persistencia |
| RNF-02 | Persistencia tras reinicios | Fiabilidad | Volúmenes Docker para DB y Kafka |
| RNF-03 | Despliegue reproducible | Portabilidad | Un solo `docker-compose up` |
| RNF-04 | Autenticación de acceso | Seguridad | JWT + contraseñas hasheadas |
| RNF-05 | Observabilidad | Operabilidad | Endpoint `/health` por servicio |
| RNF-06 | Módulo de operación | Conectividad | Internet solo para el dispositivo ESP32 |

## 5. Priorización MoSCoW (backlog consolidado)

| Prioridad | Módulos / Entregables |
|-----------|-----------------------|
| **Must have** | Docker-compose base, broker Mosquitto, Kafka (KRaft) y tópicos; suscriptor MQTT FastAPI, validación y persistencia en TimescaleDB (pipeline de ingesta); worker predictivo (regresión → tiempo restante → alerta); worker HACCP (validación → alerta final → persistencia); worker optimización (consumer → Prophet → publicación); ESP32/MQTT; dashboard operativo; despliegue Docker de los microservicios. |
| **Should have** | Volúmenes y persistencia, script de simulación, `.env.example` y README, config. Kubernetes, visualización del dashboard gerente, integración Kafka del worker de ingesta, logs de ingesta, pruebas unitarias, rutas, histórico de consumo, cálculo de ahorro, persistencia de recomendaciones, tabla `alert_audit_log`, reglas por defecto y documentación/investigaciones. |
| **Could have** | Health checks, login mock del dashboard, integración de Gemini (mock). |
| **Won't have (esta entrega)** | Alta disponibilidad multi-broker, autenticación federada, despliegue multi-nube. |

> La **priorización MoSCoW** fue acordada por el equipo y se usa para ordenar los
> sprints. Ver detalles por módulo en la sección de backlog del repositorio.

## 6. Validación

Los requisitos se validan mediante (pendiente de completar): revisión con el
cliente/experto de dominio, prototipos de dashboard y pruebas de aceptación
alineadas con los casos de uso.

## 7. Trazabilidad

Matriz requisito → caso de uso → diseño → prueba (pendiente). Enlaces:

- Casos de uso: [`casos-de-uso.md`](casos-de-uso.md)
- Arquitectura: [`../02-arquitectura/arquitectura.md`](../02-arquitectura/arquitectura.md)
- Plan de pruebas: [`../05-pruebas/plan-de-pruebas.md`](../05-pruebas/plan-de-pruebas.md)

## 8. Referencias

- SWEBOK v4, KA1 — Software Requirements.
- IEEE 830 / ISO/IEC/IEEE 29148 (ingeniería de requisitos).
