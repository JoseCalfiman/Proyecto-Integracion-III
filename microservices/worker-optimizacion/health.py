from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable

logger = logging.getLogger(__name__)

DEFAULT_HEALTH_PORT = 8080
HEALTH_PATH = "/health"


def build_health_payload(
    *,
    consumer_alive: bool,
    scheduler_running: bool,
    last_optimization_at: datetime | None,
) -> dict:
    """Estado que consultan Kubernetes y el System Controller."""
    if last_optimization_at is not None and last_optimization_at.tzinfo is None:
        last_optimization_at = last_optimization_at.replace(tzinfo=timezone.utc)
    alive = bool(consumer_alive) and bool(scheduler_running)
    return {
        "status": "ok" if alive else "degraded",
        "consumer_alive": bool(consumer_alive),
        "scheduler_running": bool(scheduler_running),
        "last_optimization_at": (
            last_optimization_at.isoformat() if last_optimization_at is not None else None
        ),
    }


class OptimizationHealth:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._last_optimization_at: datetime | None = None
        self._consumer_alive: Callable[[], bool] = lambda: False
        self._scheduler_running: Callable[[], bool] = lambda: False

    def configure(
        self,
        *,
        consumer_alive: Callable[[], bool],
        scheduler_running: Callable[[], bool],
    ) -> None:
        self._consumer_alive = consumer_alive
        self._scheduler_running = scheduler_running

    def mark_optimization(self, when: datetime | None = None) -> None:
        ts = when or datetime.now(timezone.utc)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        with self._lock:
            self._last_optimization_at = ts

    def reset(self) -> None:
        with self._lock:
            self._last_optimization_at = None
        self._consumer_alive = lambda: False
        self._scheduler_running = lambda: False

    def snapshot(self) -> dict:
        with self._lock:
            last = self._last_optimization_at
        return build_health_payload(
            consumer_alive=self._consumer_alive(),
            scheduler_running=self._scheduler_running(),
            last_optimization_at=last,
        )


health = OptimizationHealth()


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = self.path.split("?", 1)[0]
        if path != HEALTH_PATH:
            self.send_error(404)
            return
        payload = health.snapshot()
        body = json.dumps(payload).encode("utf-8")
        code = 200 if payload["status"] == "ok" else 503
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args) -> None:
        logger.debug("[health] " + fmt, *args)


def start_health_server(
    port: int | None = None,
    host: str = "0.0.0.0",
) -> ThreadingHTTPServer:
    bind_port = DEFAULT_HEALTH_PORT if port is None else port
    if port is None and os.getenv("HEALTH_PORT"):
        bind_port = int(os.environ["HEALTH_PORT"])
    server = ThreadingHTTPServer((host, bind_port), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, name="health", daemon=True)
    thread.start()
    logger.info("[health] escuchando en %s:%s%s", host, server.server_address[1], HEALTH_PATH)
    return server
