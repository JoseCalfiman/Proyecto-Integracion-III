import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Tuple

logger = logging.getLogger("system-controller")

NAMESPACE_FILE = "/var/run/secrets/kubernetes.io/serviceaccount/namespace"
REQUEST_TIMEOUT_SECONDS = 3
RESTART_ANNOTATION = "kubectl.kubernetes.io/restartedAt"

# SEGURIDAD: lo único que este servicio puede reiniciar, pase lo que pase.
# Ni la variable RESTART_ALLOWLIST ni un cambio en components.py pueden ampliarlo.
# Debe coincidir con los resourceNames del permiso "patch" en k8s/system-controller/rbac.yaml.
RESTARTABLE_WORKLOADS = frozenset(
    {"ingesta", "worker-predictivo", "worker-haccp", "worker-optimizacion"}
)


@dataclass(frozen=True)
class PodTarget:
    """Un pod en ejecución que se puede consultar por HTTP (sin exponer su IP en la API)."""
    name: str
    ip: str


@dataclass(frozen=True)
class WorkloadInfo:
    desired: int
    ready: int
    restarts: Optional[int]
    pods: Tuple[PodTarget, ...] = ()
    issue: Optional[str] = None  
    last_restart_reason: Optional[str] = None  


@dataclass(frozen=True)
class RestartOutcome:
    kind: str 
    requested_at: datetime  

@dataclass(frozen=True)
class RolloutInfo:
    phase: str  # IN_PROGRESS | COMPLETE | UNKNOWN
    desired: int
    updated: int
    ready: int
    available: int
    message: str


# ----------------------------------------------------------- diagnóstico 
_IMAGE_PULL = "No se puede descargar la imagen ({r}): revisa el nombre/tag de la imagen y el acceso al registro"
WAITING_ISSUES = {
    "CrashLoopBackOff": "El contenedor se cae una y otra vez (CrashLoopBackOff): revisa sus logs con kubectl logs --previous",
    "ImagePullBackOff": _IMAGE_PULL.format(r="ImagePullBackOff"),
    "ErrImagePull": _IMAGE_PULL.format(r="ErrImagePull"),
    "InvalidImageName": "El nombre de la imagen es inválido (InvalidImageName)",
    "CreateContainerConfigError": "Falta un ConfigMap, un Secret o una variable (CreateContainerConfigError)",
    "CreateContainerError": "Kubernetes no pudo crear el contenedor (CreateContainerError)",
    "RunContainerError": "El contenedor no pudo arrancar (RunContainerError)",
}
OOM_ISSUE = "Se quedó sin memoria (OOMKilled): sube el límite de memoria del contenedor"


def _terminated(state):
    return getattr(state, "terminated", None) if state is not None else None


def diagnose_pods(pod_items) -> Tuple[Optional[str], Optional[str]]:
    """Mira los pods de un workload y devuelve (causa_probable, último_motivo_de_reinicio). Nunca incluye IPs ni nombres de pods."""
    best: Optional[Tuple[int, str]] = None
    last_reason: Optional[str] = None

    def consider(prio: int, text: str) -> None:
        nonlocal best
        if best is None or prio < best[0]:
            best = (prio, text)

    for pod in pod_items or []:
        meta = getattr(pod, "metadata", None)
        status = getattr(pod, "status", None)
        if status is None or getattr(meta, "deletion_timestamp", None) is not None:
            continue
        if getattr(status, "phase", None) in ("Succeeded",):
            continue
        statuses = getattr(status, "container_statuses", None) or []
        pod_ready = bool(statuses) and all(getattr(cs, "ready", False) for cs in statuses)

        for cs in statuses:
            last = _terminated(getattr(cs, "last_state", None))
            if last is not None and getattr(last, "reason", None):
                if last_reason is None or last.reason == "OOMKilled":
                    last_reason = last.reason
            if getattr(cs, "ready", False):
                continue
            waiting = getattr(getattr(cs, "state", None), "waiting", None)
            now_term = _terminated(getattr(cs, "state", None))
            if waiting is not None and getattr(waiting, "reason", None):
                reason = waiting.reason
                if reason in WAITING_ISSUES:
                    consider(1, WAITING_ISSUES[reason])
                elif reason == "ContainerCreating":
                    consider(6, "El contenedor se está creando")
                else:
                    consider(5, f"Esperando: {reason}")
                if last is not None and getattr(last, "reason", None) == "OOMKilled":
                    consider(0, OOM_ISSUE)  # la causa de fondo (memoria) gana al síntoma (CrashLoopBackOff)
            elif now_term is not None:
                if getattr(now_term, "reason", None) == "OOMKilled":
                    consider(2, OOM_ISSUE)
                else:
                    code = getattr(now_term, "exit_code", None)
                    consider(3, f"El contenedor terminó con error (código {code})" if code is not None
                             else "El contenedor terminó con error")
            elif last is not None and getattr(last, "reason", None) == "OOMKilled":
                consider(2, OOM_ISSUE)
            else:
                consider(7, "El pod corre pero no está listo (falla su readinessProbe)")

        if not pod_ready and getattr(status, "phase", None) == "Pending":
            for cond in getattr(status, "conditions", None) or []:
                if getattr(cond, "type", None) == "PodScheduled" and getattr(cond, "status", None) == "False":
                    if getattr(cond, "reason", None) == "Unschedulable":
                        consider(2, "No hay recursos para programar el pod: faltan CPU/memoria en los nodos")
                    else:
                        consider(4, "El pod está pendiente de programarse")
    return (best[1] if best else None), last_reason


def diagnose_workload_conditions(workload) -> Optional[str]:
    """Causa a nivel de Deployment"""
    for cond in getattr(getattr(workload, "status", None), "conditions", None) or []:
        if getattr(cond, "type", None) == "ReplicaFailure" and getattr(cond, "status", None) == "True":
            text = f"{getattr(cond, 'message', '') or ''} {getattr(cond, 'reason', '') or ''}".lower()
            if "quota" in text:
                return "Cuota del namespace agotada: Kubernetes no puede crear pods"
            return "Kubernetes no puede crear los pods (ReplicaFailure): revisa kubectl describe del workload"
    return None


class RestartError(Exception):
    def __init__(self, reason: str, message: str):
        super().__init__(message)
        self.reason = reason


class KubernetesManager:
    def __init__(self, namespace: Optional[str] = None):
        self.available = False
        self._apps = None
        self._core = None
        self.namespace = (
            namespace
            or os.getenv("SYSTEM_NAMESPACE")
            or self._namespace_from_pod()
            or "default"
        )
        self._load()

    @staticmethod
    def _namespace_from_pod() -> Optional[str]:
        try:
            with open(NAMESPACE_FILE, encoding="utf-8") as f:
                return f.read().strip() or None
        except OSError:
            return None

    def _load(self) -> None:
        try:
            from kubernetes import client, config
        except ImportError:
            logger.warning("Librería 'kubernetes' no instalada: sin datos de réplicas")
            return
        try:
            try:
                config.load_incluster_config() 
            except config.ConfigException:
                config.load_kube_config() 
        except Exception as exc: 
            logger.warning("Sin acceso a la API de Kubernetes (%s)", type(exc).__name__)
            return
        self._apps = client.AppsV1Api()
        self._core = client.CoreV1Api()
        self.available = True
        logger.info("API de Kubernetes disponible (namespace=%s)", self.namespace)

    def _read_workload(self, kind: str, name: str):
        if kind == "StatefulSet":
            return self._apps.read_namespaced_stateful_set(
                name, self.namespace, _request_timeout=REQUEST_TIMEOUT_SECONDS
            )
        return self._apps.read_namespaced_deployment(
            name, self.namespace, _request_timeout=REQUEST_TIMEOUT_SECONDS
        )

    def _analyze_pods(self, match_labels: dict):
        """Una sola consulta de pods: (restarts, pods Running con IP, causa probable, último motivo)."""
        if not match_labels:
            return None, (), None, None
        selector = ",".join(f"{k}={v}" for k, v in match_labels.items())
        try:
            pods = self._core.list_namespaced_pod(
                self.namespace,
                label_selector=selector,
                _request_timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except Exception as exc:
            logger.warning("No se pudieron listar los pods de '%s': %s", selector, exc)
            return None, (), None, None
        total = 0
        targets = []
        for pod in pods.items:
            for cs in pod.status.container_statuses or []:
                total += cs.restart_count or 0
            meta = getattr(pod, "metadata", None)
            terminating = getattr(meta, "deletion_timestamp", None) is not None
            phase = getattr(pod.status, "phase", None)
            ip = getattr(pod.status, "pod_ip", None)
            if phase == "Running" and ip and not terminating:
                targets.append(PodTarget(name=getattr(meta, "name", "") or "", ip=ip))
        try:
            issue, last_reason = diagnose_pods(pods.items)
        except Exception as exc:  # el diagnóstico nunca debe romper el estado
            logger.warning("No se pudo diagnosticar los pods de '%s': %s", selector, exc)
            issue, last_reason = None, None
        return total, tuple(targets), issue, last_reason

    def _inspect_pods(self, match_labels: dict) -> Tuple[Optional[int], Tuple[PodTarget, ...]]:
        restarts, targets, _issue, _last = self._analyze_pods(match_labels)
        return restarts, targets

    def _count_restarts(self, match_labels: dict) -> Optional[int]:
        return self._inspect_pods(match_labels)[0]

    def get_workload_status(self, name: str, kind: str = "Deployment") -> Optional[WorkloadInfo]:
        if not self.available:
            return None
        from kubernetes.client.rest import ApiException

        kinds = [kind] + [k for k in ("Deployment", "StatefulSet") if k != kind]
        for k in kinds:
            try:
                workload = self._read_workload(k, name)
            except ApiException as exc:
                if exc.status == 404:
                    continue
                logger.warning("No se pudo leer %s/%s (HTTP %s)", k, name, exc.status)
                return None
            except Exception as exc:
                logger.warning("Error leyendo %s/%s: %s", k, name, exc)
                return None
            desired = workload.spec.replicas if workload.spec.replicas is not None else 1
            ready = workload.status.ready_replicas or 0
            match_labels = (workload.spec.selector.match_labels or {}) if workload.spec.selector else {}
            restarts, pods, issue, last_reason = self._analyze_pods(match_labels)
            if ready < desired:  # la causa a nivel de workload (cuota) manda sobre la de los pods
                issue = diagnose_workload_conditions(workload) or issue
            else:
                issue = None
            return WorkloadInfo(desired=desired, ready=ready, restarts=restarts, pods=pods,
                                issue=issue, last_restart_reason=last_reason)
        logger.warning("Workload '%s' no encontrado en el namespace '%s'", name, self.namespace)
        return None

    def _patch_workload(self, kind: str, name: str, body: dict) -> None:
        patch = (
            self._apps.patch_namespaced_stateful_set
            if kind == "StatefulSet"
            else self._apps.patch_namespaced_deployment
        )
        response = patch(
            name, self.namespace, body,
            _request_timeout=REQUEST_TIMEOUT_SECONDS, _preload_content=False,
        )
        release = getattr(response, "release_conn", None)
        if release:
            release()

    def get_rollout_status(self, name: str) -> RolloutInfo:
        """Avance del reinicio: compara réplicas actualizadas/listas con las deseadas."""
        if name not in RESTARTABLE_WORKLOADS:
            raise RestartError("not_allowed", f"'{name}' no está autorizado")
        if not self.available:
            raise RestartError("unavailable", "Sin acceso a la API de Kubernetes")
        from kubernetes.client.rest import ApiException

        for k in ("Deployment", "StatefulSet"):
            try:
                w = self._read_workload(k, name)
            except ApiException as exc:
                if exc.status == 404:
                    continue
                raise RestartError("failed", f"La API de Kubernetes respondió HTTP {exc.status}") from None
            except Exception:
                raise RestartError("failed", "No se pudo contactar la API de Kubernetes") from None
            desired = w.spec.replicas if w.spec.replicas is not None else 1
            st = w.status
            updated = getattr(st, "updated_replicas", None) or 0
            ready = getattr(st, "ready_replicas", None) or 0
            total = getattr(st, "replicas", None) or 0
            available = getattr(st, "available_replicas", None) or 0
            generation = getattr(getattr(w, "metadata", None), "generation", None)
            observed = getattr(st, "observed_generation", None)
            seen = generation is None or observed is None or observed >= generation
            done = seen and updated >= desired and ready >= desired and total <= desired
            if done:
                return RolloutInfo("COMPLETE", desired, updated, ready, available,
                                   f"Reinicio completado: {ready}/{desired} réplicas listas")
            return RolloutInfo("IN_PROGRESS", desired, updated, ready, available,
                               f"Reiniciando: {updated}/{desired} actualizadas, {ready}/{desired} listas")
        raise RestartError("not_found", f"El workload '{name}' no existe en el namespace '{self.namespace}'")

    def restart_workload(self, name: str, kind: str = "Deployment") -> RestartOutcome:
        if name not in RESTARTABLE_WORKLOADS:
            logger.warning("Reinicio bloqueado por el tope de seguridad: '%s'", name)
            raise RestartError("not_allowed", f"'{name}' no está autorizado para reinicio")
        if not self.available:
            raise RestartError("unavailable", "Sin acceso a la API de Kubernetes")
        from kubernetes.client.rest import ApiException

        requested_at = datetime.now(timezone.utc).replace(microsecond=0)
        body = {
            "spec": {
                "template": {
                    "metadata": {
                        "annotations": {RESTART_ANNOTATION: requested_at.strftime("%Y-%m-%dT%H:%M:%SZ")}
                    }
                }
            }
        }
        kinds = [kind] + [k for k in ("Deployment", "StatefulSet") if k != kind]
        for k in kinds:
            try:
                self._patch_workload(k, name, body)
            except ApiException as exc:
                if exc.status == 404:
                    continue
                if exc.status == 403:
                    logger.warning("Sin permiso para parchar %s/%s (HTTP 403)", k, name)
                    raise RestartError("forbidden", "El ServiceAccount no tiene permiso patch") from None
                logger.warning("No se pudo parchar %s/%s (HTTP %s)", k, name, exc.status)
                raise RestartError("failed", f"La API de Kubernetes respondió HTTP {exc.status}") from None
            except Exception as exc:
                logger.warning("Error parchando %s/%s: %s: %s", k, name, type(exc).__name__, exc)
                raise RestartError("failed", "No se pudo contactar la API de Kubernetes") from None
            return RestartOutcome(kind=k, requested_at=requested_at)
        raise RestartError("not_found", f"El workload '{name}' no existe en el namespace '{self.namespace}'")
