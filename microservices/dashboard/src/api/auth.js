// lo que hace este archivo es la logica de autenticacion, es decir, las funciones que se encargan de
// hacer las peticiones a la API para iniciar sesión, cerrar sesión y obtener el usuario actual.

import apiClient from './client';

// LOGIN
export const login = async (email, password) => {
  try {
    const response = await apiClient.post('/auth/login', {
      email,
      password,
    });
    return response.data;
  } catch (error) {
    throw new Error(
      error.response?.data?.detail ||
      error.response?.data?.message ||
      'Error al iniciar sesión'
    );
  }
};

// LOGOUT
export const logout = () => {
  localStorage.removeItem('token');
  localStorage.removeItem('user');
};

// OBTENER USUARIO ACTUAL (decodifica el JWT)
export const getCurrentUser = () => {
  try {
    const token = localStorage.getItem('token');
    if (!token) return null;

    const payload = JSON.parse(atob(token.split('.')[1]));

    return {
      id: payload.sub,
      email: payload.email,
      rol: payload.rol,
      nombre: payload.nombre,
    };
  } catch (error) {
    console.error('Error al decodificar el token:', error);
    return null;
  }
};

// VERIFICAR SI EL USUARIO ESTÁ AUTENTICADO
export const isAuthenticated = () => {
  const token = localStorage.getItem('token');
  if (!token) return false;

  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    const now = Date.now() / 1000;
    return payload.exp > now;
  } catch {
    return false;
  }
};

