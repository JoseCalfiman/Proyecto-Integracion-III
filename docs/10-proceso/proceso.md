# Proceso de desarrollo de software

> **Estado:** Borrador
> **Área SWEBOK:** KA10 — Software Engineering Process
> **Responsable:** José Calfimán
> **Última actualización:** 2026-10-06
> **Documentos relacionados:** [Plan de proyecto](../09-gestion-proyecto/plan-proyecto.md), [Control de versiones](../08-gestion-configuracion/control-versiones.md)

## 1. Propósito

Describir cómo el equipo organiza el trabajo: modelo de ciclo de vida, procesos,
roles y mejora continua.

## 2. Modelo de ciclo de vida

**Ágil (Scrum)** con sprints, adaptado a un equipo de 6 personas y a la
restricción de tiempo. Se usa un modelo iterativo/incremental por microservicio.

## 3. Procesos

| Proceso | Práctica en el equipo |
|---------|-----------------------|
| Planificación del sprint | Selección de ítems *Must/Should* del backlog MoSCoW |
| Ejecución | Trabajo en ramas `feature/` |
| Revisión | Pull Request hacia `develop` |
| Retrospectiva | Ajustes de proceso por sprint |
| Control de versiones | `main` → `develop` → `feature/*` |

## 4. Roles

Product Owner (cliente/docente), Scrum Master (José), equipo de desarrollo
(5 integrantes).

## 5. Definición de Terminado (DoD)

- Código integrado en `develop` vía PR revisada.
- Documentación del módulo actualizada en `docs/`.
- Pruebas básicas pasando.

## 6. Mejora continua (PDCA)

Identificación de problemas en retrospectiva → acción → verificación en el
siguiente sprint.
