import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'; // browserRouter para manejar la navegación en la aplicación, Routes para definir las rutas y Route para cada ruta individual. Navigate se utiliza para redirigir a los usuarios no autenticados a la página de login.
import { AuthProvider } from './context/AuthContext'; // use AuthProvider para envolver la aplicación y proporcionar el contexto de autenticación a todos los componentes.
import { useAuth } from './hooks/useAuth'; // useAuth importado para acceder al contexto de autenticación y verificar si el usuario está autenticado y su rol.
import Login from './pages/Login';
import Layout from './components/layout/Layout';

// Páginas del Gerente
import GerenteDashboard from './pages/gerente/Dashboard';
import GerenteAlertas from './pages/gerente/Alertas';
import GerenteAhorro from './pages/gerente/Ahorro';
import GerenteChatIA from './pages/gerente/ChatIA';
import GerenteCamaras from './pages/gerente/Camaras';
import GerenteHACCP from './pages/gerente/HACCP';
import GerenteUsuarios from './pages/gerente/Usuarios';
import GerenteHistorial from './pages/gerente/Historial';

// Páginas del Técnico
import TecnicoDashboard from './pages/tecnico/Dashboard';
import TecnicoAlertas from './pages/tecnico/Alertas';
import TecnicoChatIA from './pages/tecnico/ChatIA';
import TecnicoHACCP from './pages/tecnico/HACCP';
import TecnicoPanel from './pages/tecnico/PanelTecnico';
import TecnicoHistorial from './pages/tecnico/Historial';

// Página compartida
import Soporte from './pages/Soporte';

// ============================================================
// RUTA PROTEGIDA
// ============================================================
const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-gray-500">Cargando...</div>
      </div>
    );
  }

  return isAuthenticated ? children : <Navigate to="/login" />;
};

// ============================================================
// RUTAS SEGÚN EL ROL
// ============================================================
const AppRoutes = () => {
  const { user } = useAuth();
  const rol = user?.rol;

  return (
    <Routes>
      <Route path="/login" element={<Login />} />

      {/* Rutas del Gerente */}
      {rol === 'gerente' && (
        <>
          <Route path="/" element={<ProtectedRoute><Layout><GerenteDashboard /></Layout></ProtectedRoute>} />
          <Route path="/alertas" element={<ProtectedRoute><Layout><GerenteAlertas /></Layout></ProtectedRoute>} />
          <Route path="/ahorro" element={<ProtectedRoute><Layout><GerenteAhorro /></Layout></ProtectedRoute>} />
          <Route path="/chat-ia" element={<ProtectedRoute><Layout><GerenteChatIA /></Layout></ProtectedRoute>} />
          <Route path="/camaras" element={<ProtectedRoute><Layout><GerenteCamaras /></Layout></ProtectedRoute>} />
          <Route path="/haccp" element={<ProtectedRoute><Layout><GerenteHACCP /></Layout></ProtectedRoute>} />
          <Route path="/usuarios" element={<ProtectedRoute><Layout><GerenteUsuarios /></Layout></ProtectedRoute>} />
          <Route path="/historial" element={<ProtectedRoute><Layout><GerenteHistorial /></Layout></ProtectedRoute>} />
        </>
      )}

      {/* Rutas del Técnico */}
      {rol === 'tecnico' && (
        <>
          <Route path="/" element={<ProtectedRoute><Layout><TecnicoDashboard /></Layout></ProtectedRoute>} />
          <Route path="/alertas" element={<ProtectedRoute><Layout><TecnicoAlertas /></Layout></ProtectedRoute>} />
          <Route path="/chat-ia" element={<ProtectedRoute><Layout><TecnicoChatIA /></Layout></ProtectedRoute>} />
          <Route path="/haccp" element={<ProtectedRoute><Layout><TecnicoHACCP /></Layout></ProtectedRoute>} />
          <Route path="/panel-tecnico" element={<ProtectedRoute><Layout><TecnicoPanel /></Layout></ProtectedRoute>} />
          <Route path="/historial" element={<ProtectedRoute><Layout><TecnicoHistorial /></Layout></ProtectedRoute>} />
        </>
      )}

      {/* Ruta compartida */}
      <Route path="/soporte" element={<ProtectedRoute><Layout><Soporte /></Layout></ProtectedRoute>} />

      {/* Redirección por defecto */}
      <Route path="*" element={<Navigate to="/" />} />
    </Routes>
  );
};

function App() {
  return (
    <AuthProvider>
      <Router>
        <AppRoutes />
      </Router>
    </AuthProvider>
  );
}

export default App;