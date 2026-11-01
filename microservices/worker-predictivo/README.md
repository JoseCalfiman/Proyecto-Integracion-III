# Worker predictivo

Consume lecturas de temperatura de `sensor.raw`, mantiene una ventana por cámara
y estima con regresión lineal NumPy el tiempo hasta alcanzar el límite HACCP. Cada
predicción se guarda en TimescaleDB; si alcanza el umbral configurado, publica una
alerta en `sensor.anomaly`.

## Componentes

| Archivo | Función |
|---|---|
| `kafka_consumer.py` | Consume lecturas y coordina el flujo predictivo |
| `contract.py` | Valida y normaliza el contrato de los mensajes |
| `window.py` | Conserva lecturas recientes, ordenadas por cámara |
| `predictor.py` | Calcula pendiente, tiempo restante y nivel de riesgo |
| `haccp_predictions.py` | Consulta reglas y guarda predicciones |
| `db.py` / `models.py` | Sesiones y modelos de TimescaleDB |
| `config.py` | Configuración de Kafka, ventanas y umbrales |

## Pruebas

Desde este directorio:

```bash
python -m pytest
```
