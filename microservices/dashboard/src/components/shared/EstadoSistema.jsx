import React, { useState, useEffect } from "react";
import { Activity, RefreshCw, RotateCcw, AlertTriangle } from "lucide-react";
import Badge from "../ui/Badge";
import Modal from "../ui/Modal";
import { usePolling } from "../../hooks/usePolling";
import { getSystemStatus, restartComponent } from "../../api/systemStatus";

const POLL_NORMAL_MS = 5000;
const POLL_FAST_MS = 2000;
const FAST_WINDOW_MS = 60000;

const STATUS = {
  ONLINE: { color: "green", label: "Online", dot: "bg-green-500" },
  DEGRADED: { color: "yellow", label: "Degraded", dot: "bg-yellow-500" },
  OFFLINE: { color: "red", label: "Offline", dot: "bg-red-500" },
};
const statusOf = (s) =>
  STATUS[s] || { color: "gray", label: s || "—", dot: "bg-gray-400" };

const EstadoSistema = () => {
  const [fastUntil, setFastUntil] = useState(0);
  const [fast, setFast] = useState(false);
  const interval = fast ? POLL_FAST_MS : POLL_NORMAL_MS;
  const { data, error, loading, refresh } = usePolling(
    getSystemStatus,
    interval,
  );

  const [target, setTarget] = useState(null);
  const [restarting, setRestarting] = useState({});
  const [feedback, setFeedback] = useState(null);

  useEffect(() => {
    if (!fastUntil) return undefined;
    const t = setTimeout(
      () => setFast(false),
      Math.max(0, fastUntil - Date.now()),
    );
    return () => clearTimeout(t);
  }, [fastUntil]);

  const confirmRestart = async () => {
    const name = target.name;
    setTarget(null);
    setRestarting((r) => ({ ...r, [name]: true }));
    try {
      await restartComponent(name);
      setFeedback({
        type: "ok",
        text: `Reinicio de "${name}" solicitado. Observa cómo vuelve a ONLINE.`,
      });
      setFast(true);
      setFastUntil(Date.now() + FAST_WINDOW_MS);
      refresh();
      // El marcador "Reiniciando…"(15 s).
      setTimeout(() => setRestarting((r) => ({ ...r, [name]: false })), 15000);
    } catch (e) {
      setFeedback({
        type: "error",
        text: `No se pudo reiniciar "${name}": ${e.message}`,
      });
      setRestarting((r) => ({ ...r, [name]: false }));
    }
  };

  const components = data?.components || [];
  const summary = data?.summary;
  const global = statusOf(data?.status);

  return (
    <section
      className="bg-white rounded-lg border border-gray-200 shadow-sm mb-6"
      data-testid="estado-sistema"
    >
      <div className="flex flex-wrap items-center justify-between gap-3 px-6 py-4 border-b border-gray-100">
        <div className="flex items-center gap-3">
          <Activity size={20} className="text-blue-600" />
          <h2 className="text-lg font-semibold text-gray-800">
            Estado del Sistema
          </h2>
          {data && <Badge color={global.color}>{global.label}</Badge>}
        </div>
        <div className="flex items-center gap-4 text-sm text-gray-500">
          {summary && (
            <span data-testid="resumen">
              {summary.online} online · {summary.degraded} degraded ·{" "}
              {summary.offline} offline
            </span>
          )}
          <button
            onClick={refresh}
            className="flex items-center gap-1 text-gray-500 hover:text-gray-800"
            title="Actualizar ahora"
          >
            <RefreshCw size={14} /> Actualizar
          </button>
        </div>
      </div>

      {error && (
        <div
          className="flex items-start gap-2 mx-6 mt-4 p-3 rounded-md bg-red-50 text-red-700 text-sm"
          role="alert"
        >
          <AlertTriangle size={16} className="mt-0.5 shrink-0" />
          <span>
            {data ? "Datos desactualizados. " : ""}
            {error.message}
          </span>
        </div>
      )}

      {feedback && (
        <div
          className={`flex items-start justify-between gap-2 mx-6 mt-4 p-3 rounded-md text-sm ${
            feedback.type === "ok"
              ? "bg-green-50 text-green-700"
              : "bg-red-50 text-red-700"
          }`}
          role="status"
        >
          <span>{feedback.text}</span>
          <button
            onClick={() => setFeedback(null)}
            className="underline shrink-0"
          >
            Cerrar
          </button>
        </div>
      )}

      <div className="p-6 overflow-x-auto">
        {loading && !data ? (
          <p className="text-sm text-gray-500">Consultando estado…</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase text-gray-500 border-b border-gray-100">
                <th className="py-2 pr-4 font-medium">Componente</th>
                <th className="py-2 pr-4 font-medium">Estado</th>
                <th className="py-2 pr-4 font-medium">Latencia</th>
                <th className="py-2 pr-4 font-medium">Réplicas</th>
                <th className="py-2 pr-4 font-medium">Restarts</th>
                <th className="py-2 pr-4 font-medium">Detalle</th>
                <th className="py-2 font-medium text-right">Acción</th>
              </tr>
            </thead>
            <tbody>
              {components.map((c) => {
                const st = statusOf(c.status);
                const busy = !!restarting[c.name];
                return (
                  <tr
                    key={c.name}
                    className="border-b border-gray-50"
                    data-testid={`comp-${c.name}`}
                  >
                    <td className="py-3 pr-4 font-medium text-gray-800">
                      <span
                        className={`inline-block w-2 h-2 rounded-full mr-2 ${st.dot}`}
                      />
                      {c.name}
                    </td>
                    <td className="py-3 pr-4">
                      <Badge color={st.color}>{st.label}</Badge>
                    </td>
                    <td className="py-3 pr-4 text-gray-600">
                      {c.latency_ms != null
                        ? `${Math.round(c.latency_ms)} ms`
                        : "—"}
                    </td>
                    <td className="py-3 pr-4 text-gray-600">
                      {c.replicas
                        ? `${c.replicas.ready ?? 0}/${c.replicas.desired ?? 0}`
                        : "—"}
                    </td>
                    <td className="py-3 pr-4 text-gray-600">
                      {c.restarts ?? "—"}
                    </td>
                    <td
                      className="py-3 pr-4 text-gray-500 max-w-xs truncate"
                      title={c.detail || ""}
                    >
                      {c.detail || "—"}
                    </td>
                    <td className="py-3 text-right">
                      {c.restartable ? (
                        <button
                          disabled={busy}
                          onClick={() => setTarget(c)}
                          className="inline-flex items-center gap-1 px-3 py-1.5 rounded-md border border-gray-300 text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          <RotateCcw
                            size={14}
                            className={busy ? "animate-spin" : ""}
                          />
                          {busy ? "Reiniciando…" : "Reiniciar"}
                        </button>
                      ) : (
                        <span className="text-gray-300">—</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
        {data?.checked_at && (
          <p className="mt-3 text-xs text-gray-400">
            Última verificación:{" "}
            {new Date(data.checked_at).toLocaleTimeString()} · se actualiza cada{" "}
            {interval / 1000} s
          </p>
        )}
      </div>

      <Modal
        isOpen={!!target}
        onClose={() => setTarget(null)}
        title="Reiniciar componente"
      >
        <p className="text-sm text-gray-600 mb-6">
          ¿Reiniciar <strong>{target?.name}</strong>? Kubernetes recreará sus
          pods de forma gradual. Puede haber una breve interrupción del
          servicio.
        </p>
        <div className="flex justify-end gap-3">
          <button
            onClick={() => setTarget(null)}
            className="px-4 py-2 rounded-md border border-gray-300 text-gray-700"
          >
            Cancelar
          </button>
          <button
            onClick={confirmRestart}
            className="px-4 py-2 rounded-md bg-red-600 text-white hover:bg-red-700"
          >
            Reiniciar
          </button>
        </div>
      </Modal>
    </section>
  );
};

export default EstadoSistema;
