// createContext para manejar la autenticación del usuario en la aplicación. Proporciona funciones de login y logout, así como el estado del usuario y el token de autenticación.
// useState para manejar el estado del usuario, token y carga inicial.
// useEffect para cargar el usuario y token desde localStorage al iniciar la aplicación.

import React, { createContext, useState, useEffect } from 'react'; 

export const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const savedUser = localStorage.getItem('user');
    if (token && savedUser) {
      setUser(JSON.parse(savedUser));
    }
    setLoading(false);
  }, [token]);


  // LOGIN MOCK (temporal, mientras Diego no tenga el endpoint)
  // El rol se determina por el email (mock).
  // En producción, el backend devuelve el rol en el token JWT.
  const login = async (email, password) => {
    await new Promise((resolve) => setTimeout(resolve, 500));

    if (!email || !password) {
      return { success: false, message: 'Email y contraseña son obligatorios' };
    }

    // MOCK: Detectar rol por el email
    // toLowerCase() para evitar problemas con mayúsculas/minúsculas
    const rol = email.toLowerCase().includes('tecnico') ? 'tecnico' : 'gerente';

    // mockUser y mockToken generados para simular un login exitoso. En producción, estos valores se obtendrían del backend.
    const mockUser = {
      id: '1',
      email: email,
      rol: rol,
      nombre: email.split('@')[0],
    };

    const mockToken = 'mock-token-' + Date.now();

    localStorage.setItem('token', mockToken);
    localStorage.setItem('user', JSON.stringify(mockUser));

    setToken(mockToken);
    setUser(mockUser);

    return { success: true };
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setToken(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        loading,
        login,
        logout,
        isAuthenticated: !!token,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};