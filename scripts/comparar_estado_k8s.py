"""compara lo que muestra el panel (/control-api/status) con lo que corre Kubernetes.

python scripts/comparar_estado_k8s.py --url https://TU-DASHBOARD/control-api/status \
    --namespace student-aamonsalve

Sale con código 0 si todo coincide y 1 si hay diferencias.
"""
import argparse
import json
import subprocess
import sys
import urllib.request


def cargar_json(origen, archivo, url):
    if archivo:
        with open(archivo, encoding="utf-8") as f:
            return json.load(f)
    with urllib.request.urlopen(url, timeout=10) as r:  
        return json.load(r)


def workloads_de_kubectl(ns):
    salida = subprocess.run(
        ["kubectl", "get", "deploy,sts", "-n", ns, "-o", "json"],
        check=True, capture_output=True, text=True,
    ).stdout
    return json.loads(salida)


def pods_de_kubectl(ns):
    salida = subprocess.run(
        ["kubectl", "get", "pods", "-n", ns, "-o", "json"],
        check=True, capture_output=True, text=True,
    ).stdout
    return json.loads(salida)


def resumir_k8s(workloads, pods=None):
    out = {}
    for w in workloads.get("items", []):
        nombre = w["metadata"]["name"]
        desired = w.get("spec", {}).get("replicas", 1)
        ready = w.get("status", {}).get("readyReplicas", 0) or 0
        restarts = None
        if pods is not None:
            etiquetas = w.get("spec", {}).get("selector", {}).get("matchLabels", {})
            total = 0
            for p in pods.get("items", []):
                if p.get("status", {}).get("phase") == "Failed":
                    continue
                if all(p["metadata"].get("labels", {}).get(k) == v for k, v in etiquetas.items()):
                    total += sum(c.get("restartCount", 0) for c in p.get("status", {}).get("containerStatuses", []) or [])
            restarts = total
        out[nombre] = (desired, ready, restarts)
    return out


def comparar(panel, k8s):
    filas, hay_diferencias = [], False
    panel_por_nombre = {c["name"]: c for c in panel["components"]}
    for nombre in sorted(set(panel_por_nombre) | set(k8s)):
        c, k = panel_por_nombre.get(nombre), k8s.get(nombre)
        if c is None:
            filas.append((nombre, "SOLO EN KUBERNETES", "el panel no lo muestra")); hay_diferencias = True; continue
        if k is None:
            filas.append((nombre, "SOLO EN EL PANEL", "no existe como Deployment/StatefulSet")); hay_diferencias = True; continue
        reps = c.get("replicas")
        problemas = []
        if reps is None:
            problemas.append("el panel no trae réplicas")
        elif (reps["desired"], reps["ready"]) != (k[0], k[1]):
            problemas.append(f"réplicas panel {reps['ready']}/{reps['desired']} vs kubectl {k[1]}/{k[0]}")
        if k[2] is not None and c.get("restarts") != k[2]:
            problemas.append(f"reinicios panel {c.get('restarts')} vs kubectl {k[2]}")
        if problemas:
            hay_diferencias = True
        filas.append((nombre, "DIFERENTE" if problemas else "OK", "; ".join(problemas) or f"{k[1]}/{k[0]} listas, {c['status']}"))
    return filas, hay_diferencias


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default="http://localhost:8002/api/v1/system/status")
    ap.add_argument("--namespace", default="student-aamonsalve")
    ap.add_argument("--status-file")
    ap.add_argument("--k8s-file")
    ap.add_argument("--pods-file")
    a = ap.parse_args()

    panel = cargar_json("panel", a.status_file, a.url)
    if a.k8s_file:
        with open(a.k8s_file, encoding="utf-8") as f:
            workloads = json.load(f)
        pods = None
        if a.pods_file:
            with open(a.pods_file, encoding="utf-8") as f:
                pods = json.load(f)
    else:
        workloads, pods = workloads_de_kubectl(a.namespace), pods_de_kubectl(a.namespace)

    filas, hay_diferencias = comparar(panel, resumir_k8s(workloads, pods))
    ancho = max(len(f[0]) for f in filas)
    for nombre, estado, detalle in filas:
        print(f"{nombre.ljust(ancho)}  {estado.ljust(18)}  {detalle}")
    print("\nRESULTADO:", "HAY DIFERENCIAS" if hay_diferencias else "el panel coincide con Kubernetes")
    return 1 if hay_diferencias else 0


if __name__ == "__main__":
    sys.exit(main())
