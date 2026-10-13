import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { useAuth } from './hooks/useAuth';
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
import Configuracion from './pages/Configuracion';

// ============================================================
// RUTA PROTEGIDA
// ============================================================
const ProtectedRoute = ({ children, allowedRoles }) => {
  const { isAuthenticated, loading, user } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-gray-500">Cargando...</div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" />;
  }

  // Si el rol del usuario no está permitido, redirigir al inicio
  if (allowedRoles && !allowedRoles.includes(user?.rol)) {
    return <Navigate to="/" />;
  }

  return children;
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

      {/* ==================================================== */}
      {/* RUTAS DEL GERENTE */}
      {/* ==================================================== */}
      <Route path="/" element={
        <ProtectedRoute allowedRoles={['gerente', 'tecnico']}>
          <Layout>
            {rol === 'gerente' ? <GerenteDashboard /> : <TecnicoDashboard />}
          </Layout>
        </ProtectedRoute>
      } />

      <Route path="/alertas" element={
        <ProtectedRoute allowedRoles={['gerente', 'tecnico']}>
          <Layout>
            {rol === 'gerente' ? <GerenteAlertas /> : <TecnicoAlertas />}
          </Layout>
        </ProtectedRoute>
      } />

      <Route path="/chat-ia" element={
        <ProtectedRoute allowedRoles={['gerente', 'tecnico']}>
          <Layout>
            {rol === 'gerente' ? <GerenteChatIA /> : <TecnicoChatIA />}
          </Layout>
        </ProtectedRoute>
      } />

      <Route path="/haccp" element={
        <ProtectedRoute allowedRoles={['gerente', 'tecnico']}>
          <Layout>
            {rol === 'gerente' ? <GerenteHACCP /> : <TecnicoHACCP />}
          </Layout>
        </ProtectedRoute>
      } />

      <Route path="/historial" element={
        <ProtectedRoute allowedRoles={['gerente', 'tecnico']}>
          <Layout>
            {rol === 'gerente' ? <GerenteHistorial /> : <TecnicoHistorial />}
          </Layout>
        </ProtectedRoute>
      } />

      {/* ==================================================== */}
      {/* RUTAS EXCLUSIVAS DEL GERENTE */}
      {/* ==================================================== */}
      <Route path="/ahorro" element={
        <ProtectedRoute allowedRoles={['gerente']}>
          <Layout><GerenteAhorro /></Layout>
        </ProtectedRoute>
      } />

      <Route path="/camaras" element={
        <ProtectedRoute allowedRoles={['gerente']}>
          <Layout><GerenteCamaras /></Layout>
        </ProtectedRoute>
      } />

      <Route path="/usuarios" element={
        <ProtectedRoute allowedRoles={['gerente']}>
          <Layout><GerenteUsuarios /></Layout>
        </ProtectedRoute>
      } />

      {/* ==================================================== */}
      {/* RUTAS EXCLUSIVAS DEL TÉCNICO */}
      {/* ==================================================== */}
      <Route path="/panel-tecnico" element={
        <ProtectedRoute allowedRoles={['tecnico']}>
          <Layout><TecnicoPanel /></Layout>
        </ProtectedRoute>
      } />

      {/* ==================================================== */}
      {/* RUTA COMPARTIDA */}
      {/* ==================================================== */}
      <Route path="/soporte" element={
        <ProtectedRoute allowedRoles={['gerente', 'tecnico']}>
          <Layout><Soporte /></Layout>
        </ProtectedRoute>
      } />

      <Route path="/configuracion" element={
        <ProtectedRoute allowedRoles={['gerente', 'tecnico']}>
          <Layout><Configuracion /></Layout>
        </ProtectedRoute>
      } />

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