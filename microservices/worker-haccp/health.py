import json
import logging
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock
from typing import Any

logger = logging.getLogger(__name__)


class WorkerHealth:
    def __init__(self) -> None:
        self._lock = Lock()
        self._consumer_operational = False
        self._consumer_poll_error = False
        self._kafka_checked = False
        self._kafka_connected = False
        self._last_processed_at: datetime | None = None
        self._stopped = False

    def set_consumer_operational(self, operational: bool) -> None:
        with self._lock:
            self._consumer_operational = operational
            if operational:
                self._stopped = False

    def set_kafka_connected(self, connected: bool) -> None:
        with self._lock:
            self._kafka_checked = True
            self._kafka_connected = connected

    def set_consumer_poll_error(self, failed: bool) -> None:
        with self._lock:
            self._consumer_poll_error = failed

    def mark_processed(self) -> None:
        with self._lock:
            self._last_processed_at = datetime.now(timezone.utc)

    def mark_stopped(self) -> None:
        with self._lock:
            self._consumer_operational = False
            self._stopped = True

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            if self._stopped or self._consumer_poll_error or (
                self._kafka_checked and not self._kafka_connected
            ):
                status = "unhealthy"
            elif (
                not self._consumer_operational
                or not self._kafka_checked
            ):
                status = "starting"
            else:
                status = "healthy"

            last_processed_at = self._last_processed_at
            return {
                "status": status,
                "kafka_connected": self._kafka_connected,
                "last_processed_at": (
                    last_processed_at.isoformat().replace("+00:00", "Z")
                    if last_processed_at is not None
                    else None
                ),
                "consumer_operational": self._consumer_operational,
            }

    def liveness_snapshot(self) -> dict[str, Any]:
        with self._lock:
            status = (
                "unhealthy"
                if self._stopped
                else "alive"
                if self._consumer_operational
                else "starting"
            )
            return {
                "status": status,
                "consumer_operational": self._consumer_operational,
            }


class HealthHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def create_health_handler(health: WorkerHealth) -> type[BaseHTTPRequestHandler]:
    class HealthHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path == "/health":
                snapshot = health.snapshot()
                http_status = 200 if snapshot["status"] == "healthy" else 503
            elif self.path == "/live":
                snapshot = health.liveness_snapshot()
                http_status = 200 if snapshot["status"] == "alive" else 503
            else:
                self.send_error(404)
                return

            response = json.dumps(snapshot).encode("utf-8")
            self.send_response(http_status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)

        def log_message(self, format: str, *args: Any) -> None:
            logger.debug("Health HTTP: " + format, *args)

    return HealthHandler
