# D6: panel técnico con datos reales

Validado el 19 de noviembre de 2026. Se reconstruyeron ingesta y dashboard.
La comparación de IDs se realizó con SQL en una transacción de solo lectura y
peticiones HTTP al servicio real usando un JWT temporal de técnico activo.
No se insertaron ni borraron registros de la base de desarrollo.

| Endpoint bajo /api/v1 | HTTP | Resultado contrastado con SQL |
| --- | --- | --- |
| /panel/gateways | 200 | 4 cámaras; UUID 22222222-2222-2222-2222-222222222222, 44444444-4444-4444-4444-444444444444, 55555555-5555-5555-5555-555555555555, 66666666-6666-6666-6666-666666666666 |
| /panel/sensores | 200 | 4 sensores; IDs 1, 2, 3, 4 |
| /panel/alertas | 200 | 2 alertas; IDs 2, 1 |
| /panel/health | 200 | degraded: db=ok, kafka=error, mqtt=ok |

También se verificaron los conteos de sensores por cámara y la última lectura
por ID de sensor contra SQL, campos de batería/ping nulos y conectividad de
cámara desconocida. Las cuatro rutas devolvieron 401 sin token y 403 con gerente.
El error de Kafka se informa tal como lo observa el productor de ingesta; no se
reemplaza por un éxito supuesto ni significa que se haya diagnosticado su causa.

La suite `test_panel.py` aprobó seis pruebas, incluidas las pruebas heredadas de
permisos. Verifica inventarios vacíos, cámaras inactivas, asociación de lecturas
por sensor (sin atribuir datos de cámara a sensores sin lecturas), alertas,
permisos y salud degradada. Usa SQLite en memoria con `get_db` sustituido.
Se ejecutó con `DATABASE_URL=sqlite://` y los tests montados en solo lectura:

```bash
docker compose run --rm --no-deps -e DATABASE_URL=sqlite:// \
  -v "$PWD/microservices/ingesta/tests:/app/tests:ro" \
  ingesta python -B -m unittest discover -s tests -p test_panel.py -v
```

La compilación Vite del dashboard pasó dentro de Docker. Se eliminaron los
inventarios y alertas ficticios, el uptime fijo y el tráfico simulado del panel.
Los campos sin telemetría se presentan como desconocidos o sin dato.
