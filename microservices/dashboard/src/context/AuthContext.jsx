import React, { createContext, useState } from 'react';
import { login as requestToken, getCurrentUser } from '../api/auth';

export const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(() => localStorage.getItem('token'));
  const user = getCurrentUser(token);

  const login = async (email, password) => {
    try {
      const next = await requestToken(email, password);
      if (!getCurrentUser(next)) throw new Error();
      localStorage.setItem('token', next);
      setToken(next);
      return { success: true };
    } catch (error) {
      return { success: false, message: error.response?.status === 401
        ? 'Correo o contraseña incorrectos' : 'No se pudo iniciar sesión' };
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setToken(null);
  };

  return (
    <AuthContext.Provider value={{ user, token, loading: false, login, logout, isAuthenticated: !!user }}>
      {children}
    </AuthContext.Provider>
  );
};
