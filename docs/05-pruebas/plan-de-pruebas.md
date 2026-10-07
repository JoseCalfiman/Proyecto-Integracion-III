# Plan de pruebas

> **Estado:** Pendiente
> **Área SWEBOK:** KA5 — Software Testing
> **Responsable:** Diego Curiqueo
> **Última actualización:** 2026-10-06
> **Documentos relacionados:** [Requerimientos](../01-requerimientos/requerimientos.md)

## 1. Propósito

Definir la estrategia, los niveles, las técnicas y los criterios de las pruebas del
sistema.

## 2. Niveles de prueba

| Nivel | Alcance | Herramienta |
|-------|---------|-------------|
| Unitarias | Modelos, validadores, predictor | `pytest`, `unittest` |
| Integración | MQTT→ingesta, Kafka→workers, API | `pytest`, TestClient, broker mock |
| Sistema | Flujo extremo a extremo | Docker Compose |
| Aceptación | Casos de uso (ver KA1) | Manual |

## 3. Técnicas

Caja negra (partición de equivalencia, valores límite) y caja blanca (cobertura de
ramas) sobre las funciones críticas: `validar_payload`, `calcular_pendiente`,
`calcular_tiempo_restante`, `validar_haccp`.

## 4. Casos de prueba (muestra)

| ID | Objetivo | Entrada | Resultado esperado |
|----|----------|---------|--------------------|
| CP-01 | Validación Pydantic | temperatura fuera de rango (-60) | Rechazo / error |
| CP-02 | Regresión lineal | serie con tendencia de subida | pendiente > 0 |
| CP-03 | Tiempo restante | pendiente ≤ 0 | sin riesgo |
| CP-04 | Regla HACCP | temp > máx y tiempo > tolerancia | alerta HACCP |

## 5. Ubicación de pruebas

`microservices/*/tests/` y `tests/` en la raíz. Ejecutar con `python -m pytest`.

## 6. Criterios de salida (pendiente)

Cobertura mínima acordada, cero fallos en CI, todos los CP críticos en verde.
