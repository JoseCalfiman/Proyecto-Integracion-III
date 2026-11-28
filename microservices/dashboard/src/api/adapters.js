// Traduce entre el formato del backend (inglés, FastAPI) y el que esperan las vistas (español).

// ---------- Alertas ----------
const SEVERIDAD_FRONT = {
  critical: "critica",
  high: "critica",
  medium: "advertencia",
  low: "baja",
};
const ESTADO_FRONT = {
  active: "activa",
  acknowledged: "reconocida",
  resolved: "resuelta",
};
export const SEVERIDAD_BACK = {
  critica: "critical",
  advertencia: "medium",
  baja: "low",
};
export const ESTADO_BACK = {
  activa: "active",
  reconocida: "acknowledged",
  resuelta: "resolved",
};

export const alertaFromApi = (a) => ({
  id: `ALT-${a.id_alert}`,
  id_alert: a.id_alert,
  camara: a.chamber_name || "Sin cámara",
  mensaje: a.message || a.alert_type || "",
  temperatura: null,
  severidad: SEVERIDAD_FRONT[a.severity] || "baja",
  estado: ESTADO_FRONT[a.status] || a.status,
  timestamp: a.generation_date,
  auditoria: null,
});

// ---------- Cámaras ----------
export const camaraFromApi = (c) => ({
  id: c.id_chamber,
  nombre: c.name,
  ubicacion: c.location,
  sensor_id: "—",
  mcu_id: "—",
  setpoint: "—",
  active: c.active === true,
  estado: c.active ? "en_linea" : "offline",
});

export const camaraToApi = (form) => ({
  name: form.nombre,
  location: form.ubicacion || null,
  ...(typeof form.active === "boolean" ? { active: form.active } : {}),
});

// ---------- HACCP ----------
// Mapeo uno a uno con los 4 niveles del backend.
const SEV_HACCP_FRONT = {
  low: "bajo",
  medium: "medio",
  high: "alto",
  critical: "critico",
};
const SEV_HACCP_BACK = { bajo: "low", medio: "medium", alto: "high", critico: "critical" };

export const SEVERIDADES_HACCP = Object.keys(SEV_HACCP_BACK);

// Si el backend envía una severidad desconocida, `severidad` queda en null y
// `severidad_api` conserva el valor recibido para mostrarlo como inválido.
export const reglaFromApi = (r) => ({
  camara_id: r.id_chamber,
  camara: r.chamber_name,
  id_rule: r.id_rule ?? null,
  has_rule: r.has_rule !== false,
  temp_max: Number(r.max_absolute_temp),
  temp_min: Number(r.min_absolute_temp),
  tiempo_tolerancia: r.tolerance_time_min,
  severidad: SEV_HACCP_FRONT[r.severity] ?? null,
  severidad_api: r.severity ?? null,
  activa: Boolean(r.active),
  review_date: r.review_date ?? null,
  modified_by_name: r.modified_by_name ?? null,
});

export const reglaToApi = (form) => {
  const severity = SEV_HACCP_BACK[form.severidad];
  if (!severity) throw new Error("Selecciona un nivel de severidad válido");
  return {
    max_absolute_temp: form.temp_max,
    min_absolute_temp: form.temp_min,
    tolerance_time_min: form.tiempo_tolerancia,
    severity,
    active: form.activa,
  };
};