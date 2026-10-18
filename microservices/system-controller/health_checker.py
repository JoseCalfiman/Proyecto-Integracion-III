import asyncio
import logging
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


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _elapsed_ms(start: float) -> int:
    return max(1, round((time.perf_counter() - start) * 1000))


# ----------------------------------------------------------------- checks
# Los detalles NO incluyen nombres de host internos a propósito

async def check_http(url: str, timeout: float) -> CheckResult:
    start = time.perf_counter()
    path = urlparse(url).path or "/"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
    except httpx.TimeoutException:
        return CheckResult(False, False, None, f"Timeout (> {timeout:g} s) en {path}")
    except httpx.HTTPError as exc:
        return CheckResult(False, False, None, f"No responde en {path} ({type(exc).__name__})")
    latency = _elapsed_ms(start)
    detail = f"HTTP {response.status_code} en {path}"
    return CheckResult(True, response.is_success, latency, detail)


async def check_tcp(host: str, port: int, timeout: float) -> CheckResult:
    start = time.perf_counter()
    try:
        _, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout)
    except asyncio.TimeoutError:
        return CheckResult(False, False, None, f"Timeout (> {timeout:g} s) en el puerto {port}")
    except OSError:
        return CheckResult(False, False, None, f"No responde en el puerto {port}")
    latency = _elapsed_ms(start)
    writer.close()
    try:
        await writer.wait_closed()
    except OSError:
        pass
    return CheckResult(True, True, latency, f"Puerto {port} abierto (check TCP básico)")


# ----------------------------------------------------------------- reglas
def derive_status(
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
    status, detail = derive_status(replicas, check_res, latency_threshold_ms)
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
