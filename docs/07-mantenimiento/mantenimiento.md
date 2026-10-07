# Plan de mantenimiento

> **Estado:** Pendiente
> **Área SWEBOK:** KA7 — Software Maintenance
> **Responsable:** Equipo completo
> **Última actualización:** 2026-10-06
> **Documentos relacionados:** [Operaciones](../06-operaciones/despliegue.md)

## 1. Propósito

Definir cómo se mantiene el sistema tras la entrega (ISO/IEC/IEEE 14764).

## 2. Tipos de mantenimiento

| Tipo | Ejemplo en el proyecto |
|------|------------------------|
| Correctivo | Corregir el cálculo de pendiente (`worker-predictivo`). |
| Adaptativo | Actualizar versiones de Kafka/Prophet/React. |
| Perfectivo | Mejorar precisión del modelo o gráficos. |
| Preventivo | Refactor de modelos SQLAlchemy, cobertura de tests. |
| De emergencia | Caída de la ingesta o de TimescaleDB. |

## 3. Problemas conocidos a resolver

- `.env` no versionado (documentar en `.env.example`).
- `Dockerfile` del dashboard vacío.
- Inconsistencia Redis vs. Kafka en el README de `worker-haccp`.

## 4. Estrategia

- Ramas `hotfix/` para correctivos; PR hacia `develop`.
- Toda corrección incluye prueba que la cubra.
- Versionado semántico de imágenes y releases.

## 5. Registro de cambios

Ver [`08-gestion-configuracion/control-versiones.md`](../08-gestion-configuracion/control-versiones.md).
