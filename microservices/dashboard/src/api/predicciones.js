import apiClient from './client';

// Respuesta: id_prediction, id_chamber, slope, projected_temperature,
// remaining_time_min, risk_level y calculation_date.
export const getUltimaPrediccion = async (idChamber) => {
  try {
    const response = await apiClient.get('/predictions/latest', {
      params: { id_chamber: idChamber },
    });
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Error al obtener la última predicción');
  }
};

export const getHistorialPredicciones = async (idChamber, { limit = 100, offset = 0 } = {}) => {
  try {
    const response = await apiClient.get('/predictions/history', {
      params: { id_chamber: idChamber, limit, offset },
    });
    return response.data;
  } catch (error) {
    throw new Error(error.response?.data?.detail || 'Error al obtener el historial de predicciones');
  }
};
