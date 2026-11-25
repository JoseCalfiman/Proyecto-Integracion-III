// Cliente de cámaras: CRUD sobre /api/v1/chambers (gestión solo Gerente).

import apiClient from "./client";
import { camaraFromApi, camaraToApi } from "./adapters";

const msg = (error, fallback) => {
  const detail = error.response?.data?.detail;
  const status = error.response?.status;
  const text = typeof detail === 'string' ? detail
    : Array.isArray(detail) ? detail.map((item) => item.msg).join('; ')
    : error.message;
  return `${fallback}${status ? ` (HTTP ${status})` : ''}${text ? `: ${text}` : ''}`;
};

// listar las camaras
// permisos: tecnico, gerente
export const getCamaras = async (includeInactive = false) => {
  try {
    const { data } = await apiClient.get("/chambers", { params: { include_inactive: includeInactive === true } });
    if (!Array.isArray(data)) throw new Error("Respuesta de cámaras inválida");
    return data.map(camaraFromApi);
  } catch (error) {
    throw new Error(msg(error, "Error al obtener las cámaras"));
  }
};

// obtener una camara por ID
// permisos: tecnico, gerente
export const getCamara = async (id) => {
  try {
    const { data } = await apiClient.get(`/chambers/${id}`);
    return camaraFromApi(data);
  } catch (error) {
    throw new Error(msg(error, "Error al obtener la cámara"));
  }
};

// crear camara
// solo gerente
export const crearCamara = async (form) => {
  try {
    const { data } = await apiClient.post("/chambers", {
      name: form.nombre.trim(),
      location: form.ubicacion.trim() || null,
    });
    return camaraFromApi(data);
  } catch (error) {
    throw new Error(msg(error, "Error al crear la cámara"));
  }
};

// actualizar camara
// solo gerente
export const actualizarCamara = async (id, form) => {
  try {
    const { data } = await apiClient.put(`/chambers/${id}`, camaraToApi(form));
    return camaraFromApi(data);
  } catch (error) {
    throw new Error(msg(error, "Error al actualizar la cámara"));
  }
};

// eliminar camara
// solo gerente
export const eliminarCamara = async (id, permanent = false) => {
  try {
    await apiClient.delete(`/chambers/${id}`, { params: { permanent } });
  } catch (error) {
    throw new Error(msg(error, "Error al eliminar la cámara"));
  }
};