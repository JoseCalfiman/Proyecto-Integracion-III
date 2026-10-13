# Fundamentos matemáticos

> **Estado:** Borrador
> **Área SWEBOK:** KA17 — Mathematical Foundations
> **Responsable:** Matías Cárcamo
> **Última actualización:** 2026-10-06
> **Documentos relacionados:** [Modelos y métodos](../11-modelos-metodos/modelos-metodos.md)

## 1. Propósito

Documentar el sustento matemático de los cálculos del sistema.

## 2. Regresión lineal (worker predictivo)

Ajuste por mínimos cuadrados de la temperatura en función del tiempo:

```
y = m·x + b        (m = pendiente, b = intercepto)
```

La pendiente `m` se obtiene con `sklearn.linear_model.LinearRegression`.

## 3. Tiempo restante estimado

```
tiempo_restante = (absolute_max_temp - temp_actual) / pendiente
```

- Si `pendiente <= 0` → no hay riesgo.
- `absolute_max_temp` proviene de `haccp_rules`.

## 4. Logic y conjuntos

Reglas de decisión (lógica booleana) para HACCP:

```
alerta = (temperatura > max_absoluta) AND (tiempo_restante < tolerancia_min)
```

## 5. Estadística y series de tiempo

- Agregación de ventana deslizante (5 min / 30 muestras).
- Pronóstico de series de tiempo con **Prophet**.
- Cálculo de ahorro: reducción de consumo × `precio_kwh` (CLP).

## 6. Pendiente

Formalización de errores del modelo, validación estadística y métricas de error
(MAE/RMSE).
