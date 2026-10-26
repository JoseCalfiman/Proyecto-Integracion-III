import json
import threading
import urllib.error
import urllib.request
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer

from health import HealthHandler, build_health_payload, health, start_health_server


def setup_function() -> None:
    health.reset()


def test_health_payload_ok_when_consumer_and_scheduler_are_up():
    when = datetime(2026, 10, 17, 15, 0, tzinfo=timezone.utc)
    payload = build_health_payload(
        consumer_alive=True,
        scheduler_running=True,
        last_optimization_at=when,
    )
    assert payload == {
        "status": "ok",
        "consumer_alive": True,
        "scheduler_running": True,
        "last_optimization_at": "2026-10-17T15:00:00+00:00",
    }


def test_health_payload_degraded_without_scheduler_or_consumer():
    no_scheduler = build_health_payload(
        consumer_alive=True,
        scheduler_running=False,
        last_optimization_at=None,
    )
    no_consumer = build_health_payload(
        consumer_alive=False,
        scheduler_running=True,
        last_optimization_at=None,
    )
    assert no_scheduler["status"] == "degraded"
    assert no_scheduler["scheduler_running"] is False
    assert no_scheduler["last_optimization_at"] is None
    assert no_consumer["status"] == "degraded"
    assert no_consumer["consumer_alive"] is False


def test_health_endpoint_exposes_live_state():
    health.configure(consumer_alive=lambda: True, scheduler_running=lambda: True)
    health.mark_optimization(datetime(2026, 10, 17, 12, 30, tzinfo=timezone.utc))
    server = start_health_server(port=0, host="127.0.0.1")
    try:
        status, body = _get(server, "/health")
        assert status == 200
        assert body["status"] == "ok"
        assert body["consumer_alive"] is True
        assert body["scheduler_running"] is True
        assert body["last_optimization_at"] == "2026-10-17T12:30:00+00:00"
    finally:
        server.shutdown()
        server.server_close()


def test_health_endpoint_returns_503_when_scheduler_is_down():
    health.configure(consumer_alive=lambda: True, scheduler_running=lambda: False)
    server = ThreadingHTTPServer(("127.0.0.1", 0), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status, body = _get(server, "/health")
        assert status == 503
        assert body["status"] == "degraded"
        assert body["scheduler_running"] is False
        assert body["last_optimization_at"] is None
    finally:
        server.shutdown()
        server.server_close()


def test_health_endpoint_unknown_path_is_404():
    server = ThreadingHTTPServer(("127.0.0.1", 0), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        status, _ = _get(server, "/status")
        assert status == 404
    finally:
        server.shutdown()
        server.server_close()


def _get(server: ThreadingHTTPServer, path: str) -> tuple[int, dict | None]:
    port = server.server_address[1]
    url = f"http://127.0.0.1:{port}{path}"
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            raw = response.read().decode("utf-8")
            return response.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            body = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            body = None
        return exc.code, body
