import apiClient from './client';

export const preguntarIA = async (
  pregunta,
  camaraId,
  conversacionId = null
) => {
  try {
    const response = await apiClient.post('/gemini/chat', {
      pregunta,
      camara_id: camaraId,
      id_conversation: conversacionId,
    });

    return response.data;
  } catch (error) {
    throw new Error(
      error.response?.data?.detail ||
        'IA no disponible en este momento'
    );
  }
};