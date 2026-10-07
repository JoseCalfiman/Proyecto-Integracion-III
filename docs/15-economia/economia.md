# Economía de la ingeniería de software

> **Estado:** Pendiente
> **Área SWEBOK:** KA15 — Software Engineering Economics
> **Responsable:** José Calfimán
> **Última actualización:** 2026-10-06
> **Documentos relacionados:** [Plan de proyecto](../09-gestion-proyecto/plan-proyecto.md)

## 1. Propósito

Documentar el análisis económico del proyecto: esfuerzo, costos, reutilización y
retorno esperado (ROI).

## 2. Esfuerzo estimado

Estimación por persona/módulo en función de los sprints planificados (ver KA9).

## 3. Costos

| Concepto | Tipo | Nota |
|----------|------|------|
| Hardware ESP32 | CAPEX | Dispositivo de borde |
| Host/cloud | OPEX | Depende del despliegue |
| Software | — | Stack open source (Python, Kafka, PostgreSQL, React) |
| Horas de desarrollo | CAPEX | Esfuerzo del equipo |

## 4. Reutilización (open source)

El uso de software libre (TimescaleDB, Kafka, Mosquitto, Prophet, FastAPI, React)
reduce costos de licencias.

## 5. Beneficio esperado

El módulo de optimización estima ahorro energético en CLP
(`saving_recommendation`), lo que sustenta el retorno de la inversión.

## 6. Análisis pendiente

Cálculo formal de ROI, costo total de propiedad (TCO) y punto de equilibrio.
