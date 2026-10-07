// lo que se desarrolla en este archivo es la logica de las alertas, es decir, las funciones que se encargan de
// hacer las peticiones a la API para obtener, crear, actualizar y eliminar alertas.
import apiClient from "./client";
import { alertaFromApi, SEVERIDAD_BACK, ESTADO_BACK } from "./adapters";

const msg = (error, fallback) => error.response?.data?.detail || fallback;

// "ALT-12" -> 12
const idNumerico = (id) => parseInt(String(id).replace(/\D/g, ""), 10);

// listar alertas
export const getAlertas = async (filtros = {}) => {
  try {
    const params = { limit: 200 };
    if (filtros.estado) params.status = ESTADO_BACK[filtros.estado];
    if (filtros.severidad) params.severity = SEVERIDAD_BACK[filtros.severidad];
    const { data } = await apiClient.get("/alerts", { params });
    return data.map(alertaFromApi);
  } catch (error) {
    throw new Error(msg(error, "Error al obtener las alertas"));
  }
};

// obtener alerta por ID
export const getAlertaById = async (id) => {
  try {
    const { data } = await apiClient.get(`/alerts/${idNumerico(id)}`);
    return alertaFromApi(data);
  } catch (error) {
    throw new Error(msg(error, "Error al obtener la alerta"));
  }
};

// Solo técnico
const idUsuario = () => {
  try {
    return JSON.parse(localStorage.getItem("user"))?.id;
  } catch {
    return undefined;
  }
};

// reconocer la alerta por el lado del tecnico
export const reconocerAlerta = async (id) => {
  try {
    const { data } = await apiClient.put(
      `/alerts/${idNumerico(id)}/acknowledge`,
      { id_user: idUsuario() },
    );
    return alertaFromApi(data);
  } catch (error) {
    throw new Error(msg(error, "Error al reconocer la alerta"));
  }
};

// resolver alterta (solo tecnico)
export const resolverAlerta = async (id) => {
  try {
    const { data } = await apiClient.put(`/alerts/${idNumerico(id)}/resolve`, {
      id_user: idUsuario(),
    });
    return alertaFromApi(data);
  } catch (error) {
    throw new Error(msg(error, "Error al resolver la alerta"));
  }
};