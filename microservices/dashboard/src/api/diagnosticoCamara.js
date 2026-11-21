import apiClient from './client';
import { getHistorial } from './historial';
import { getHistorialPredicciones } from './predicciones';

const validarLista = (data, endpoint) => {
  if (!Array.isArray(data)) {
    throw new Error(`${endpoint}: el backend no devolvió una lista válida`);
  }
  return data;
};

/** Consulta lecturas de la cámara en una ventana móvil, usando timestamps ISO UTC. */
export const getLecturasDiagnostico = (idChamber, { hours = 24, limit = 10000 } = {}) => {
  const hasta = new Date();
  const desde = new Date(hasta.getTime() - (hours * 60 * 60 * 1000));

  return getHistorial({
    id_chamber: idChamber,
    desde: desde.toISOString(),
    hasta: hasta.toISOString(),
    limit,
  }).then((data) => validarLista(data, 'Historial de lecturas'));
};

export const getPrediccionesDiagnostico = (idChamber) =>
  getHistorialPredicciones(idChamber, { limit: 20, offset: 0 })
    .then((data) => validarLista(data, 'Historial de predicciones'));

export const getReglaDiagnostico = async (idChamber) => {
  // Se conserva el contrato original del backend (id_rule, max_absolute_temp,
  // min_absolute_temp, tolerance_time_min, severity, active, review_date).
  // No usar getReglasPorCamara aquí: ese helper adapta los campos al formato español.
  const { data } = await apiClient.get(`/haccp/rules/${encodeURIComponent(idChamber)}`);
  return data;
};

export const getAlertasDiagnostico = async (idChamber) => {
  const { data } = await apiClient.get('/alerts', {
    params: { id_chamber: idChamber, limit: 20, offset: 0 },
  });
  return validarLista(data, 'Alertas de la cámara');
};