// Cliente de usuarios: CRUD sobre /api/v1/usuarios (solo Gerente).

import apiClient from './client';

export const getUsuarios = async () => {
  try {
    const response = await apiClient.get('/usuarios');
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Error al obtener los usuarios');
  }
};

export const crearUsuario = async (data) => {
  try {
    const response = await apiClient.post('/usuarios', data);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Error al crear el usuario');
  }
};

export const actualizarUsuario = async (id, data) => {
  try {
    const response = await apiClient.put(`/usuarios/${id}`, data);
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Error al actualizar el usuario');
  }
};

// "Eliminar" un usuario en realidad lo desactiva (no se borra el registro).
export const desactivarUsuario = async (id, activo = false) => {
  try {
    const response = await apiClient.put(`/usuarios/${id}`, { activo });
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Error al actualizar el estado del usuario');
  }
};
