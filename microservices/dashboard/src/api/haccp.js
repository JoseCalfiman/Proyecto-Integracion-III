// Cliente HACCP -> backend /api/v1/haccp/rules (routes/haccp.py)
import apiClient from './client';
import { reglaFromApi, reglaToApi } from './adapters';

const msg = (error, fallback) => error.response?.data?.detail || fallback;

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
  try {
    const { data } = await apiClient.put(`/haccp/rules/${camaraId}`, reglaToApi(form));
    return reglaFromApi(data);
  } catch (error) {
    throw new Error(msg(error, 'Error al actualizar las reglas de la cámara'));
  }
};
