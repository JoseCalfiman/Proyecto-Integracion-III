import apiClient from './client';

// obtener el historial de mediciones
export const getHistorial = async (filtros = {}) => {
  try {
    const response = await apiClient.get('/historial', { params: filtros });
    return response.data;
  } catch (error) {
    throw new Error(
      error.response?.data?.detail || 'Error al obtener el historial'
    );
  }
};

// Exportar el historial (CSV o PDF)
export const exportarHistorial = async (formato = 'csv', filtros = {}) => {
  try {
    const response = await apiClient.get('/historial/export', {
      params: { format: formato, ...filtros },
      responseType: 'blob',
    });
    return response.data;
  } catch (error) {
    throw new Error(
      error.response?.data?.detail || 'Error al exportar el historial'
    );
  }
};