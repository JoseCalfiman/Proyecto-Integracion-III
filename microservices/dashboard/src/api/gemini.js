// Cliente del asistente IA (Gemini): envía la pregunta + cámara seleccionada
// y FastAPI arma el contexto histórico antes de reenviar a Gemini.

import apiClient from './client';

export const preguntarIA = async (pregunta, camaraId) => {
  try {
    const response = await apiClient.post('/gemini/chat', {
      pregunta,
      camara_id: camaraId,
    });
    return response.data;
  } catch (error) {
    throw new Error(
      error.response?.data?.detail || 'IA no disponible en este momento'
    );
  }
};
