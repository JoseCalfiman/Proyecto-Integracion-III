# Plan de proyecto

> **Estado:** Borrador
> **Área SWEBOK:** KA9 — Software Engineering Management
> **Responsable:** José Calfimán (Scrum Master)
> **Última actualización:** 2026-10-06
> **Documentos relacionados:** [Requerimientos](../01-requerimientos/requerimientos.md), [Proceso](../10-proceso/proceso.md)

## 1. Objetivo

Entregar una plataforma distribuida de monitoreo de frigorífico con ingesta,
analítica y dashboard, dentro del plazo de la asignatura.

## 2. Alcance

Ver priorización **MoSCoW** consolidada en
[`../01-requerimientos/requerimientos.md`](../01-requerimientos/requerimientos.md).

## 3. Equipo y roles

| Integrante | Rol / módulo |
|------------|--------------|
| José Calfimán | Infraestructura, Docker, Mosquitto/Kafka, dashboard, Scrum Master |
| Diego Curiqueo | Ingesta, API, modelos, persistencia |
| Matías Cárcamo | Worker predictivo |
| Ricardo Aravena | Worker optimización |
| Eduardo Domínguez | Worker HACCP |
| Alexis Monsalve | IoT (Wokwi/ESP32) y dashboard frontend |

## 4. Planificación

- Metodología: Scrum con sprints cortos (ver KA10).
- Backlog priorizado con MoSCoW.
- Entregables por microservicio en ramas `feature/`.

## 5. Riesgos

| Riesgo | Prob. | Impacto | Mitigación |
|--------|:----:|:------:|------------|
| Integración tardía de servicios | Media | Alto | Integración continua en `develop` |
| Tiempo limitado | Alta | Alto | Priorizar *Must have* |
| Dependencia de servicios externos (Gemini) | Media | Medio | Mocks |

## 6. Métricas y control

Avance por módulo, burndown por sprint y cumplimiento de MoSCoW (herramientas
de seguimiento del equipo). Estimación y presupuesto en KA15.
