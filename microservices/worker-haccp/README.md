Responsable: Eduardo Dominguez

Microservicio que escucha los eventos de riesgo (alerta_tecnica) publicados en Redis, aplica las reglas HACCP definidas (por ejemplo, temperatura > 4°C por más de 2 minutos). Además, guarda un log de cada alerta en la base de datos.

## Reglas HACCP

La tabla `haccp_rules` mantiene una regla activa por cámara con estos campos:

| Campo | Uso | Valor por defecto |
| --- | --- | ---: |
| `rule_id` | Identificador de la regla | generado por la base de datos |
| `chamber_id` | Cámara a la que aplica | obligatorio |
| `absolute_max_temp` | Temperatura máxima absoluta (°C) | `4.00` |
| `absolute_min_temp` | Temperatura mínima absoluta (°C) | `-30.00` |
| `tolerance_time_min` | Tiempo tolerado fuera de rango | `15` minutos |
| `is_active` | Indica si la regla se aplica | `TRUE` |
| `created_at` | Fecha de creación | fecha actual |
| `modified_by_user_id` | Usuario que modificó la regla | `NULL` para reglas iniciales |

`create_default_rules_for_all_chambers(session)` inserta una regla por cada
cámara que todavía no tenga una regla. Es idempotente y conserva las reglas
existentes. La función debe ejecutarse después de que existan las cámaras y
las tablas `chambers`, `users` y `haccp_rules`.

`validar_haccp(alerta_predictiva, regla_camara)` devuelve `True` cuando la
temperatura prevista supera `absolute_max_temp` o cuando
`remaining_time_min` es menor que `tolerance_time_min`. La regla se recibe
como argumento para que cada cámara pueda tener límites diferentes.



├── worker-haccp/                  # Worker HACCP y Alertas (Eduardo)
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── main.py                    # Lógica principal (consumer Kafka)
│   │   ├── config.py                  # Configuración desde .env
│   │   ├── models.py                  # Modelos SQLAlchemy
│   │   ├── haccp_validator.py         # Validación de reglas HACCP
│   │   ├── kafka_consumer.py          # Consumidor de Kafka
│   │   ├── crud.py                    # Operaciones CRUD en base de datos
│   │   ├── tests/
│   │   │   ├── test_haccp.py
│   │   │   └── test_kafka.py
│   │   └── __init__.py