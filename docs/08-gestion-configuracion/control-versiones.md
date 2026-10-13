# Control de versiones y gestión de configuración

> **Estado:** Borrador (flujo definido en el README raíz; completar formato de baseline)
> **Área SWEBOK:** KA8 — Software Configuration Management
> **Responsable:** Ricardo Aravena
> **Última actualización:** 2026-10-06
> **Documentos relacionados:** [Proceso](../10-proceso/proceso.md)

## 1. Propósito

Identificar, controlar y auditar los artefactos del software (ítems de
configuración) y gestionar los cambios.

## 2. Ítems de configuración (CI)

Código fuente de cada microservicio, `docker-compose.yml`, `database/init.sql` y
`seeds.sql`, `mosquitto/`, `kafka/topics-setup.sh`, `wokwi/`, `docs/`.

## 3. Estrategia de ramas

```
main (estable) → develop (integración) → feature/<microservicio> (trabajo individual)
```

Cada persona trabaja en su rama `feature/` y hace Pull Request hacia `develop`
cuando su parte funciona.

## 4. Convención de commits

Prefijos sugeridos: `feat:`, `fix:`, `docs:`.

## 5. Control de cambios y auditoría

- Todo cambio entra por Pull Request revisada.
- Baselines: `main` en cada entrega; etiquetas `v0.1`, `v0.2`… (pendiente).
- Registro de estado (status accounting) pendiente de formalizar.

## 6. Archivos ignorados (`.gitignore`)

Secretos (`.env`), artefactos de build, cachés (`__pycache__`, `.pytest_cache`).
