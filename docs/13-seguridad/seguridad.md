# Seguridad del software

> **Estado:** Borrador
> **Área SWEBOK:** KA13 — Software Security
> **Responsable:** Diego Curiqueo / José Calfimán
> **Última actualización:** 2026-10-06
> **Documentos relacionados:** [Arquitectura](../02-arquitectura/arquitectura.md), [Operaciones](../06-operaciones/despliegue.md)

## 1. Propósito

Incorporar la seguridad a lo largo del ciclo de vida: autenticación, gestión de
secretos, codificación segura y pruebas de seguridad.

## 2. Autenticación y autorización

- **JWT** con tabla `revoked_tokens` para revocación.
- Contraseñas almacenadas como hash (`password_hash`).
- Roles (`roles`, `users`) para autorización por perfil (gerente/técnico/admin).

## 3. Gestión de secretos

- Credenciales de MQTT en `mosquitto/pwfile` y `acl.conf`.
- Variables sensibles en `.env` (no versionado); documentadas en `.env.example`.
- Conexión a BD mediante variables de entorno.

## 4. Codificación segura

- Validación estricta de entrada con **Pydantic**.
- Consultas parametrizadas vía **SQLAlchemy** (prevención de inyección SQL).
- Principio de mínimo privilegio en credenciales de servicios.

## 5. Consideraciones de red

- Segmentación por red Docker `frigorifico-net`.
- En producción el dashboard se sirve tras **Nginx**.

## 6. Actividades pendientes

- Modelado de amenazas (STRIDE).
- Análisis de dependencias (SCA) y de vulnerabilidades (CVE/CWE/CVSS).
- Pruebas de seguridad y DevSecOps (KA6).
