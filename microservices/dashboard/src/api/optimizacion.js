// obtener las recomendaciones de optimizacion de la API y almacenarlas en el estado global de la aplicación.

import apiClient from './client';

// obtener recomendaciones de ahorro 

export const getRecomendacionesAhorro = async () => {
  try {
    const response = await apiClient.get('/optimizacion/recomendations');
    return response.data;
  } catch (error) {
    throw new Error(
      error.response?.data?.detail || 'Error al obtener las recomendaciones de ahorro'
    );
  }
};

//obtener pronostico de consumo (prophet)
export const getForecast = async () => {
  try {
    const response = await apiClient.get('/optimizacion/forecast');
    return response.data;
  } catch (error) {
    throw new Error(
      error.response?.data?.detail || 'Error al obtener el pronóstico'
    );
  }
};

// exportar reporte (csv o PDF)

export const exportarReporte = async (formato = 'csv') => {
  try {
    const response = await apiClient.get('/optimizacion/export', {
      params: { format: formato },
      responseType: 'blob',
    });
    return response.data;
  } catch (error) {
    throw new Error(
      error.response?.data?.detail || 'Error al exportar el reporte'
    );
  }
};