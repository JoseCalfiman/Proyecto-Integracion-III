// A2 (provisional hasta D5): análisis gerencial usando endpoints YA existentes.
// El endpoint /stats/summary del backlog no está implementado en feature/dashboard.
import apiClient from "./client";

const MAX_ALERTAS = 200; // Límite permitido por GET /alerts. No descarga el historial completo.

export const getAlertasParaEstadisticas = async ({ signal } = {}) => {
  const { data } = await apiClient.get("/alerts", {
    params: { limit: MAX_ALERTAS, offset: 0 },
    signal,
  });
  if (!Array.isArray(data)) {
    throw new Error("El servidor no entregó una lista de alertas válida.");
  }
  return {
    alertas: data,
    // Si recibimos 200, NO podemos afirmar que está completo el historial.
    muestraLimitada: data.length >= MAX_ALERTAS,
    totalConsultadas: data.length,
  };
};