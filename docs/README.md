# Documentación — Sistema de Monitoreo de Frigorífico Inteligente

Este directorio es la **sección central del repositorio que reúne, organiza y
conserva toda la documentación generada** por el equipo.

La estructura sigue el estándar **IEEE SWEBOK Guide v4.0** (*Guide to the Software
Engineering Body of Knowledge*, IEEE Computer Society, 2024), que define **18 Áreas
de Conocimiento** (*Knowledge Areas*, **KA**). Cada área tiene su propia carpeta
numerada en `docs/`.

> **Alcance de esta entrega.** Por restricciones de tiempo no se exige el contenido
> completo de cada documento. La **estructura sí es definitiva**, y cada documento
> declara explícitamente su estado (`Completo`, `Borrador` o `Pendiente`) y su
> responsable.

---

## Índice general de la documentación

Este índice es el punto único de entrada. Toda la documentación se referencia aquí.

| KA | Área de conocimiento (SWEBOK v4) | Carpeta | Documentos | Estado |
|:--:|----------------------------------|---------|------------|:------:|
| 1 | Software Requirements | [`01-requerimientos/`](01-requerimientos/) | [Requerimientos](01-requerimientos/requerimientos.md), [Casos de uso](01-requerimientos/casos-de-uso.md) | Borrador |
| 2 | Software Architecture | [`02-arquitectura/`](02-arquitectura/) | [Arquitectura](02-arquitectura/arquitectura.md), [Diagrama de software](02-arquitectura/diagrama-software.md) | Borrador |
| 3 | Software Design | [`03-diseno/`](03-diseno/) | [Modelo de datos](03-diseno/modelo-datos.md) | Borrador |
| 4 | Software Construction | [`04-construccion/`](04-construccion/) | [Manual técnico](04-construccion/manual-tecnico.md) | Borrador |
| 5 | Software Testing | [`05-pruebas/`](05-pruebas/) | [Plan de pruebas](05-pruebas/plan-de-pruebas.md) | Pendiente |
| 6 | Software Engineering Operations | [`06-operaciones/`](06-operaciones/) | [Operaciones y despliegue](06-operaciones/despliegue.md) | Pendiente |
| 7 | Software Maintenance | [`07-mantenimiento/`](07-mantenimiento/) | [Plan de mantenimiento](07-mantenimiento/mantenimiento.md) | Pendiente |
| 8 | Software Configuration Management | [`08-gestion-configuracion/`](08-gestion-configuracion/) | [Control de versiones](08-gestion-configuracion/control-versiones.md) | Pendiente |
| 9 | Software Engineering Management | [`09-gestion-proyecto/`](09-gestion-proyecto/) | [Plan de proyecto](09-gestion-proyecto/plan-proyecto.md) | Pendiente |
| 10 | Software Engineering Process | [`10-proceso/`](10-proceso/) | [Proceso de desarrollo](10-proceso/proceso.md) | Pendiente |
| 11 | Software Engineering Models and Methods | [`11-modelos-metodos/`](11-modelos-metodos/) | [Modelos y métodos](11-modelos-metodos/modelos-metodos.md) | Pendiente |
| 12 | Software Quality | [`12-calidad/`](12-calidad/) | [Plan de calidad](12-calidad/calidad.md) | Pendiente |
| 13 | Software Security | [`13-seguridad/`](13-seguridad/) | [Seguridad](13-seguridad/seguridad.md) | Pendiente |
| 14 | Software Engineering Professional Practice | [`14-practica-profesional/`](14-practica-profesional/) | [Práctica profesional](14-practica-profesional/practica-profesional.md) | Pendiente |
| 15 | Software Engineering Economics | [`15-economia/`](15-economia/) | [Economía del proyecto](15-economia/economia.md) | Pendiente |
| 16 | Computing Foundations | [`16-fundamentos-computacion/`](16-fundamentos-computacion/) | [Fundamentos de computación](16-fundamentos-computacion/fundamentos-computacion.md) | Pendiente |
| 17 | Mathematical Foundations | [`17-fundamentos-matematicos/`](17-fundamentos-matematicos/) | [Fundamentos matemáticos](17-fundamentos-matematicos/fundamentos-matematicos.md) | Pendiente |
| 18 | Engineering Foundations | [`18-fundamentos-ingenieria/`](18-fundamentos-ingenieria/) | [Fundamentos de ingeniería](18-fundamentos-ingenieria/fundamentos-ingenieria.md) | Pendiente |

---

## Descripción del proyecto (contexto documental)

Plataforma distribuida de monitoreo para un frigorífico que integra:

- **Sensores / ESP32 (Wokwi)** que publican telemetría por **MQTT**.
- **Ingesta** (FastAPI + Paho MQTT) que valida payloads y persiste en **TimescaleDB**.
- **Apache Kafka** como bus de eventos asíncrono (`sensor.raw`, `sensor.anomaly`,
  `haccp.alerts`, `optimization.reports`).
- **Workers**: predictivo (regresión lineal), HACCP (reglas sanitarias) y
  optimización (Prophet + APScheduler).
- **Dashboard** (React + Vite + Tailwind) para gerentes y técnicos, con asistente
  **Gemini**.

---

## Convenciones de documentación

1. **Idioma:** español.
2. **Ubicación:** cada documento vive en la carpeta del KA de SWEBOK que le
   corresponde. Si un documento cubre más de un KA, se ubica en el KA principal y
   se referencia desde el otro.
3. **Encabezado obligatorio:** todo documento incluye un bloque de metadatos con
   *Estado*, *Responsable* y *Última actualización*.
4. **Registro:** al crear un documento nuevo, se agrega una fila a la tabla del
   índice general de este archivo y se enlaza desde la carpeta del KA.
5. **Plantilla:** usar [`plantillas/documento.md`](plantillas/documento.md) como base.
6. **Diagramas:** las imágenes y diagramas exportados se guardan en
   [`assets/`](assets/).
7. **Conservación:** los documentos no se eliminan; cuando dejan de ser vigentes
   pasan a estado *Obsoleto* con una nota de reemplazo.

## Referencia del estándar

- SWEBOK Guide v4.0, IEEE Computer Society, 2024 — <https://www.computer.org/education/bodies-of-knowledge/software-engineering>
