// Cliente de cámaras: CRUD sobre /api/v1/camaras (gestión solo Gerente).

import apiClient from './client';

// listar las camaras
// permisos: tecnico, gerente
export const getCamaras = async () => {
  try {
    const response = await apiClient.get('/camaras');
    return response.data;
  } catch (error) {
    throw new Error(
      error.response?.data?.detail || 'Error al obtener las cámaras'
    );
  }
};

// obtener una camara por ID
// permisos: tecnico, gerente
export const getCamara = async (id) => {
  try {
    const response = await apiClient.get(`/camaras/${id}`);
    return response.data;
  } catch (error) {
    throw new Error(
      error.response?.data?.detail || 'Error al obtener la cámara'
    );
  }
};

// crear camara
// solo gerente
export const crearCamara = async (data) => {
  try {
    const response = await apiClient.post('/camaras', data);
    return response.data;
  } catch (error) {
    throw new Error(
      error.response?.data?.detail || 'Error al crear la cámara'
    );
  }
};

// actualizar camara
// solo gerente
export const actualizarCamara = async (id, data) => {
  try {
    const response = await apiClient.put(`/camaras/${id}`, data);
    return response.data;
  } catch (error) {
    throw new Error(
      error.response?.data?.detail || 'Error al actualizar la cámara'
    );
  }
};

// eliminar camara
// solo gerente
export const eliminarCamara = async (id) => {
  try {
    const response = await apiClient.delete(`/camaras/${id}`);
    return response.data;
  } catch (error) {
    throw new Error(
      error.response?.data?.detail || 'Error al eliminar la cámara'
    );
  }
};
