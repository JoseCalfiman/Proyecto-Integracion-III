# Métricas de alertas HACCP (E5)

Este documento define las métricas de alertas que complementan el resumen de
D5. La rama `feature/ingesta` implementa `GET /api/v1/stats/summary` y entrega,
por cámara, `alerts` y `critical_alerts`; ambos cuentan filas de
`generated_alerts` cuya fecha de generación cae en el período, sin filtrar por
estado. E5 deja las fórmulas y una consulta de referencia para extender ese
resumen sin modificar archivos de Ingesta ni Dashboard.

## Definiciones

Todas las métricas se agrupan por `id_chamber` y usan `generation_date` para
determinar si una alerta pertenece al período solicitado por D5. Se incluyen
las cámaras activas, incluso si no tienen alertas en el período. Una alerta
publicada de nuevo en Kafka con el mismo `id_alert` cuenta una sola vez: la
fuente de conteo es la fila persistida, no las entregas del tópico.

| Métrica | Fórmula |
| --- | --- |
| `alerts` | Cantidad de alertas generadas en el período, sin importar estado. |
| `critical_alerts` | Cantidad con `severity = 'critical'`, en cualquier estado. Puede superponerse con los conteos por estado. |
| `active_alerts` | Cantidad con `status = 'active'`. |
| `acknowledged_alerts` | Cantidad con `status = 'acknowledged'`. |
| `resolved_alerts` | Cantidad con `status = 'resolved'`. |
| `mean_resolution_minutes` | Promedio de `resolution_date - generation_date`, en minutos, para alertas del período resueltas y con ambas fechas válidas. Es `null` si no hay muestras válidas. |
| `resolution_samples` | Número de alertas incluidas en el promedio de resolución. |

El promedio usa solamente alertas en estado resuelto con `resolution_date >=
generation_date`; una duración negativa o incompleta no aporta una muestra. El
conteo de resueltas sí las incluye si su estado es `resolved`. Se informa el
tamaño de muestra junto al promedio para que el dashboard pueda contextualizar
el indicador; no se inventa un promedio igual a cero cuando no hay resoluciones.

El estado representa el estado actual de la alerta. Por eso, al consultar un
período anterior, una alerta generada entonces puede contarse hoy como resuelta.
La severidad y el estado son dimensiones distintas: una alerta crítica también
puede estar activa, reconocida o resuelta.

## Consulta de referencia para D5

La consulta conserva cámaras activas sin alertas mediante `LEFT JOIN`. Los
parámetros temporales deben normalizarse igual que en D5: `desde` es inclusivo;
un `hasta` de fecha incluye el día completo (`hasta_exclusivo` es la medianoche
del día siguiente en UTC), mientras que un `hasta` con hora es inclusivo.

```sql
SELECT
    c.id_chamber,
    c.name,
    COUNT(a.id_alert) AS alerts,
    COUNT(a.id_alert) FILTER (
        WHERE a.severity = 'critical'
    ) AS critical_alerts,
    COUNT(a.id_alert) FILTER (
        WHERE a.status = 'active'
    ) AS active_alerts,
    COUNT(a.id_alert) FILTER (
        WHERE a.status = 'acknowledged'
    ) AS acknowledged_alerts,
    COUNT(a.id_alert) FILTER (
        WHERE a.status = 'resolved'
    ) AS resolved_alerts,
    AVG(
        EXTRACT(EPOCH FROM (a.resolution_date - a.generation_date)) / 60.0
    ) FILTER (
        WHERE a.status = 'resolved'
          AND a.generation_date IS NOT NULL
          AND a.resolution_date IS NOT NULL
          AND a.resolution_date >= a.generation_date
    ) AS mean_resolution_minutes,
    COUNT(a.id_alert) FILTER (
        WHERE a.status = 'resolved'
          AND a.generation_date IS NOT NULL
          AND a.resolution_date IS NOT NULL
          AND a.resolution_date >= a.generation_date
    ) AS resolution_samples
FROM chambers AS c
LEFT JOIN generated_alerts AS a
    ON a.id_chamber = c.id_chamber
   AND a.generation_date >= :desde_utc
   AND (
       (:hasta_es_fecha AND a.generation_date < :hasta_exclusivo_utc)
       OR
       (NOT :hasta_es_fecha AND a.generation_date <= :hasta_inclusivo_utc)
   )
WHERE c.active IS TRUE
GROUP BY c.id_chamber, c.name
ORDER BY c.name, c.id_chamber;
```

Los filtros de fecha van en el `JOIN`, no en un `WHERE` sobre `generated_alerts`,
para que las cámaras sin alertas sigan apareciendo con conteos en cero y promedio
`null`. `AVG` ya ignora valores nulos; el filtro explícito también excluye
duraciones incompletas o negativas.

## Validación con un conjunto conocido

Se toma un período que contiene las cinco alertas siguientes:

| Cámara | Severidad | Estado | Duración hasta resolución |
| --- | --- | --- | ---: |
| A | critical | active | — |
| A | high | acknowledged | — |
| A | medium | resolved | 30 min |
| A | critical | resolved | 90 min |
| B | medium | resolved | 15 min |
| C | — | sin alertas | — |

El resultado esperado de la consulta es:

| Cámara | `alerts` | `critical_alerts` | `active_alerts` | `acknowledged_alerts` | `resolved_alerts` | `mean_resolution_minutes` | `resolution_samples` |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| A | 4 | 2 | 1 | 1 | 2 | 60 | 2 |
| B | 1 | 0 | 0 | 0 | 1 | 15 | 1 |
| C | 0 | 0 | 0 | 0 | 0 | `null` | 0 |

Comprobación manual: para A, `(30 + 90) / 2 = 60` minutos; la cámara C no
produce un promedio porque su conjunto de duraciones está vacío. Los conteos de
estado suman el total por cámara (`active + acknowledged + resolved = alerts`)
cuando todos los estados son válidos. `critical_alerts` no se suma a los estados
porque es una clasificación independiente.

Este CTE reproduce el conjunto sin insertar ni modificar filas. Se puede pegar
directamente en `psql` para demostrar los resultados:

```sql
WITH chambers(id_chamber, name, active) AS (
    VALUES
        ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid, 'A', true),
        ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'::uuid, 'B', true),
        ('cccccccc-cccc-cccc-cccc-cccccccccccc'::uuid, 'C', true)
), alerts(id_alert, id_chamber, severity, status, generation_date, resolution_date) AS (
    VALUES
        (1, 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid, 'critical', 'active',        '2026-01-01 00:00+00'::timestamptz, NULL::timestamptz),
        (2, 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid, 'high',     'acknowledged', '2026-01-01 00:00+00'::timestamptz, NULL::timestamptz),
        (3, 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid, 'medium',   'resolved',     '2026-01-01 00:00+00'::timestamptz, '2026-01-01 00:30+00'::timestamptz),
        (4, 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'::uuid, 'critical', 'resolved',     '2026-01-01 00:00+00'::timestamptz, '2026-01-01 01:30+00'::timestamptz),
        (5, 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'::uuid, 'medium',   'resolved',     '2026-01-01 00:00+00'::timestamptz, '2026-01-01 00:15+00'::timestamptz)
)
SELECT c.name,
       COUNT(a.id_alert) AS alerts,
       COUNT(a.id_alert) FILTER (WHERE a.severity = 'critical') AS critical_alerts,
       COUNT(a.id_alert) FILTER (WHERE a.status = 'active') AS active_alerts,
       COUNT(a.id_alert) FILTER (WHERE a.status = 'acknowledged') AS acknowledged_alerts,
       COUNT(a.id_alert) FILTER (WHERE a.status = 'resolved') AS resolved_alerts,
       ROUND((AVG(EXTRACT(EPOCH FROM (a.resolution_date - a.generation_date)) / 60.0)
           FILTER (WHERE a.status = 'resolved' AND a.generation_date IS NOT NULL
             AND a.resolution_date IS NOT NULL AND a.resolution_date >= a.generation_date))::numeric, 3)
           AS mean_resolution_minutes,
       COUNT(a.id_alert) FILTER (WHERE a.status = 'resolved' AND a.generation_date IS NOT NULL
         AND a.resolution_date IS NOT NULL AND a.resolution_date >= a.generation_date) AS resolution_samples
FROM chambers c
LEFT JOIN alerts a ON a.id_chamber = c.id_chamber
 AND a.generation_date >= '2026-01-01 00:00+00'::timestamptz
 AND a.generation_date < '2026-02-01 00:00+00'::timestamptz
WHERE c.active IS TRUE
GROUP BY c.id_chamber, c.name
ORDER BY c.name, c.id_chamber;
```

La salida debe coincidir con la tabla esperada anterior. Para validar alertas
reales, se ejecuta la consulta de referencia sobre `chambers` y
`generated_alerts` con el período elegido.

## Compatibilidad y alcance

La respuesta D5 existente conserva sus campos `alerts` y `critical_alerts` con
las definiciones anteriores. Los campos `active_alerts`,
`acknowledged_alerts`, `resolved_alerts`, `mean_resolution_minutes` y
`resolution_samples` son la extensión propuesta por E5; exponerlos en el
endpoint compartido requiere integrarlos en la rama de Ingesta de Diego. Este
cambio solo aporta el contrato y la consulta de referencia para que esa
integración no altere las rutas de D5.
