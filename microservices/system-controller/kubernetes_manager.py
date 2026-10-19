import logging
import os
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger("system-controller")

NAMESPACE_FILE = "/var/run/secrets/kubernetes.io/serviceaccount/namespace"
REQUEST_TIMEOUT_SECONDS = 3


@dataclass(frozen=True)
class WorkloadInfo:
    desired: int
    ready: int
    restarts: Optional[int]  


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

    def _count_restarts(self, match_labels: dict) -> Optional[int]:
        if not match_labels:
            return None
        selector = ",".join(f"{k}={v}" for k, v in match_labels.items())
        try:
            pods = self._core.list_namespaced_pod(
                self.namespace,
                label_selector=selector,
                _request_timeout=REQUEST_TIMEOUT_SECONDS,
            )
        except Exception as exc:
            logger.warning("No se pudieron listar los pods de '%s': %s", selector, exc)
            return None
        total = 0
        for pod in pods.items:
            for cs in pod.status.container_statuses or []:
                total += cs.restart_count or 0
        return total

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
            return WorkloadInfo(desired=desired, ready=ready, restarts=self._count_restarts(match_labels))
        logger.warning("Workload '%s' no encontrado en el namespace '%s'", name, self.namespace)
        return None
