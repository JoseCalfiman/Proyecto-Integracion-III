// Cliente del Panel Técnico.
// Todas las llamadas requieren rol "tecnico" (validado en el backend con JWT).

import apiClient from './client';

// ============================================================
// ESTADO DE GATEWAYS (cámaras + MCUs)
// Tabla: chambers + sensors
// ============================================================
export const getGateways = async () => {
  try {
    const response = await apiClient.get('/panel/gateways');
    return response.data;
  } catch (error) {
    throw new Error(
      error.response?.data?.detail || 'Error al obtener el estado de los gateways'
    );
  }
};

// ============================================================
// ALERTAS DEL SISTEMA
// Tabla: generated_alerts
// ============================================================
export const getAlertasSistema = async () => {
  try {
    const response = await apiClient.get('/panel/alertas');
    return response.data;
  } catch (error) {
    throw new Error(
      error.response?.data?.detail || 'Error al obtener las alertas del sistema'
    );
  }
};

// ============================================================
// TRÁFICO DE RED (últimas 6 horas)
// Tabla: sensor_data (agregación)
// ============================================================
export const getTraficoRed = async () => {
  try {
    const response = await apiClient.get('/panel/trafico');
    return response.data;
  } catch (error) {
    throw new Error(
      error.response?.data?.detail || 'Error al obtener el tráfico de red'
    );
  }
};

// ============================================================
// INVENTARIO DE SENSORES
// Tabla: sensors
// ============================================================
export const getSensores = async () => {
  try {
    const response = await apiClient.get('/panel/sensores');
    return response.data;
  } catch (error) {
    throw new Error(
      error.response?.data?.detail || 'Error al obtener el inventario de sensores'
    );
  }
};

// ============================================================
// CALIBRAR SENSOR
// Tabla: sensors (UPDATE)
// ============================================================
export const calibrarSensor = async (sensorId) => {
  try {
    const response = await apiClient.put(`/panel/calibrar/${sensorId}`);
    return response.data;
  } catch (error) {
    throw new Error(
      error.response?.data?.detail || 'Error al calibrar el sensor'
    );
  }
};

// ============================================================
// VERIFICAR SALUD DE MICROSERVICIOS
// Endpoint: /health de cada servicio
// ============================================================
export const verificarSalud = async () => {
  try {
    const response = await apiClient.get('/panel/health');
    return response.data;
  } catch (error) {
    throw new Error(
      error.response?.data?.detail || 'Error al verificar la salud del sistema'
    );
  }
};