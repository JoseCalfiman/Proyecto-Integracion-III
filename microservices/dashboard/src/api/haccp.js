// realizar peticiones a la API para obtener los datos de HACCP y almacenarlos en el estado global de la aplicación.

import apiClient from './client';

// listar reglas haccp
export const getReglasHaccp = async () => {
  try {
    const response = await apiClient.get('/haccp/reglas');
    return response.data;
  } catch (error) {
    throw new Error(
      error.response?.data?.detail || 'Error al obtener las reglas HACCP'
    );
  }
};

// obtener reglas haccp de una camara
export const getReglasPorCamara = async (camaraId) => {
  try {
    const response = await apiClient.get(`/haccp/rules/${camaraId}`);
    return response.data;
  } catch (error) {
    throw new Error(
      error.response?.data?.detail || 'Error al obtener las reglas de la cámara'
    );
  }
};

// actualizar reglas haccp de una camara
export const actualizarReglasPorCamara = async (camaraId, data) => {
  try {
    const response = await apiClient.put(`/haccp/rules/${camaraId}`, data);
    return response.data;
  } catch (error) {
    throw new Error(
      error.response?.data?.detail || 'Error al actualizar las reglas de la cámara'
    );
  }
};
