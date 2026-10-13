import React from 'react';
import { Bell, User, Menu } from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';


const Header = () => {
    const {user} = useAuth();

  return (
    <header className="bg-white shadow-sm px-6 py-4 flex items-center justify-between">
      {/* Título dinámico */}
      <div className="flex items-center gap-4">
        <h2 className="text-lg font-semibold text-gray-800">
          Panel de Control
        </h2>
      </div>

      {/* Acciones del usuario */}
      <div className="flex items-center gap-4">
        {/* Notificaciones */}
        <button
          className="p-2 rounded-full hover:bg-gray-100 transition-colors relative"
          title="Notificaciones"
        >
          <Bell size={20} className="text-gray-600" />
          {/* Badge de alertas (opcional) */}
          <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></span>
        </button>

        {/* Info del usuario */}
        <div className="flex items-center gap-3 pl-4 border-l border-gray-200">
          <div className="w-9 h-9 rounded-full bg-primary-600 flex items-center justify-center text-white">
            <User size={18} />
          </div>
          <div className="hidden md:flex flex-col">
            <span className="text-sm font-medium text-gray-700">
              {user?.nombre || 'Usuario'}
            </span>
            <span className="text-xs text-gray-500 capitalize">
              {user?.rol || 'Rol'}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;