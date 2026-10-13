# Modelos y métodos de ingeniería de software

> **Estado:** Borrador
> **Área SWEBOK:** KA11 — Software Engineering Models and Methods
> **Responsable:** Equipo completo
> **Última actualización:** 2026-10-06
> **Documentos relacionados:** [Arquitectura](../02-arquitectura/arquitectura.md)

## 1. Propósito

Registrar los modelos, métodos y técnicas de análisis/diseño aplicados al proyecto.

## 2. Métodos aplicados

| Método | Aplicación |
|--------|-----------|
| Modelado de arquitectura | Vistas y diagramas (KA2) |
| Modelado de datos | Diagrama E-R (KA3) |
| Modelado de casos de uso | KA1 |
| Modelado de dominio | Entidades del frigorífico (empresa, cámara, sensor) |
| Métodos ágiles | Scrum (KA10) |
| Priorización | MoSCoW |
| Notación | UML-like (Mermaid), JSON Schema/Pydantic |

## 3. Modelos analíticos

- **Regresión lineal** para la tendencia de temperatura (worker predictivo).
- **Series de tiempo / Prophet** para el consumo eléctrico (worker optimización).
- **Reglas de producción** para HACCP (condición → alerta).

## 4. Métodos formales / semi-formales

Validación de contratos con Pydantic y esquemas de BD con restricciones `CHECK`.
Los detalles formales por módulo quedan pendientes de documentar.
