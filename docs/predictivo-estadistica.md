# Interpretación estadística del Predictivo

> **Estado:** Borrador, pendiente de revisión cruzada y demo con datos reales  
> **Área SWEBOK:** KA17 — Mathematical Foundations  
> **Responsable:** Matías Cárcamo  
> **Última actualización:** 2026-11-26  
> **Documentos relacionados:** [Integración y dashboard](predictivo-integracion.md),
> [Worker Predictivo](worker-predictivo.md), [Pruebas estadísticas](../microservices/worker-predictivo/tests/README.md)

## 1. Propósito y alcance

Explicar las métricas que CryoMetric calcula para cada ventana de temperatura
y potencia eléctrica, y cómo usarlas para interpretar la predicción de una cámara.
Por defecto, la ventana conserva hasta cinco minutos y treinta lecturas.
La temperatura se expresa en °C y la potencia en kW. El conteo de muestras
es una cantidad sin unidad.

## 2. Qué significa cada métrica

| Métrica | Cálculo e interpretación |
| --- | --- |
| Conteo (`sample_count`) | Cantidad de mediciones disponibles para esa variable. |
| Media (`media`) | Suma de las mediciones dividida por su cantidad. Un extremo puede desplazarla mucho. |
| Mediana (`mediana`) | Valor central de los datos ordenados. Si hay una cantidad par, se promedian los dos centrales. Permite comparar el centro de la serie con la media. |
| Desviación muestral (`std`, `std_temp`) | Dispersión respecto a la media. Es la raíz de la suma de diferencias al cuadrado dividida por n − 1. Cero indica mediciones iguales. Con menos de dos mediciones devuelve `None`, porque el divisor sería cero o faltan datos. |
| Mínimo y máximo | Menor y mayor medición de la ventana original. |
| Q1 y Q3 | Percentiles 25 y 75. Se calculan sobre datos ordenados, con interpolación lineal en la posición (n − 1) × p, contando desde cero. |
| IQR (`iqr`, `iqr_temp`) | Q3 − Q1. Describe la amplitud de la mitad central de las mediciones. |
| Atípico (`outlier`) | Temperatura fuera de los límites Q1 − factor × IQR y Q3 + factor × IQR. Se registra con su posición, timestamp y valor para revisión. |
| Pendiente (`pendiente_por_minuto`, `slope` en la API) | Cambio estimado de temperatura en °C/min mediante regresión lineal sobre las lecturas aceptadas. Positiva indica calentamiento y negativa enfriamiento. |
| Tiempo restante (`tiempo_restante_min`, `remaining_time_min` en la API) | Minutos estimados hasta el límite de temperatura, suponiendo que continúe la tendencia. |

`FACTOR_IQR = 1.5` es el multiplicador convencional de la regla de Tukey.
Un factor menor marca más lecturas y uno mayor marca menos. Se define en
`descriptive_stats.py`. Las temperaturas iguales a los límites se aceptan.
Con IQR cero, cualquier valor diferente de Q1/Q3 queda fuera de los límites.
La marca de atípico aporta un criterio de revisión estadística.

Las estadísticas describen todas las lecturas originales, incluidos los atípicos.
Para la regresión se excluyen las temperaturas marcadas y se conservan las
distancias temporales originales. La ventana y las lecturas excluidas quedan
auditables. La detección de atípicos se aplica a temperatura.

## 3. Cómo se calculan pendiente y tiempo restante

Con tiempos t en minutos y temperaturas T, la pendiente es

```text
m = suma[(t − media(t)) × (T − media(T))] / suma[(t − media(t))²]
tiempo restante = (límite de temperatura − última temperatura aceptada) / m
```

El código calcula primero con segundos y multiplica la pendiente por 60.
El tiempo restante toma como referencia el instante de la última lectura
aceptada (`reference_timestamp`). Si el dato más reciente es atípico, esa
referencia puede ser anterior a la última lectura recibida (`recorded_at`).

Con pendiente cero o negativa, el cálculo devuelve tiempo restante `None`.
Con pendiente positiva y temperatura aceptada que ya alcanzó el límite,
devuelve cero minutos. Una ventana insuficiente devuelve pendiente y tiempo
restante `None`. La API representa esos valores como `null` y la pantalla
los muestra como un guion.

El nivel predictivo depende del tiempo restante y del umbral de alerta.
Con el umbral por defecto de 40 minutos, se clasifica como CRITICO hasta
10 minutos, ALTO hasta 24, MEDIO hasta 40 y BAJO por encima de 40.
La alerta predictiva se activa hasta 40 minutos inclusive.
Con tiempo restante `None`, el contrato devuelve SIN_RIESGO.
Las infracciones de temperatura absoluta se revisan mediante HACCP.

## 4. Ejemplos reproducibles

En ambos ejemplos hay una muestra por minuto y se usa un límite de −10 °C
y un umbral de alerta de 40 minutos. El límite de −10 °C pertenece a la
demostración; en operación se usa la regla HACCP activa de la cámara o
el respaldo configurado.

| Resultado | Aumento real | Pico aislado |
| --- | --- | --- |
| Temperaturas | −18, −17, −16 | −18, −18.1, −17.9, −18, 20 |
| Conteo y duración | 3 muestras, 2 minutos | 5 muestras, 4 minutos |
| Media / mediana | −17 / −17 °C | −10.4 / −18 °C |
| Desviación muestral | 1 °C | Aproximadamente 16.994 °C |
| Q1 / Q3 / IQR | −17.5 / −16.5 / 1 °C | −18 / −17.9 / 0.1 °C |
| Límites IQR | −19 a −15 °C | −18.15 a −17.75 °C |
| Atípicos | Ninguno | 20 °C, índice 4, minuto 4 |
| Pendiente original | 1 °C/min | 7.61 °C/min |
| Pendiente con lecturas aceptadas | 1 °C/min | 0.02 °C/min |
| Tiempo restante | (−10 − (−16)) / 1 = 6 minutos | (−10 − (−18)) / 0.02 ≈ 400 minutos, desde el minuto 3 |
| Nivel / alerta predictiva | CRITICO / sí | BAJO / no |
| Condiciones de calidad | DATOS_VARIABLES | DATOS_VARIABLES y CON_ATIPICOS |

En la serie con pico, la regresión original tiene un numerador de 76.1 y
denominador de 10, de donde sale 7.61. Al excluir el pico, las cuatro lecturas
aceptadas tienen media −18 °C, numerador 0.1 y denominador 5.
Por eso la pendiente resulta 0.02 °C/min.

Desde PowerShell en la raíz del repositorio, con Python y NumPy disponibles:

```powershell
@'
import sys
from math import isclose
sys.path.insert(0, "microservices/worker-predictivo")
from predictor import calcular_pendiente, evaluar_riesgo

for temperaturas, pendiente_esperada, tiempo_esperado in [
    ([-18, -17, -16], 1, 6),
    ([-18, -18.1, -17.9, -18, 20], 0.02, 400),
]:
    tiempos = [i * 60 for i in range(len(temperaturas))]
    ventana = [
        {"timestamp": t, "temperature": temperatura}
        for t, temperatura in zip(tiempos, temperaturas)
    ]
    resultado = evaluar_riesgo(ventana, absolute_max_temp=-10)
    print("Temperaturas:", temperaturas)
    print("Pendiente original:", calcular_pendiente(tiempos, temperaturas))
    print("Pendiente aceptada:", resultado["pendiente_por_minuto"])
    print("Tiempo restante:", resultado["tiempo_restante_min"])
    print("Condiciones:", resultado["diagnostico"]["condiciones"])
    assert isclose(resultado["pendiente_por_minuto"], pendiente_esperada)
    assert isclose(resultado["tiempo_restante_min"], tiempo_esperado)
'@ | python -
```

La demo visual existente se genera ejecutando
`python microservices/worker-predictivo/tools/demo_estadistica.py`.
El script imprime la ubicación del informe HTML que se puede abrir en el navegador.

## 5. Interpretación en el dashboard

En **Calidad de datos y tendencia por cámara**, disponible para gerente y técnico,
se consulta la predicción guardada y su diagnóstico cada 15 segundos.
El diagnóstico por cámara del Panel Técnico permite desplegar los criterios
y las lecturas atípicas.

| Condición | Interpretación operativa |
| --- | --- |
| VENTANA_INSUFICIENTE | Menos de dos lecturas utilizables, sin separación temporal o con datos no finitos. La pantalla indica evaluación pendiente. |
| DATOS_VARIABLES | La desviación muestral de la ventana original alcanza el umbral configurado. Puede aparecer ante calentamiento sostenido o ante un extremo. |
| CON_ATIPICOS | Hay temperaturas fuera de los límites IQR que requieren revisión. |
| Lista de condiciones vacía | La ventana cumple los criterios de suficiencia y presenta baja dispersión y cero atípicos detectados. |

Las condiciones pueden coexistir. Para DATOS_VARIABLES se adopta inicialmente
`umbral_std_temp = 0.5` °C, configurable al evaluar y pendiente de validación
por el equipo. El riesgo se evalúa por separado con pendiente y tiempo restante.
Por ejemplo, la serie creciente tiene datos variables y riesgo crítico.
Una ventana insuficiente conserva SIN_RIESGO en el contrato, junto con
su condición de insuficiencia, que la pantalla presenta como evaluación pendiente.

Revisar siempre la fecha de la lectura y el conteo utilizable.
El dashboard avisa cuando las lecturas tienen más de dos minutos de antigüedad.
Las predicciones anteriores a M5 pueden tener `diagnostico: null`.
El resumen histórico de D4 usa el rango de fechas elegido y desviación
poblacional con divisor n. El bloque predictivo usa su ventana deslizante
y desviación muestral con divisor n − 1.

## 6. Revisión cruzada y validación con datos reales

| Actividad | Estado | Evidencia que debe registrar el equipo |
| --- | --- | --- |
| Reproducir los dos ejemplos contra el código | Verificado localmente | Comando de esta guía y valores esperados |
| Revisión por Diego/Alexis | Pendiente | Nombre, fecha y observaciones sobre fórmulas e interpretación en pantalla |
| Demo con Wokwi y los servicios activos | Pendiente | UUID de cámara, fecha, lecturas, predicción y captura o respuesta de la API |

Para la demo real, seguir la [verificación con Wokwi](predictivo-integracion.md#verificación-con-wokwi).
Comparar el diagnóstico de la API con la cámara seleccionada en pantalla
y observar una ventana estable, un incremento sostenido y una lectura atípica
entre mediciones estables. Registrar el límite HACCP usado y el intervalo real
entre mediciones, porque ambos afectan la predicción. Mantener este documento
en Borrador hasta completar la revisión cruzada y la demo.

## 7. Trazabilidad

- [Estadística descriptiva y límites IQR](../microservices/worker-predictivo/descriptive_stats.py).
- [Regresión, tiempo restante y diagnóstico](../microservices/worker-predictivo/predictor.py).
- [Componente del dashboard](../microservices/dashboard/src/components/shared/PredictionDiagnostics.jsx).
- [Casos matemáticos de M6](../microservices/worker-predictivo/tests/test_statistical_cases.py).
- [Contrato e integración de M5](predictivo-integracion.md).
