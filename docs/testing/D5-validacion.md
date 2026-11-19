# D5: validación con la base de desarrollo

Fecha: 19 de noviembre de 2026.

Se reconstruyó y reinició únicamente `ingesta`: la imagen anterior no incluía
`/api/v1/stats/summary`. Se consultó el endpoint por HTTP desde el contenedor,
con un JWT temporal para una cuenta gerente activa, sin imprimir credenciales.
La verificación SQL se realizó en una transacción de solo lectura.

Rango UTC: `2026-09-28T20:49:16.942528+00:00` a
`2026-11-19T16:21:26.622343+00:00`.
La base contiene 2726 lecturas en ese intervalo y tres cámaras activas.

Comprobaciones aprobadas:

- HTTP 200 y presencia de todas las cámaras activas.
- Media, mediana y desviación poblacional de temperatura contra `AVG`,
  `percentile_cont(0.5)` y `stddev_pop` de PostgreSQL.
- Promedio y suma de consumo contra `AVG` y `SUM` de PostgreSQL.
- Alertas, críticas y recomendaciones pendientes contra conteos SQL independientes.
- Identificadores, valores y orden completo de ambos rankings.
- `top=3` conserva todas las cámaras en el resumen y limita los rankings.
- HTTP 401 sin token; HTTP 422 con fecha inválida, rango invertido y `top=0`.
- Período vacío devuelve las cámaras activas sin lecturas ni alertas.
- Las nueve pruebas de `test_stats.py` aprobaron, incluidas las diez cámaras sintéticas.

Ranking de consumo observado (suma de muestras en kW, no energía en kWh):

| Posición | Cámara | Valor |
| --- | --- | ---: |
| 1 | Túnel de Enfriamiento A | 2040.17 |
| 2 | Cámara Mantenimiento 03 | 1254.73 |
| 3 | Cámara Principal 02 | 1094.96 |

Las tres cámaras tienen cero alertas en el intervalo. El ranking ordena el empate
por UUID ascendente: Mantenimiento 03, Principal 02, Túnel de Enfriamiento A.

Limitación: no se cumple todavía la prueba de aceptación con diez cámaras reales,
pues solo hay tres activas en esta base. Tampoco hay alertas reales con conteos
distintos para comprobar su orden descendente; ese caso sí pasa con datos
sintéticos. No se insertaron datos ni se modificaron registros para simular esa
validación.
