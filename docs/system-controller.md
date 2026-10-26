#1.Propósito
El System Controller es un microservicio FastAPI que:

1-Consulta el estado de cada componente del sistema y lo expone en un único endpoint (GET /api/v1/system/status).
2-Permite reiniciar en Kubernetes los componentes autorizados (POST /api/v1/system/components/{name}/restart).

El panel técnico "Estado del Sistema" del Dashboard consume estos endpoints. Ningún otro servicio depende del Controller.

#2.Componentes monitoreados
El valor de name es el que aparece en el JSON y en la URL de reinicio (coincidir con el nombre del Deployment en Kubernetes)

| name                  | Workload en K8s                   | Cómo se verifica                                              | ¿Reiniciable? |
| --------------------- | --------------------------------- | ------------------------------------------------------------- | ------------- |
| `ingesta`             | Deployment                        | HTTP `GET http://ingesta-service:8000/health` + réplicas      | Sí            |
| `worker-predictivo`   | Deployment                        | Solo K8s (réplicas listas y restarts). No tiene servidor HTTP | Sí            |
| `worker-haccp`        | Deployment                        | Solo K8s                                                      | Sí            |
| `worker-optimizacion` | Deployment                        | Solo K8s                                                      | Sí            |
| `dashboard`           | Deployment                        | HTTP `GET http://dashboard-service:80/` + réplicas            | No            |
| `kafka`               | Deployment (pasará a StatefulSet) | Kafka AdminClient: broker, 4 tópicos y particiones            | No            |
| `timescaledb`         | Deployment                        | `SELECT 1` + réplicas                                         | No            |
| `mosquitto`           | Deployment                        | MQTT connect / auth / disconnect + réplicas                   | No            |

Checks de Kafka, DB y MQTT. Cada uno tiene dos etapas. Primero una conexión TCP de 1s: si nadie escucha, el componente queda `OFFLINE`. Si el puerto responde, corre el check real, con un timeout total de 3 s (2 s en la base de datos):

| Componente    | Check real                                                                                | Falla de este check                                                                    |
| ------------- | ----------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| `kafka`       | `AdminClient.list_topics`: hay broker, existen los 4 tópicos y cada partición tiene líder | `DEGRADED`, con detalle `Faltan tópicos: …` o `Particiones sin líder en: …`            |
| `timescaledb` | Conexión + `SELECT 1`                                                                     | `DEGRADED`: `Autenticación rechazada`, `La base de datos o el usuario no existe`, etc. |
| `mosquitto`   | CONNECT con el usuario `MQTT_CONTROLLER_USER`, espera CONNACK, DISCONNECT                 | `DEGRADED`: `Conexión rechazada: …` o `El broker no respondió al CONNECT`              |

Un fallo, un timeout o una excepción en cualquiera de ellos se captura dentro del check: el componente se marca `DEGRADED` y el Controller sigue respondiendo. Los `detail` son texto propio y no copian mensajes de las librerías, para no filtrar hosts ni usuarios. Los checks viven en `kafka_checker.py`, `database_checker.py` y `mqtt_checker.py`.

El propio System Controller no aparece en la lista: si la respuesta llega, está en línea. Su estado se consulta en `GET /health`.

Tópicos que debe tener Kafka: `sensor.raw`, `sensor.anomaly`, `haccp.alerts`, `optimization.reports`.

#3.Estados de un componente

| Estado     | Condición (se cumple cualquiera de las de esa fila)                                                                                                                  |
| ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ONLINE`   | Réplicas listas = réplicas deseadas (> 0) y el check funcional pasa y la latencia está bajo el umbral.                                                               |
| `DEGRADED` | Hay al menos 1 réplica lista, pero: (a) hay menos réplicas listas que las deseadas, o (b) el check funcional falla o da timeout, o (c) la latencia supera el umbral. |
| `OFFLINE`  | 0 réplicas listas, o el componente no responde en absoluto (conexión rechazada, fallo de DNS) cuando no hay información de Kubernetes.                               |

Reglas de apoyo:
-Un check funcional que falla nunca tumba al Controller: el error se captura y se refleja como `DEGRADED` o `OFFLINE` según la tabla en ese componente, con la causa en `detail`.
-Los workers no tienen check HTTP, así que su estado sale solo de las réplicas y restarts que informa Kubernetes.
-Sin ninguna fuente de información (sin check y sin acceso a la API de Kubernetes, por ejemplo con Docker Compose) el componente queda `DEGRADED` con `detail` "Sin información: ...". No se marca `ONLINE` ni `OFFLINE` porque no hay base para afirmarlo. -`latency_ms` es un entero (milisegundos redondeados, mínimo 1). `detail` nunca incluye nombres de host internos.
-Umbral de latencia: 1000 ms.
-Timeouts por check: HTTP 2s, DB 2s, Kafka 3s, MQTT 3s. Los checks corren en paralelo, así que una respuesta completa demora como máximo 3s.

#4.Estado global
El campo estado resume todo el sistema:

-`OFFLINE`: algún componente crítico está `OFFLINE`. Críticos: `ingesta`, `kafka`, `timescaledb`, `mosquitto`.

-`DEGRADED`: ningún crítico está `OFFLINE`, pero algún componente no está `ONLINE`.

-`ONLINE`: todos los componentes están `ONLINE`.
Ejemplo: un worker apagado deja el componente en `OFFLINE` y el sistema en `DEGRADED`.

#5.Endpoints
##5.1 `GET /health`
Salud del propio Controller. Para el healthcheck de Docker y los probes de Kubernetes.

```json
{ "status": "ok" }
```

##5.2 `GET /api/v1/system/status`
Responde siempre `200` con el estado completo, aunque haya componentes caídos (el panel necesita mostrarlos). Solo responde `503` si el propio Controller no puede calcular el estado. Ejemplo de Json de respuesta:

```json
{
  "status": "DEGRADED",
  "checked_at": "2026-10-15T18:30:00Z",
  "summary": { "total": 8, "online": 6, "degraded": 1, "offline": 1 },
  "components": [
    {
      "name": "ingesta",
      "type": "microservice",
      "status": "ONLINE",
      "latency_ms": 12,
      "detail": "HTTP 200 en /health",
      "last_check": "2026-10-15T18:30:00Z",
      "replicas": { "desired": 1, "ready": 1 },
      "restarts": 0,
      "restartable": true
    },
    {
      "name": "worker-predictivo",
      "type": "worker",
      "status": "OFFLINE",
      "latency_ms": null,
      "detail": "0/1 réplicas listas",
      "last_check": "2026-10-15T18:30:00Z",
      "replicas": { "desired": 1, "ready": 0 },
      "restarts": 3,
      "restartable": true
    },
    {
      "name": "worker-haccp",
      "type": "worker",
      "status": "ONLINE",
      "latency_ms": null,
      "detail": "1/1 réplicas listas",
      "last_check": "2026-10-15T18:30:00Z",
      "replicas": { "desired": 1, "ready": 1 },
      "restarts": 0,
      "restartable": true
    },
    {
      "name": "worker-optimizacion",
      "type": "worker",
      "status": "ONLINE",
      "latency_ms": null,
      "detail": "1/1 réplicas listas",
      "last_check": "2026-10-15T18:30:00Z",
      "replicas": { "desired": 1, "ready": 1 },
      "restarts": 1,
      "restartable": true
    },
    {
      "name": "dashboard",
      "type": "frontend",
      "status": "ONLINE",
      "latency_ms": 8,
      "detail": "HTTP 200 en /",
      "last_check": "2026-10-15T18:30:00Z",
      "replicas": { "desired": 1, "ready": 1 },
      "restarts": 0,
      "restartable": false
    },
    {
      "name": "kafka",
      "type": "infra",
      "status": "ONLINE",
      "latency_ms": 45,
      "detail": "Broker OK; 4/4 tópicos; 4 particiones",
      "last_check": "2026-10-15T18:30:00Z",
      "replicas": { "desired": 1, "ready": 1 },
      "restarts": 0,
      "restartable": false
    },
    {
      "name": "timescaledb",
      "type": "infra",
      "status": "ONLINE",
      "latency_ms": 5,
      "detail": "SELECT 1 OK",
      "last_check": "2026-10-15T18:30:00Z",
      "replicas": { "desired": 1, "ready": 1 },
      "restarts": 0,
      "restartable": false
    },
    {
      "name": "mosquitto",
      "type": "infra",
      "status": "DEGRADED",
      "latency_ms": 2100,
      "detail": "Conexión OK pero latencia sobre el umbral (2100 ms > 1000 ms)",
      "last_check": "2026-10-15T18:30:00Z",
      "replicas": { "desired": 1, "ready": 1 },
      "restarts": 0,
      "restartable": false
    }
  ]
}
```

Campos de primer nivel

| Campo        | Descripción                                                     |
| ------------ | --------------------------------------------------------------- |
| `status`     | `ONLINE` `DEGRADED` `OFFLINE`. Estado global (sección 4).       |
| `checked_at` | Fecha y hora ISO-8601 en UTC (`Z`) en que se armó la respuesta. |
| `summary`    | Conteos `total`, `online`, `degraded`, `offline` (enteros).     |
| `components` | Un objeto por componente, en el orden de la sección 2.          |

Campos de cada componente

| Campo         | ¿Puede ser null? | Descripción                                                                                                                  |
| ------------- | ---------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `name`        | No               | Nombre del componente.                                                                                                       |
| `type`        | No               | `microservice` `worker` `frontend` `infra`.                                                                                  |
| `status`      | No               | `ONLINE` `DEGRADED` `OFFLINE`.                                                                                               |
| `latency_ms`  | Sí               | Duración del check activo en ms. null si no hay check activo (workers) o no hubo respuesta.                                  |
| `detail`      | No               | Texto corto que explica el estado o la causa del fallo.                                                                      |
| `last_check`  | No               | ISO-8601 UTC del último check de ese componente.                                                                             |
| `replicas`    | Sí               | `{ "desired": int, "ready": int }`. null si no hay acceso a la API de Kubernetes (por ejemplo, corriendo en Docker Compose). |
| `restarts`    | Sí               | Suma de reinicios de los contenedores del componente. null en el mismo caso que `replicas`.                                  |
| `restartable` | No               | true si el componente está en la allowlist de reinicio. El panel lo usa para mostrar u ocultar el botón.                     |

##5.3 `POST /api/v1/system/components/{name}/restart`
Parchea la anotación `kubectl.kubernetes.io/restartedAt` del Deployment/StatefulSet, lo que dispara un reinicio ordenado.
Respuesta `202 Accepted`:

```json
{
  "name": "worker-predictivo",
  "action": "restart",
  "status": "RESTART_REQUESTED",
  "requested_at": "2026-10-15T18:31:00Z",
  "message": "Reinicio solicitado. El estado se actualizará en /api/v1/system/status."
}
```

Errores (formato FastAPI estándar `{"detail": "..."}`, que es el que ya lee el Dashboard en `error.response.data.detail`):

| Código | Cuándo                                              | Ejemplo de `detail`                             |
| ------ | --------------------------------------------------- | ----------------------------------------------- |
| `404`  | El nombre no existe en la lista de componentes.     | "Componente foo no existe"                      |
| `403`  | El componente existe, pero no está en la allowlist. | "El componente dashboard no se puede reiniciar" |
| `503`  | No se pudo contactar la API de Kubernetes.          | "No se pudo contactar la API de Kubernetes"     |

El reinicio es asíncrono: el `202` solo confirma que se solicitó. El estado real se ve consultando `/status`.

#6.Rutas públicas (API Gateway)
Nginx es el único punto de entrada del Dashboard. El navegador solo habla con Nginx, y Nginx enruta cada petición al servicio correcto:

| Desde el navegador                            | Lo que recibe el servicio                                   |
| --------------------------------------------- | ----------------------------------------------------------- |
| `GET /api/v1/*`                               | Ingesta: `GET /api/v1/*` (misma ruta)                       |
| `GET /control-api/status`                     | Controller: `GET /api/v1/system/status`                     |
| `POST /control-api/components/{name}/restart` | Controller: `POST /api/v1/system/components/{name}/restart` |

Nginx reemplaza el prefijo `/control-api/` por `/api/v1/system/`:

```nginx
location ^~ /control-api/ {
    proxy_pass http://system-controller-service:8000/api/v1/system/;
}
```

Si el Controller no responde, Nginx devuelve `503` con `{"detail": "System Controller no disponible"}`, el mismo formato de error que ya lee el Dashboard.

#7.Frecuencia
-El panel consulta `/status` cada 5s.
-El Controller no guarda historial: cada llamada ejecuta los checks en el momento.
