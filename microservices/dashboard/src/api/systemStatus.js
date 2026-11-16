import axios from "axios";

const controlClient = axios.create({
  baseURL: import.meta.env?.VITE_CONTROL_API_URL || "/control-api",
  timeout: 8000,
});

const toError = (err) => {
  const status = err.response?.status ?? null;
  const detail = err.response?.data?.detail;
  const message =
    (typeof detail === "string" && detail) ||
    (status
      ? `Error ${status} del System Controller`
      : "No se pudo contactar al System Controller");
  return Object.assign(new Error(message), { status });
};

const VALID_STATUS = ["ONLINE", "DEGRADED", "OFFLINE"];

const toNumberOrNull = (v) =>
  typeof v === "number" && Number.isFinite(v) ? v : null;

// Deja la respuesta del Controller con una forma segura para el panel.
// - Si no es un /status válido (p. ej. el gateway devolvió index.html con 200) falla
//   con un error claro, en vez de mostrar un panel vacío.
export const normalizeSystemStatus = (raw) => {
  if (!raw || typeof raw !== "object" || !Array.isArray(raw.components)) {
    throw Object.assign(
      new Error("Respuesta inválida del System Controller (no es /status)"),
      { status: null },
    );
  }
  const seen = new Set();
  const components = [];
  for (const c of raw.components) {
    const name = typeof c?.name === "string" ? c.name.trim().toLowerCase() : "";
    if (!name || seen.has(name)) continue;
    seen.add(name);
    const status = VALID_STATUS.includes(c.status) ? c.status : "UNKNOWN";
    components.push({
      name,
      type: typeof c.type === "string" ? c.type : "unknown",
      status,
      latency_ms: toNumberOrNull(c.latency_ms),
      detail:
        typeof c.detail === "string" && c.detail
          ? c.detail
          : status === "UNKNOWN"
            ? "Estado no reconocido por el panel"
            : "",
      last_check: c.last_check ?? null,
      replicas: c.replicas
        ? {
            desired: toNumberOrNull(c.replicas.desired) ?? 0,
            ready: toNumberOrNull(c.replicas.ready) ?? 0,
          }
        : null,
      restarts: toNumberOrNull(c.restarts),
      restartable: c.restartable === true,
    });
  }
  return { ...raw, components };
};

export const getSystemStatus = async () => {
  let data;
  try {
    ({ data } = await controlClient.get("/status"));
  } catch (err) {
    throw toError(err);
  }
  return normalizeSystemStatus(data);
};

// Avance de un reinicio: { phase: "IN_PROGRESS" | "COMPLETE", ready, desired, message, ... }
export const getRollout = async (name) => {
  try {
    const { data } = await controlClient.get(
      `/components/${encodeURIComponent(name)}/rollout`,
    );
    return data;
  } catch (err) {
    throw toError(err);
  }
};

export const restartComponent = async (name) => {
  try {
    const { data } = await controlClient.post(
      `/components/${encodeURIComponent(name)}/restart`,
    );
    return data;
  } catch (err) {
    throw toError(err);
  }
};
