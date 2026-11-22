# Integración de estadísticas predictivas y dashboard (M5)

## Recorrido de datos

Wokwi publica en MQTT, Ingesta valida y publica en Kafka y el Predictor mantiene
una ventana por cámara. Cada evaluación guarda la pendiente, el tiempo restante,
el riesgo y el diagnóstico en la misma fila de la tabla `predictions`.
La API devuelve ese diagnóstico y el dashboard consulta la última predicción
cada 15 segundos. Las métricas corresponden al cálculo guardado, no a una
reconstrucción de la ventana en el navegador.

## Contrato aditivo v1

Se mantienen los endpoints y campos previos.

- `GET /api/v1/predictions/latest?id_chamber=<uuid>`
- `GET /api/v1/predictions/history?id_chamber=<uuid>&limit=20&offset=0`

Ambos agregan `diagnostico`, un objeto opcional. Las predicciones anteriores
devuelven `diagnostico: null`. Se conservan `slope`,
`projected_temperature`, `remaining_time_min`, `risk_level`,
`id_prediction`, `id_chamber` y `calculation_date`.
El esquema completo está tipado en `schemas.PredictionDiagnostics` y aparece en
OpenAPI. El diagnóstico contiene los siguientes campos.

| Campo | Interpretación |
| --- | --- |
| schema_version | Versión del contrato, actualmente 1 |
| recorded_at | Timestamp de la última lectura recibida en la ventana |
| reference_timestamp | Timestamp de la última lectura aceptada para la predicción |
| sample_count / usable_sample_count | Lecturas originales y lecturas utilizables |
| span_minutes | Duración de la ventana original |
| temperature / consumption_kw | Estadísticas originales por variable |
| std_temp / iqr_temp | Desviación e IQR de temperatura, para diagnóstico |
| outlier_count / outliers | Cantidad y detalle de atípicos de temperatura |
| std_ddof | 1, desviación muestral con divisor n − 1 |
| factor_iqr | Multiplicador de los límites de Tukey |
| absolute_max_temp / umbral_alerta_minutos | Límite de temperatura y umbral temporal usados en la evaluación |
| umbral_std_temp | Umbral descriptivo de variabilidad en °C |
| condiciones | VENTANA_INSUFICIENTE, DATOS_VARIABLES y/o CON_ATIPICOS |

Cada bloque de estadísticas tiene `sample_count`, `media`, `mediana`, `std`,
`min`, `max`, `q1`, `q3` e `iqr`. Los timestamps se guardan como ISO 8601.
Cada atípico incluye su `index` original (desde cero), `timestamp`,
`temperature` y, si llegó, `consumption_kw`.

Las estadísticas incluyen los atípicos. La pendiente y el tiempo restante usan
las lecturas aceptadas por IQR. Si la última lectura es atípica, el tiempo restante
corresponde a `reference_timestamp`, no al momento de refrescar la pantalla.
Sin consumo recibido, su bloque tiene conteo cero y estadísticas nulas.
Con menos de dos muestras, la desviación muestral es nula.

## Encaje con D4 y D6

D4 (`/stats/chambers/{id_chamber}`) describe todas las lecturas del intervalo
solicitado y usa desviación poblacional. El diagnóstico predictivo describe la
ventana deslizante usada por el worker y emplea desviación muestral. El dashboard
identifica ambas convenciones y mantiene el resumen histórico existente.

D6 conserva sus endpoints e inventario real. El diagnóstico individual por
cámara del Panel Técnico incorpora el componente compartido
`PredictionDiagnostics`. Ese componente también aparece en el inicio del
técnico y en el dashboard del gerente. Ambos roles ven las métricas, y el técnico
puede desplegar los criterios y lecturas atípicas. Los permisos de los endpoints
de predicciones siguen siendo los de Ingesta para técnico y gerente.

Se muestran estados de carga, errores, predicciones anteriores sin diagnóstico
y lecturas con más de dos minutos de antigüedad. Una ventana insuficiente se
presenta como evaluación pendiente aunque el contrato histórico indique
`SIN_RIESGO`.

## Actualización de una instalación existente

La migración es aditiva e idempotente y mantiene las predicciones anteriores.
Con TimescaleDB en marcha, desde PowerShell en la raíz del repositorio:

```powershell
Get-Content database/migrations/002_prediction_diagnostics.sql | docker compose exec -T timescaledb sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'
docker compose up -d --build worker-predictivo ingesta dashboard
```

El Predictor también verifica la columna al iniciar. Las instalaciones nuevas
la crean desde `database/init.sql`. Para una actualización coordinada, aplicar
la migración antes de reconstruir Ingesta evita consultas durante la transición.

## Verificación con Wokwi

1. Configurar las variables del entorno y arrancar los servicios habituales.
2. Iniciar Wokwi con el UUID de una cámara registrada.
3. Acceder al dashboard como gerente o técnico y seleccionar esa cámara.
4. Comprobar que la fecha de última lectura, el conteo y las estadísticas cambian.
5. Consultar `/predictions/latest` con el mismo UUID y comparar su diagnóstico
   con la pantalla. Se puede usar la pestaña Network del navegador autenticado.
6. Mantener una serie estable y después introducir un pico entre varias lecturas
   estables. Comprobar la lectura registrada y la pendiente con datos aceptados.
7. Detener el envío y comprobar el aviso de antigüedad tras dos minutos.

Las pruebas automatizadas usan eventos y bases aislados. La comprobación con
Wokwi requiere los servicios desplegados y no se sustituye por esas pruebas.
