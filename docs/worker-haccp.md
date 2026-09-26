# Reglas de validación HACCP

Este documento describe los criterios implementados por el módulo `haccp_validator.py` del worker HACCP. Los valores son parámetros técnicos del proyecto; deben contrastarse con los requisitos sanitarios aplicables al producto y a la cámara antes de usarse como límites operativos definitivos.

## Umbrales predeterminados del validador

| Parámetro | Valor predeterminado | Significado |
| --- | ---: | --- |
| `max_temp_c` | 4 °C | Límite superior. Una lectura solo lo supera si es estrictamente mayor que 4 °C. |
| `min_temp_c` | -30 °C | Límite inferior. Una lectura solo queda por debajo si es estrictamente menor que -30 °C. |
| `warning_duration_seconds` | 900 s (15 min) | Duración mínima fuera del rango para declarar una alerta/violación. |
| `critical_duration_seconds` | 1800 s (30 min) | Duración desde la que la severidad se clasifica como crítica. |
| `critical_temp_c` | 6 °C | Temperatura desde la que una alerta puntual se clasifica como crítica. |
| `sample_interval_seconds` | 10 s | Intervalo predeterminado entre muestras al evaluar series. |

Los parámetros se encuentran en `DEFAULT_HACCP_RULE`. Los evaluadores permiten sobrescribirlos con un diccionario `rule`; `validar_haccp` también adapta una regla ORM o un diccionario de la base de datos.

## Evaluación de una lectura y su duración

`evaluate_temperature_rule(temperature_c, duration_seconds, rule)` considera fuera de rango una lectura mayor que el máximo o menor que el mínimo y aplica estas condiciones:

1. Si la temperatura está dentro del rango inclusivo [-30 °C, 4 °C], el resultado es `normal` y no hay alerta.
2. Si está fuera del rango pero la duración es inferior a 900 segundos, la severidad informativa es `warning`, aunque `is_alert` permanece en `false`.
3. Si permanece fuera del rango durante al menos 900 segundos, `is_alert` pasa a `true`.
4. Una alerta puntual se clasifica como `critical` si la temperatura alcanza 6 °C o si la duración alcanza 1800 segundos; de lo contrario es `warning`.

Con estos defaults, puede emitirse una alerta `warning` entre los 15 y 30 minutos si la temperatura es inferior a 6 °C. Una temperatura de 6 °C o más genera una alerta crítica al alcanzar los 15 minutos.

| Temperatura | Duración | Resultado predeterminado |
| ---: | ---: | --- |
| 4.0 °C o -30.0 °C | Cualquier duración | `normal`; ambos límites se incluyen en el rango |
| 4.1 °C | 899 s | Sin alerta; severidad `warning` |
| 4.1 °C | 900 s | Alerta `warning` |
| 6.0 °C | 900 s | Alerta `critical` por temperatura |
| -30.1 °C | 900 s | Alerta `warning` por estar debajo del mínimo |
| 4.1 °C | 1800 s | Alerta `critical` por duración |

## Evaluación de una serie de lecturas

`evaluate_temperature_series(temperatures, sample_interval_seconds, rule)` recorre las lecturas en orden y considera fuera de rango cada valor mayor que `max_temp_c` o menor que `min_temp_c`. Un valor dentro del rango cierra la secuencia fuera de rango actual. Para cada secuencia de `n` lecturas consecutivas fuera de rango, la duración calculada por la implementación es `(n + 1) × intervalo_de_muestreo`.

La duración de las secuencias detectadas se suma, incluso si se separan por lecturas dentro del rango. Si el total es menor que 900 s, `has_violation` es `false` y la severidad es `normal`; al alcanzar 900 s, `has_violation` es `true`. La severidad se marca crítica desde 1800 s de total. Este evaluador no usa `critical_temp_c`: la clasificación de la serie depende del tiempo total, no de la temperatura máxima.

El intervalo efectivo es el argumento `sample_interval_seconds` (10 s por defecto en la firma). Debe pasarse explícitamente cuando la cadencia de los datos sea distinta; si se pasa un valor falsy, el módulo recurre al intervalo configurado en la regla.

## Valores de la regla persistida en base de datos

El worker define una regla predeterminada para `haccp_rules` en `crud.py`. `validar_haccp` traduce sus campos `max_absolute_temp` y `min_absolute_temp` a los límites del validador, y convierte `tolerance_time_min` a segundos para `warning_duration_seconds`:

| Campo de base de datos | Valor predeterminado | Uso previsto |
| --- | ---: | --- |
| `max_absolute_temp` | 4.00 °C | Temperatura máxima absoluta de la cámara |
| `min_absolute_temp` | -30.00 °C | Temperatura mínima absoluta de la cámara |
| `tolerance_time_min` | 15 min | Tiempo de tolerancia de la regla |
| `active` | `true` | Indica que la regla está activa |

Los 15 minutos de tolerancia de la regla persistida son la fuente de la duración mínima de alerta. Los umbrales de severidad crítica (6 °C y 30 minutos) no están almacenados en `haccp_rules` y permanecen como parámetros predeterminados del validador.

## Estado de integración

El consumidor obtiene la regla activa y llama a `validar_haccp(payload, rule)`. El evento debe incluir `temperature_c` y `duration_seconds`; si falta cualquiera, se ignora y no se genera alerta. Con una violación válida, el consumidor persiste y publica la severidad y el mensaje calculados por el validador, no la severidad original del evento predictivo. El productor de `sensor.anomaly` no está incluido en este repositorio, por lo que debe enviar ambos campos para cumplir este contrato.

## Referencias del código

- `microservices/worker-haccp/haccp_validator.py`: umbrales predeterminados y algoritmos de evaluación.
- `microservices/worker-haccp/tests/test_haccp.py`: casos probados para el límite, la duración, la sobrescritura de reglas y series temporales.
- `microservices/worker-haccp/crud.py`: valores predeterminados de las reglas persistidas.
- `microservices/worker-haccp/models.py`: estructura de `HaccpRule`.
- `microservices/worker-haccp/kafka_consumer.py`: integración del worker con Kafka y la regla activa.