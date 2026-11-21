# Pruebas estadísticas del Predictor (M6)

Desde la raíz del repositorio, usando un entorno con las dependencias del worker:

```powershell
python -m pytest -q microservices/worker-predictivo/tests
python -m pytest -v microservices/worker-predictivo/tests/test_statistical_cases.py
```

La batería de `test_statistical_cases.py` contiene diez casos con resultados
calculables a mano.

| Caso | Resultado esperado |
| --- | --- |
| Media frente a mediana con extremo | [-18,-18,-18,-18,20] tiene media −10,4 y mediana −18 |
| Serie estable | Desviación muestral cero |
| Cuartiles interpolados | [1,2,3,4] tiene Q1=1,75, Q3=3,25 e IQR=1,5 |
| Atípico sin mutación | El 20 de la serie controlada se identifica en el índice 4 |
| Tendencia creciente | [-18,-17,-16], cada minuto, da 1 °C/min |
| Tendencia decreciente | [-16,-17,-18] da −1 °C/min, sin tiempo restante ni alerta |
| Tiempo restante | Desde −16 hasta −10 a 1 °C/min faltan 6 minutos |
| Tiempos irregulares | Muestras a 0,30,120 s con −18,−17,5,−16 conservan 1 °C/min |
| Límite alcanzado | Temperatura −10, límite −10 y pendiente positiva dan 0 minutos |
| Atípico interior | Excluir el pico conserva los tiempos y da 0,1 °C/min y 76 min |

Los archivos previos complementan estos casos con ventanas vacías, unitarias,
variables, no finitas, timestamps datetime y sin separación temporal, IQR y
diagnóstico. `test_consumer.py` verifica eventos sin Kafka real y
`test_persist_diagnostics.py` comprueba el diagnóstico serializable de M5.

El test de integración HTTP en `microservices/ingesta/tests/test_predictions.py`
ejecuta el Predictor aislado, guarda su diagnóstico en SQLite y lo consulta por
la API, incluyendo la compatibilidad con predicciones anteriores sin diagnóstico.
