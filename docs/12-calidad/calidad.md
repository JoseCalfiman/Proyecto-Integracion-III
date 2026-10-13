# Plan de calidad de software

> **Estado:** Pendiente
> **Área SWEBOK:** KA12 — Software Quality
> **Responsable:** Equipo completo
> **Última actualización:** 2026-10-06
> **Documentos relacionados:** [Pruebas](../05-pruebas/plan-de-pruebas.md), [Arquitectura](../02-arquitectura/arquitectura.md)

## 1. Propósito

Definir los atributos de calidad, las actividades de aseguramiento (SQA) y las
métricas del proyecto.

## 2. Atributos de calidad (ISO/IEC 25010)

| Atributo | Objetivo |
|----------|----------|
| Adecuación funcional | Cubrir los RF del pipeline de ingesta y alertas |
| Desempeño | Ingesta extremo a extremo < 5 s |
| Fiabilidad | Continuar operando si la DB no está disponible (workers) |
| Usabilidad | Dashboard claro para gerente y técnico |
| Seguridad | JWT, credenciales MQTT, secretos fuera del repo |
| Mantenibilidad | Un microservicio por responsable, con README y tests |

## 3. Actividades SQA

Revisión de Pull Requests, pruebas automatizadas (`pytest`), linting
(Oxlint/ESLint) y revisión de documentación.

## 4. Métricas

Cobertura de pruebas, número de defectos por sprint, adherencia a MoSCoW y tiempos
de ingesta.

## 5. Verificación y validación (V&V)

Verificación por pruebas unitarias/integración; validación contra casos de uso.
Detalle en el plan de pruebas (KA5).
