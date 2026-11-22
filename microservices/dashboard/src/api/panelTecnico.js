import apiClient from './client';

const errorApi = (error, mensaje) => {
  const detalle = error.response?.data?.detail;
  const codigo = error.response?.status;
  const texto = typeof detalle === 'string' ? detalle : error.message;
  return new Error(`${mensaje}${codigo ? ` (HTTP ${codigo})` : ''}: ${texto || 'sin detalle'}`);
};

const obtenerArreglo = async (path, params, mensaje) => {
  try {
    const { data } = await apiClient.get(path, { params });
    if (!Array.isArray(data)) {
      throw new Error('La API no devolvió una lista válida');
    }
    return data;
  } catch (error) {
    throw errorApi(error, mensaje);
  }
};

// GET /api/v1/chambers: cámaras registradas/habilitadas.
// IMPORTANTE: active=true NO demuestra conectividad (online/ping) del gateway.
export const getCamarasTecnico = () =>
  obtenerArreglo('/chambers', undefined, 'No se pudieron consultar las cámaras');

// GET /api/v1/alerts: alertas almacenadas (no "nuevas" ni solo activas).
export const getAlertasSistema = () =>
  obtenerArreglo('/alerts', { limit: 20, offset: 0 }, 'No se pudieron consultar las alertas');

// GET /api/v1/dashboard/temperature: agregados reales de temperatura.
// No representa RX/TX ni bytes de red; el gráfico debe etiquetarse como temperatura.
export const getTemperaturasTecnico = () =>
  obtenerArreglo('/dashboard/temperature', { minutes: 360 }, 'No se pudo consultar la temperatura');

// D6: inventario físico de sensores. Si el backend aún no publica esta ruta,
// el Panel muestra error explícito; NUNCA muestra sensores inventados.
export const getSensores = () =>
  obtenerArreglo('/panel/sensores', undefined, 'Inventario de sensores no disponible (pendiente de D6)');

// Compatibilidad con posibles consumidores antiguos; NO usado por A3.
// Estos endpoints dependen de D6 y fallan de forma visible si no existen.
export const getGateways = () =>
  obtenerArreglo('/panel/gateways', undefined, 'Estado de gateways no disponible (pendiente de D6)');

export const getTraficoRed = () =>
  obtenerArreglo('/panel/trafico', undefined, 'Tráfico de red no disponible (pendiente de D6)');

export const calibrarSensor = async (sensorId) => {
  try {
    const { data } = await apiClient.put(`/panel/calibrar/${encodeURIComponent(sensorId)}`);
    return data;
  } catch (error) {
    throw errorApi(error, 'No se pudo calibrar el sensor');
  }
};

export const verificarSalud = async () => {
  try {
    const { data } = await apiClient.get('/panel/health');
    return data;
  } catch (error) {
    throw errorApi(error, 'No se pudo verificar el estado del panel');
  }
};