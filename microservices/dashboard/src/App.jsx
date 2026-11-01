import { lazy, Suspense } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { useAuth } from './hooks/useAuth';
import Layout from './components/layout/Layout';

const Login = lazy(() => import('./pages/Login'));

const GerenteDashboard = lazy(() => import('./pages/gerente/Dashboard'));
const GerenteAlertas = lazy(() => import('./pages/gerente/Alertas'));
const GerenteAhorro = lazy(() => import('./pages/gerente/Ahorro'));
const GerenteChatIA = lazy(() => import('./pages/gerente/ChatIA'));
const GerenteCamaras = lazy(() => import('./pages/gerente/Camaras'));
const GerenteHACCP = lazy(() => import('./pages/gerente/HACCP'));
const GerenteUsuarios = lazy(() => import('./pages/gerente/Usuarios'));
const GerenteHistorial = lazy(() => import('./pages/gerente/Historial'));

const TecnicoDashboard = lazy(() => import('./pages/tecnico/Dashboard'));
const TecnicoAlertas = lazy(() => import('./pages/tecnico/Alertas'));
const TecnicoChatIA = lazy(() => import('./pages/tecnico/ChatIA'));
const TecnicoHACCP = lazy(() => import('./pages/tecnico/HACCP'));
const TecnicoPanel = lazy(() => import('./pages/tecnico/PanelTecnico'));
const TecnicoHistorial = lazy(() => import('./pages/tecnico/Historial'));

const Soporte = lazy(() => import('./pages/Soporte'));
const Configuracion = lazy(() => import('./pages/Configuracion'));
const routeFallback = (
  <div className="min-h-screen flex items-center justify-center text-gray-500">
    Cargando...
  </div>
);

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

  const routes = (
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

  return <Suspense fallback={routeFallback}>{routes}</Suspense>;
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
