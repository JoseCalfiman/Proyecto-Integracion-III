import apiClient from './client';

export const listarAlertasTecnicas = async (params) =>
  (await apiClient.get('/alerts', { params })).data;

export const obtenerAlerta = async (id) =>
  (await apiClient.get(`/alerts/${id}`)).data;

export const asumirAlerta = async (id) =>
  (await apiClient.put(`/alerts/${id}/acknowledge`, {})).data;

export const cerrarAlerta = async (id, values) =>
  (await apiClient.put(`/alerts/${id}/resolve`, values)).data;

export const obtenerAuditoria = async (id) =>
  (await apiClient.get(`/alerts/${id}/audit`)).data;

export const obtenerTecnicos = async () =>
  (await apiClient.get('/alerts/manager/technicians')).data;

export const descargarReporte = async (params) => {
  // Filtra parámetros vacíos / nulos / indefinidos
  const filtered = Object.fromEntries(
    Object.entries(params).filter(
      ([, v]) => v !== '' && v !== null && v !== undefined
    )
  );

  try {
    const { data } = await apiClient.get('/alerts/manager/report', {
      params: filtered,
      responseType: 'blob',
    });

    const url = URL.createObjectURL(data);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'intervenciones-haccp.csv';
    a.click();

    setTimeout(() => URL.revokeObjectURL(url), 1000);
  } catch (e) {
    // Si el error trae un Blob, intenta extraer el `detail` del JSON
    if (e.response?.data instanceof Blob) {
      try {
        const body = JSON.parse(await e.response.data.text());
        if (typeof body.detail === 'string') throw new Error(body.detail);
      } catch (err) {
        if (!(err instanceof SyntaxError)) throw err;
      }
    }
    throw e;
  }
};