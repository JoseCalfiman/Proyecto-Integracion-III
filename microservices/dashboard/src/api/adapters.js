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
  estado: c.active ? "en_linea" : "offline",
});

export const camaraToApi = (form) => ({
  name: form.nombre,
  location: form.ubicacion || null,
});

// ---------- HACCP ----------
const SEV_HACCP_FRONT = {
  critical: "critico",
  high: "critico",
  medium: "medio",
  low: "bajo",
};
const SEV_HACCP_BACK = { critico: "critical", medio: "medium", bajo: "low" };

export const reglaFromApi = (r) => ({
  camara_id: r.id_chamber,
  camara: r.chamber_name,
  temp_max: Number(r.max_absolute_temp),
  temp_min: Number(r.min_absolute_temp),
  tiempo_tolerancia: r.tolerance_time_min,
  severidad: SEV_HACCP_FRONT[r.severity] || "medio",
  activa: r.active,
});

export const reglaToApi = (form) => ({
  max_absolute_temp: form.temp_max,
  min_absolute_temp: form.temp_min,
  tolerance_time_min: form.tiempo_tolerancia,
  severity: SEV_HACCP_BACK[form.severidad] || "medium",
  active: form.activa,
});
