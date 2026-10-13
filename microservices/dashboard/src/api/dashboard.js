import apiClient from "./client";

const msg = (error, fallback) => error.response?.data?.detail || fallback;

// ============================================================
// DATOS EN VIVO DEL DASHBOARD
// ============================================================
export const getDashboardLive = async () => {
  try {
    const { data } = await apiClient.get("/dashboard/live");
    return data;
  } catch (error) {
    throw new Error(msg(error, "Error al obtener datos del dashboard"));
  }
};

// ============================================================
// GRÁFICO DE TEMPERATURA
// ============================================================
export const pivotTemperature = (rows) => {
  const series = [];
  const byTime = new Map();
  for (const r of rows) {
    const name = r.chamber_name || r.id_chamber;
    if (!series.includes(name)) series.push(name);
    const key = r.timestamp;
    if (!byTime.has(key)) {
      byTime.set(key, {
        time: new Date(key).toLocaleTimeString("es-CL", {
          hour: "2-digit",
          minute: "2-digit",
          hour12: false,
        }),
      });
    }
    byTime.get(key)[name] = Math.round(r.temperature * 10) / 10;
  }
  return { data: [...byTime.values()], series };
};

export const getTemperatureSeries = async (minutes = 120) => {
  try {
    const { data } = await apiClient.get("/dashboard/temperature", {
      params: { minutes },
    });
    return pivotTemperature(data);
  } catch (error) {
    throw new Error(msg(error, "Error al obtener la serie de temperatura"));
  }
};

// ============================================================
// GRÁFICO DE CONSUMO
// ============================================================
export const mapConsumption = (rows) =>
  rows.map((r) => {
    const [y, m, d] = r.day.split("-").map(Number);
    const label = new Date(y, m - 1, d)
      .toLocaleDateString("es-CL", { weekday: "short" })
      .replace(".", "");
    return { day: label.charAt(0).toUpperCase() + label.slice(1), kwh: r.kwh };
  });

export const getConsumptionSeries = async (days = 7) => {
  try {
    const { data } = await apiClient.get("/dashboard/consumption", {
      params: { days },
    });
    return mapConsumption(data);
  } catch (error) {
    throw new Error(msg(error, "Error al obtener la serie de consumo"));
  }
};
