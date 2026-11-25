import apiClient from './client';

export async function getResumenAlertas(signal) {
  const { data } = await apiClient.get('/alerts/manager/summary', { signal });
  return data;
}

export async function getHistorialAlertas(filtros, cursor, signal) {
  const params = { ...filtros, ...cursor };
  Object.keys(params).forEach((key) => { if (!params[key]) delete params[key]; });
  const { data } = await apiClient.get('/alerts/manager/history', { params, signal });
  return data;
}

export const errorAlertas = (error) => {
  const detail = error.response?.data?.detail;
  return typeof detail === 'string' ? detail : 'No se pudo consultar Ingesta. Intenta nuevamente.';
};