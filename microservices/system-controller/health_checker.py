import asyncio
import logging
import os
import socket
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Awaitable, Callable, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlparse

import httpx

from schemas import ComponentStatus, Replicas, Status, Summary, SystemStatus

logger = logging.getLogger("system-controller")


@dataclass(frozen=True)
class CheckResult:
    reachable: bool  
    ok: bool  
    latency_ms: Optional[int]
    detail: str


@dataclass(frozen=True)
class Component:
    name: str  
    type: str 
    critical: bool = False  
    restartable: bool = False
    kind: str = "Deployment"
    check: Optional[Callable[[], Awaitable[CheckResult]]] = None
    timeout: float = 3.0
    # Si no hay URL de salud, se mide cada pod por su IP (puerto y ruta) usando la API de Kubernetes.
    pod_health_port: Optional[int] = None
    pod_health_path: str = "/health"


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _elapsed_ms(start: float) -> int:
    return max(1, round((time.perf_counter() - start) * 1000))


# A partir de cuántos reinicios acumulados se avisa en el detalle (J6).
RESTART_WARN_THRESHOLD = int(os.getenv("RESTART_WARN_THRESHOLD", "3"))


def classify_network_error(exc: BaseException) -> str:
    """Recorre la cadena de causas y devuelve: 'dns', 'refused', 'timeout' u 'other'."""
    seen = 0
    while exc is not None and seen < 8:
        if isinstance(exc, socket.gaierror):
            return "dns"
        if isinstance(exc, ConnectionRefusedError):
            return "refused"
        if isinstance(exc, (TimeoutError, asyncio.TimeoutError)):
            return "timeout"
        exc = exc.__cause__ or exc.__context__
        seen += 1
    return "other"


def http_unhealthy_hint(code: int) -> str:
    if code in (401, 403):
        return "exige autenticación (la ruta de salud no debería pedirla)"
    if code == 404:
        return "la ruta de salud no existe en el servicio"
    if code >= 500:
        return "el servicio responde pero se declara no saludable"
    return "respuesta inesperada del servicio"


# ----------------------------------------------------------------- checks
# Los detalles NO incluyen nombres de host internos a propósito

async def check_http(url: str, timeout: float) -> CheckResult:
    start = time.perf_counter()
    path = urlparse(url).path or "/"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
    except httpx.TimeoutException:
        return CheckResult(False, False, None, f"Timeout (> {timeout:g} s) en {path}: el servicio no contestó a tiempo (lento o bloqueado)")
    except httpx.HTTPError as exc:
        kind = classify_network_error(exc)
        if kind == "dns":
            msg = f"No se resuelve el nombre del servicio (DNS) al consultar {path}: revisa que su Service exista"
        elif kind == "refused":
            msg = f"Conexión rechazada en {path}: el proceso no está escuchando (¿se cayó o está iniciando?)"
        else:
            msg = f"No responde en {path} ({type(exc).__name__})"
        return CheckResult(False, False, None, msg)
    latency = _elapsed_ms(start)
    detail = f"HTTP {response.status_code} en {path}"
    if not response.is_success:
        detail += f": {http_unhealthy_hint(response.status_code)}"
    return CheckResult(True, response.is_success, latency, detail)


async def check_pods_http(pods: Sequence, port: int, path: str, timeout: float) -> CheckResult:
    """Consulta /health de cada pod en paralelo. Latencia = la del pod más lento (peor caso).
    El detalle nunca incluye IPs ni nombres de host internos."""
    if not pods:
        return CheckResult(False, False, None, "Sin pods en ejecución para consultar")
    results = await asyncio.gather(*(check_http(f"http://{p.ip}:{port}{path}", timeout) for p in pods))
    total = len(results)
    healthy = sum(1 for r in results if r.ok)
    latencies = [r.latency_ms for r in results if r.latency_ms is not None]
    worst = max(latencies) if latencies else None
    if healthy == total:
        return CheckResult(True, True, worst, f"{results[0].detail} ({healthy}/{total} pods)")
    if not any(r.reachable for r in results):
        return CheckResult(False, False, None, f"{total} pods sin respuesta en {path}: {results[0].detail}")
    bad = next(r for r in results if not r.ok)
    return CheckResult(True, False, worst, f"{healthy}/{total} pods saludables en {path}: {bad.detail}")


async def check_tcp(host: str, port: int, timeout: float) -> CheckResult:
    start = time.perf_counter()
    try:
        _, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout)
    except asyncio.TimeoutError:
        return CheckResult(False, False, None, f"Timeout (> {timeout:g} s) en el puerto {port}: el servicio no contestó a tiempo (lento o bloqueado)")
    except OSError as exc:
        kind = classify_network_error(exc)
        if kind == "dns":
            msg = f"No se resuelve el nombre del servicio (DNS) en el puerto {port}: revisa que su Service exista"
        elif kind == "refused":
            msg = f"Conexión rechazada en el puerto {port}: nada escucha ahí (¿se cayó o está iniciando?)"
        else:
            msg = f"No responde en el puerto {port}"
        return CheckResult(False, False, None, msg)
    latency = _elapsed_ms(start)
    writer.close()
    try:
        await writer.wait_closed()
    except OSError:
        pass
    return CheckResult(True, True, latency, f"Puerto {port} abierto (check TCP básico)")


async def layered_check(
    host: str,
    port: int,
    timeout: float,
    deep: Callable[[float], Tuple[bool, str]],
    tcp_timeout: float = 1.0,
) -> CheckResult:
    start = time.perf_counter()
    tcp = await check_tcp(host, port, min(tcp_timeout, timeout))
    if not tcp.reachable:
        return tcp
    remaining = max(0.5, timeout - (time.perf_counter() - start))
    try:
        ok, detail = await asyncio.wait_for(asyncio.to_thread(deep, remaining), remaining + 0.5)
    except asyncio.TimeoutError:
        return CheckResult(True, False, None, f"Timeout (> {timeout:g} s) en el check")
    except Exception as exc:
        logger.warning("El check profundo en el puerto %s falló: %s: %s", port, type(exc).__name__, exc)
        return CheckResult(True, False, None, f"El check falló ({type(exc).__name__})")
    return CheckResult(True, ok, _elapsed_ms(start), detail)


# ----------------------------------------------------------------- reglas
def _derive_base(
    replicas: Optional[Replicas],
    check: Optional[CheckResult],
    latency_threshold_ms: int,
) -> Tuple[Status, str]:
    if replicas is not None:
        if replicas.desired == 0:
            return Status.OFFLINE, "Apagado (0 réplicas deseadas)"
        if replicas.ready == 0:
            return Status.OFFLINE, f"0/{replicas.desired} réplicas listas"
        if replicas.ready < replicas.desired:
            return Status.DEGRADED, f"{replicas.ready}/{replicas.desired} réplicas listas"

    if check is None:
        if replicas is not None:
            return Status.ONLINE, f"{replicas.ready}/{replicas.desired} réplicas listas"
        return Status.DEGRADED, "Sin información: no hay check disponible ni acceso a Kubernetes"

    if not check.reachable:
        return (Status.DEGRADED if replicas is not None else Status.OFFLINE), check.detail
    if not check.ok:
        return Status.DEGRADED, check.detail
    if check.latency_ms is not None and check.latency_ms > latency_threshold_ms:
        return (
            Status.DEGRADED,
            f"{check.detail}; latencia sobre el umbral ({check.latency_ms} ms > {latency_threshold_ms} ms)",
        )
    return Status.ONLINE, check.detail


def derive_status(
    replicas: Optional[Replicas],
    check: Optional[CheckResult],
    latency_threshold_ms: int,
    *,
    issue: Optional[str] = None,
    restarts: Optional[int] = None,
    last_restart_reason: Optional[str] = None,
    scale_hint: Optional[str] = None,
) -> Tuple[Status, str]:
    """Estado + detalle con una pista accionable (J6). Sin datos extra, el texto no cambia."""
    status, detail = _derive_base(replicas, check, latency_threshold_ms)
    parts = [detail]
    if replicas is not None and replicas.desired == 0 and scale_hint:
        parts.append(f"alguien lo escaló a 0; para encenderlo: {scale_hint}")
    elif replicas is not None and replicas.ready < replicas.desired and issue:
        parts.append(issue)
    if restarts is not None and restarts >= RESTART_WARN_THRESHOLD:
        extra = f"{restarts} reinicios acumulados"
        if last_restart_reason:
            extra += f" (último motivo: {last_restart_reason})"
        parts.append(extra)
    return status, " — ".join(parts)


def derive_global(statuses: Dict[str, Status], critical: Sequence[str]) -> Status:
    if any(statuses.get(name) == Status.OFFLINE for name in critical):
        return Status.OFFLINE
    if any(s != Status.ONLINE for s in statuses.values()):
        return Status.DEGRADED
    return Status.ONLINE


# ------------------------------------------------------------ orquestación
async def _noop():
    return None


async def _run_probes(component: Component, k8s) -> Tuple[Optional[CheckResult], Optional[object]]:
    check_coro = component.check() if component.check else _noop()
    k8s_coro = (
        asyncio.to_thread(k8s.get_workload_status, component.name, component.kind)
        if k8s is not None and k8s.available
        else _noop()
    )
    check_res, workload = await asyncio.gather(check_coro, k8s_coro, return_exceptions=True)

    if isinstance(check_res, BaseException):
        logger.exception("El check de '%s' lanzó una excepción", component.name, exc_info=check_res)
        check_res = CheckResult(True, False, None, "Error interno al ejecutar el check")
    if isinstance(workload, BaseException):
        logger.warning("Lectura de Kubernetes falló para '%s': %s", component.name, workload)
        workload = None

    # Un check mal escrito no debe tumbar todo.
    if check_res is not None and not isinstance(check_res, CheckResult):
        logger.error("El check de '%s' devolvió %s en vez de CheckResult", component.name, type(check_res).__name__)
        check_res = CheckResult(True, False, None, "Error interno: el check devolvió un resultado inválido")

    # Sin URL de salud: medir cada pod por su IP (Kubernetes ya nos dijo cuáles son).
    if (
        check_res is None
        and component.pod_health_port
        and workload is not None
        and getattr(workload, "pods", ())
    ):
        try:
            check_res = await check_pods_http(
                workload.pods, component.pod_health_port, component.pod_health_path, 2.0
            )
        except Exception:
            logger.exception("El chequeo por pods de '%s' lanzó una excepción", component.name)
            check_res = CheckResult(True, False, None, "Error interno al consultar los pods")
    return check_res, workload


async def evaluate_component(component: Component, k8s, latency_threshold_ms: int) -> ComponentStatus:
    try:
        check_res, workload = await asyncio.wait_for(
            _run_probes(component, k8s), timeout=component.timeout + 1
        )
    except asyncio.TimeoutError:
        check_res = CheckResult(False, False, None, f"Timeout (> {component.timeout:g} s)")
        workload = None
    except Exception:  
        logger.exception("Error evaluando '%s'", component.name)
        check_res = CheckResult(True, False, None, "Error interno al evaluar el componente")
        workload = None

    replicas = (
        Replicas(desired=workload.desired, ready=workload.ready) if workload is not None else None
    )
    kind = getattr(component, "kind", "Deployment")
    scale_hint = f"kubectl scale {'sts' if kind == 'StatefulSet' else 'deploy'}/{component.name} --replicas=1"
    status, detail = derive_status(
        replicas, check_res, latency_threshold_ms,
        issue=getattr(workload, "issue", None),
        restarts=workload.restarts if workload is not None else None,
        last_restart_reason=getattr(workload, "last_restart_reason", None),
        scale_hint=scale_hint,
    )
    return ComponentStatus(
        name=component.name,
        type=component.type,
        status=status,
        latency_ms=check_res.latency_ms if check_res else None,
        detail=detail,
        last_check=_now(),
        replicas=replicas,
        restarts=workload.restarts if workload is not None else None,
        restartable=component.restartable,
    )


async def collect_status(
    components: Sequence[Component], k8s, latency_threshold_ms: int
) -> SystemStatus:
    """Evalúa TODOS los componentes en paralelo y arma la respuesta."""
    results: List[ComponentStatus] = await asyncio.gather(
        *(evaluate_component(c, k8s, latency_threshold_ms) for c in components)
    )
    statuses = {r.name: r.status for r in results}
    critical = [c.name for c in components if c.critical]
    return SystemStatus(
        status=derive_global(statuses, critical),
        checked_at=_now(),
        summary=Summary(
            total=len(results),
            online=sum(1 for r in results if r.status == Status.ONLINE),
            degraded=sum(1 for r in results if r.status == Status.DEGRADED),
            offline=sum(1 for r in results if r.status == Status.OFFLINE),
        ),
        components=list(results),
    )
