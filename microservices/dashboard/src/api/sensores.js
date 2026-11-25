import apiClient from './client';
export const listarSensores = async (id, after_id = 0) => (await apiClient.get(`/chambers/${id}/sensors`, { params: { after_id } })).data;
export const guardarSensor = async (id, sensor, values) => (await (sensor ? apiClient.put(`/chambers/${id}/sensors/${sensor}`, values) : apiClient.post(`/chambers/${id}/sensors`, values))).data;
export const diagnosticarSensor = async (id, sensor) => (await apiClient.get(`/chambers/${id}/sensors/${sensor}/diagnostics`)).data;
export const detalleError = (e) => typeof e.response?.data?.detail === 'string' ? e.response.data.detail : e.response?.status === 422 ? 'Revisa los campos requeridos y su formato.' : e.message || 'No se pudo completar la solicitud.';