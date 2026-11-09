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


@dataclass(frozen=True)
class RestartOutcome:
    kind: str 
    requested_at: datetime  

@dataclass(frozen=True)
class RolloutInfo:
    phase: str  
    desired: int
    updated: int
    ready: int
    available: int
    message: str


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

    def _inspect_pods(self, match_labels: dict) -> Tuple[Optional[int], Tuple[PodTarget, ...]]:
        """Una sola consulta de pods: suma de restarts y pods Running con IP (para medir latencia)."""
        if not match_labels:
            return None, ()
        selector = ",".join(f"{k}={v}" for k, v in match_labels.items())
        try:
            pods = self._core.list_namespaced_pod(
                self.namespace,
                label_selector=selector,
                _request_timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except Exception as exc:
            logger.warning("No se pudieron listar los pods de '%s': %s", selector, exc)
            return None, ()
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
        return total, tuple(targets)

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
            restarts, pods = self._inspect_pods(match_labels)
            return WorkloadInfo(desired=desired, ready=ready, restarts=restarts, pods=pods)
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
