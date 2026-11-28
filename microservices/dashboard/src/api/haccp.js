// Cliente HACCP -> backend /api/v1/haccp/rules (routes/haccp.py)
import apiClient from './client';
import { reglaFromApi, reglaToApi } from './adapters';

// FastAPI devuelve `detail` como string (404/403) o como lista de objetos con .msg (422).
const msg = (error, fallback) => {
  const detail = error.response?.data?.detail;
  if (typeof detail === 'string' && detail) return detail;
  if (Array.isArray(detail)) {
    const text = detail.map((item) => item?.msg).filter(Boolean).join('; ');
    if (text) return text;
  }
  return error.response ? fallback : (error.message || fallback);
};

export const getReglasHaccp = async () => {
  try {
    const { data } = await apiClient.get('/haccp/rules');
    return data.map(reglaFromApi);
  } catch (error) {
    throw new Error(msg(error, 'Error al obtener las reglas HACCP'));
  }
};

export const getReglasPorCamara = async (camaraId) => {
  try {
    const { data } = await apiClient.get(`/haccp/rules/${camaraId}`);
    return reglaFromApi(data);
  } catch (error) {
    throw new Error(msg(error, 'Error al obtener las reglas de la cámara'));
  }
};

export const actualizarReglasPorCamara = async (camaraId, form) => {
  const body = reglaToApi(form);
  try {
    const { data } = await apiClient.put(`/haccp/rules/${camaraId}`, body);
    return reglaFromApi(data);
  } catch (error) {
    throw new Error(msg(error, 'Error al actualizar las reglas de la cámara'));
  }
};
