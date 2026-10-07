import apiClient from './client';

// ============================================================
// DATOS EN VIVO DEL DASHBOARD
// ============================================================
export const getDashboardLive = async () => {
  try {
    const response = await apiClient.get('/dashboard/live');
    return response.data;
  } catch (error) {
    throw new Error(
      error.response?.data?.detail || 'Error al obtener datos del dashboard'
    );
  }
};

// ============================================================
// CÁMARAS (usa el endpoint de Diego: /chambers)
// ============================================================
export const getCamaras = async () => {
  try {
    const response = await apiClient.get('/chambers');
    return response.data;
  } catch (error) {
    throw new Error(
      error.response?.data?.detail || 'Error al obtener las cámaras'
    );
  }
};

// ============================================================
// ALERTAS
// ============================================================
export const getAlertas = async () => {
  try {
    const response = await apiClient.get('/alertas');
    return response.data;
  } catch (error) {
    throw new Error(
      error.response?.data?.detail || 'Error al obtener las alertas'
    );
  }
};