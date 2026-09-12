// lo que se desarrolla en este archivo es la logica de las alertas, es decir, las funciones que se encargan de
// hacer las peticiones a la API para obtener, crear, actualizar y eliminar alertas.

import apiClient from './client';

// listar alertas
export const getAlertas = async (filtros = {}) => {
    try {
        const response = await apiClient.get('/alertas', { params: filtros });
        return response.data;
    } catch (error) {
        throw new Error(
            error.response?.data?.detail ||
            error.response?.data?.message ||
            'Error al obtener las alertas'
        );
    }
};


// obtener alerta por ID
export const getAlertaById = async (id) => {
    try {
        const response = await apiClient.get(`/alertas/${id}`);
        return response.data;
    } catch (error) {
        throw new Error(
            error.response?.data?.detail ||
            error.response?.data?.message ||
            'Error al obtener la alerta'
        );
    }
};


// reconocer la alerta por el lado del tecnico 
export const reconocerAlerta = async (id) => {
    try {
        const response = await apiClient.put(`/alertas/${id}/acknowledge`);
        return response.data;
    } catch (error) {
        throw new Error(
            error.response?.data?.detail ||
            error.response?.data?.message ||
            'Error al reconocer la alerta'
        );
    }
};

// resolver alterta (solo tecnico)
export const resolverAlerta = async (id) => {
    try {
        const response = await apiClient.put(`/alertas/${id}/resolve`);
        return response.data;
    } catch (error) {
        throw new Error(
            error.response?.data?.detail ||
            error.response?.data?.message ||
            'Error al resolver la alerta'
        );
    }
};

