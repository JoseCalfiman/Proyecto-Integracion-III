// Cliente de cámaras: CRUD sobre /api/v1/camaras (gestión solo Gerente).

import apiClient from "./client";
import { camaraFromApi, camaraToApi } from "./adapters";

// id de la empresa (el backend exige id_company al crear). Mientras no haya login real,
// usa la empresa del seed; luego saldrá del JWT.
const COMPANY_ID =
  import.meta.env.VITE_COMPANY_ID || "11111111-1111-1111-1111-111111111111";

const msg = (error, fallback) => error.response?.data?.detail || fallback;

// listar las camaras
// permisos: tecnico, gerente
export const getCamaras = async () => {
  try {
    const { data } = await apiClient.get("/chambers");
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
      id_company: COMPANY_ID,
      ...camaraToApi(form),
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
export const eliminarCamara = async (id) => {
  try {
    await apiClient.delete(`/chambers/${id}`);
  } catch (error) {
    throw new Error(msg(error, "Error al eliminar la cámara"));
  }
};
