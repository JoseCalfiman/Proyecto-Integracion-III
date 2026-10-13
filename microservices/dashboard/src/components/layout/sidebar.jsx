import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  Home, AlertTriangle, TrendingUp, MessageSquare,
  Settings, Users, FileText, LogOut, HelpCircle,
  Camera, Wrench, ClipboardList,
} from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';

const Sidebar = () => {
  const location = useLocation();
  const { user, logout } = useAuth();
  const rol = user?.rol || 'gerente';

  const menuGerente = [
    { icon: Home, label: 'Monitoreo', path: '/' },
    { icon: AlertTriangle, label: 'Alertas HACCP', path: '/alertas' },
    { icon: TrendingUp, label: 'Optimización y Ahorro', path: '/ahorro' },
    { icon: MessageSquare, label: 'Asistente IA', path: '/chat-ia' },
    { icon: Camera, label: 'Configuración de Cámaras', path: '/camaras' },
    { icon: ClipboardList, label: 'Reglas HACCP', path: '/haccp' },  // ← Cambiado
    { icon: Users, label: 'Gestión de Usuarios', path: '/usuarios' },
    { icon: FileText, label: 'Historial y Reportes', path: '/historial' },
    { icon: Settings, label: 'Configuración', path: '/configuracion' },
  ];

  const menuTecnico = [
    { icon: Home, label: 'Monitoreo', path: '/' },
    { icon: AlertTriangle, label: 'Alertas HACCP', path: '/alertas' },
    { icon: MessageSquare, label: 'Asistente IA', path: '/chat-ia' },
    { icon: ClipboardList, label: 'Reglas HACCP', path: '/haccp' },  // ← Cambiado
    { icon: Wrench, label: 'Panel Técnico', path: '/panel-tecnico' },
    { icon: FileText, label: 'Historial y Reportes', path: '/historial' },
    { icon: Settings, label: 'Configuración', path: '/configuracion' },
  ];

  const menuItems = rol === 'gerente' ? menuGerente : menuTecnico;

  return (
    <aside className="w-64 bg-white shadow-md flex flex-col h-full">
      <div className="p-6 border-b">
        <h1 className="text-2xl font-bold text-green-600">CryoMetric</h1>
        <p className="text-xs text-gray-500">Cold Storage Monitoring</p>
      </div>

      <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
        {menuItems.map((item, index) => {
          const isActive = location.pathname === item.path;
          return (
            <Link
              key={index}
              to={item.path}
              className={`flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-green-50 text-green-600'
                  : 'text-gray-700 hover:bg-gray-50'
              }`}
            >
              <item.icon size={18} />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t space-y-1">
        <Link
          to="/soporte"
          className="flex items-center gap-3 px-4 py-2 text-sm text-gray-600 hover:bg-gray-50 rounded-lg"
        >
          <HelpCircle size={18} />
          Ayuda y Soporte
        </Link>
        <button
          onClick={logout}
          className="flex items-center gap-3 px-4 py-2 text-sm text-red-600 hover:bg-red-50 rounded-lg w-full"
        >
          <LogOut size={18} />
          Cerrar Sesión
        </button>
      </div>
    </aside>
  );
};

export default Sidebar;