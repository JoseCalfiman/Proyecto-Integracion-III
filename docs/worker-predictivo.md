# Worker Predictivo

**Responsable:** Matías Cárcamo
**Ubicación en el repo:** `microservices/worker-predictivo/`

## 1. Propósito

El Worker Predictivo escucha las lecturas de temperatura que llegan por
el tópico de Kafka `sensor.raw`, estima si la temperatura de una cámara
va en aumento y calcula cuántos minutos quedan antes de que se pase del
límite HACCP configurado para esa cámara. Si el riesgo es inminente,
publica una alerta en el tópico `sensor.anomaly`. Además, cada predicción
que calcula (tenga riesgo o no) queda guardada en la tabla
`generated_predictions`, para tener un historial.

## 2. Cómo se calcula la tendencia de temperatura (regresión lineal)

Por cada cámara se guarda un historial corto con las últimas lecturas de
temperatura de los últimos `VENTANA_MINUTOS` minutos (5 minutos por
defecto, ver `config.py`). Cada vez que llega una lectura nueva:

1. Se agrega al historial de esa cámara.
2. Se eliminan del historial las lecturas más antiguas que
   `VENTANA_MINUTOS`.
3. Con los puntos que quedan (tiempo y temperatura), se calcula una
    **regresión lineal** usando operaciones vectorizadas de `NumPy`. En simple: se busca la
   línea recta que mejor representa cómo ha ido cambiando la
   temperatura en ese tramo de tiempo.

El resultado de esa regresión es la **pendiente**, es decir, cuántos
grados sube (o baja) la temperatura por minuto. Es el mismo concepto que
la pendiente de una recta en matemáticas: "cuánto cambia y por cada
cambio en x".

- Si hay menos de 2 lecturas en el historial, no alcanza para calcular
  una pendiente, así que se retorna `None`.
- Pendiente **positiva** = la cámara se está calentando.
- Pendiente **negativa o cero** = la temperatura está estable o
  bajando, no hay riesgo.

Implementación: `predictor.calcular_pendiente()`.

### Tratamiento de atípicos y diagnóstico de ventana (M3 y M4)

`evaluar_riesgo()` identifica temperaturas fuera de
`[Q1 - 1,5 × IQR, Q3 + 1,5 × IQR]`, con cuartiles interpolados linealmente.
La regresión usa las lecturas aceptadas y sus timestamps originales, conservando
las distancias temporales. La ventana original permanece disponible y las
lecturas excluidas quedan en el log y en `diagnostico.outliers`, con índice,
timestamp y temperatura.

El tiempo restante se calcula desde la última lectura aceptada. Si el último
dato es un spike, el tiempo estimado corresponde al instante de la última lectura
aceptada. Un valor fuera de IQR es una marca estadística que requiere revisión.
El control de límites absolutos de HACCP sigue siendo responsabilidad del worker HACCP.

Por ejemplo, con muestras separadas por un minuto,
`[-18, -18.1, -17.9, -18, 20]` pasa de una pendiente sin filtrar de
`7,61 °C/min` a `0,02 °C/min`. La lectura de `20 °C` queda registrada.
La tendencia `[-18, -17, -16]` conserva su pendiente de `1 °C/min`.
`calcular_pendiente()` permite calcular la regresión directa para comparar.

Cada evaluación devuelve `diagnostico` y el consumidor lo registra junto con
el identificador de cámara. Sus métricas describen la ventana original:

- `sample_count`: número de lecturas.
- `span_minutes`: diferencia entre el mayor y el menor timestamp en minutos.
  En una ventana vacía es `None`.
- `std_temp`: desviación estándar muestral. Es `None` con menos de dos
  muestras o temperaturas no finitas.
- `iqr_temp`: Q3 menos Q1. Es `None` en una ventana vacía o con temperaturas
  no finitas.
- `outlier_count` y `outliers`: cantidad y detalle de lecturas marcadas por IQR.
- `usable_sample_count`: cantidad de lecturas aceptadas para la regresión.
- `umbral_std_temp`: umbral usado para indicar variabilidad, en °C.
- `condiciones`: lista de condiciones que pueden coexistir.

Las condiciones son `VENTANA_INSUFICIENTE` cuando hay menos de dos lecturas
aceptadas, no hay separación temporal o existen datos no finitos;
`DATOS_VARIABLES` cuando la desviación alcanza el umbral; y `CON_ATIPICOS`
cuando IQR marca alguna lectura. Una lista vacía indica que ninguna de estas
condiciones se cumple. Una ventana insuficiente devuelve pendiente y tiempo
restante `None` y `hay_riesgo=False`; el diagnóstico permite distinguirla de
una ventana evaluable sin riesgo.

Se adopta inicialmente `umbral_std_temp=0.5` °C, configurable en
`evaluar_riesgo()`. Es un criterio descriptivo operativo pendiente de validación
por el equipo. Las métricas se calculan sobre la ventana completa, por lo que
un spike puede activar tanto variabilidad como presencia de atípicos.

## 3. Fórmula del tiempo restante

Con la pendiente ya calculada, se estima cuántos minutos faltan para que
la cámara llegue a `max_absolute_temp` (el límite HACCP de esa cámara,
que se obtiene desde la tabla `haccp_rules`):

```
tiempo_restante = (max_absolute_temp - temp_actual) / pendiente
```

Donde:

- `temp_actual` es la última temperatura registrada.
- `max_absolute_temp` se obtiene de la regla HACCP activa más reciente
  de la cámara (`haccp_rules.active = TRUE`, la de `review_date` más
  nueva). Si la cámara no tiene ninguna regla activa, se usa como
  respaldo el valor por defecto `LIMITE_HACCP_DEFAULT` de `config.py`.
- `pendiente` es el valor calculado en el paso anterior (grados por
  minuto).

Casos especiales:

- **Si `pendiente <= 0`**, no hay riesgo, y la función retorna `None`
  directamente (no tiene sentido calcular un "tiempo restante" si la
  temperatura no está subiendo).
- **Si `temp_actual >= max_absolute_temp`**, la cámara ya se pasó del
  límite, así que el tiempo restante se marca como `0` minutos.

Implementación: `predictor.estimar_tiempo_restante()`.

## 4. Criterios de alerta (niveles de riesgo)

El tiempo restante, solo como número, no dice mucho a simple vista. Por
eso el worker lo traduce a un **nivel de riesgo**, más fácil de leer para
el resto del sistema (dashboard, notificaciones, etc.):

| Nivel de riesgo | Se asigna cuando... |
|---|---|
| `SIN_RIESGO` | No hay pendiente positiva (temperatura estable o bajando) |
| `CRITICO` | El tiempo restante es 25% o menos del umbral de alerta |
| `ALTO` | El tiempo restante es 60% o menos del umbral de alerta |
| `MEDIO` | El tiempo restante es 100% o menos del umbral de alerta |
| `BAJO` | El tiempo restante supera el umbral de alerta (la cámara se está calentando, pero todavía hay margen) |

El **umbral de alerta** que se usa para estos cortes no es siempre el
mismo número: se toma primero desde `tolerance_time_min` de la regla
HACCP activa de la cámara, si es que la regla trae ese dato configurado.
Solo si la cámara no tiene ese valor, se usa el umbral por defecto
`UMBRAL_ALERTA_MINUTOS` de `config.py` (40 minutos).

Aparte del nivel de riesgo, el worker también deja un valor booleano
`hay_riesgo`, que es `True` cuando el tiempo restante es menor o igual al
umbral de alerta. Ese valor es el que decide si se publica una alerta en
`sensor.anomaly`.

**Nota:** `risk_level` (el nivel de riesgo calculado en cada lectura,
según qué tan cerca está el tiempo restante del umbral) no es lo mismo
que `haccp_rules.severity`. `severity` es un valor que alguien configuró
de antemano para decir qué tan grave sería incumplir esa regla en
particular. `risk_level`, en cambio, refleja qué tan urgente es la
situación en este momento, según cómo se está comportando la
temperatura ahora mismo.

Implementación: `predictor.determinar_nivel_riesgo()` y
`predictor.evaluar_riesgo()` (esta última junta pendiente, tiempo
restante y nivel de riesgo en un solo resultado).

## 5. Flujo completo, paso a paso

1. Llega un mensaje al tópico `sensor.raw` con la temperatura de una
   cámara.
2. `kafka_consumer.py` actualiza el historial deslizante de esa cámara
   (los últimos `VENTANA_MINUTOS` minutos).
3. Se busca la regla HACCP activa de la cámara (`repository.obtener_regla_haccp_activa`).
4. `predictor.evaluar_riesgo()` hace todo el cálculo:
   - calcula la pendiente (regresión lineal),
   - estima el tiempo restante con la fórmula de la sección 3,
   - determina el nivel de riesgo de la sección 4.
5. Esa predicción se guarda en la tabla `generated_predictions`
   (`repository.guardar_prediccion`), haya o no haya riesgo.
6. Si `hay_riesgo` es `True`, se publica una alerta en el tópico
   `sensor.anomaly`.

## 6. Qué se guarda en generated_predictions

Cada predicción calculada (con o sin riesgo) se guarda en la tabla
`generated_predictions`, con estos campos:

| Campo | Qué significa |
|---|---|
| `prediction_id` | Identificador único, autoincremental |
| `chamber_id` | UUID de la cámara (referencia a `chambers.id_chamber`) |
| `calculated_slope` | Pendiente calculada (grados por minuto) |
| `projected_temperature` | El `max_absolute_temp` de la regla HACCP usada; queda vacío si no hay riesgo |
| `remaining_time_min` | Tiempo restante estimado; queda vacío si no hay riesgo |
| `risk_level` | `SIN_RIESGO`, `BAJO`, `MEDIO`, `ALTO` o `CRITICO` |
| `calculated_at` | Fecha y hora del cálculo (la genera la base de datos) |

Esto permite revisar más adelante el historial de predicciones por
cámara, aunque en ese momento no se haya disparado ninguna alerta.
