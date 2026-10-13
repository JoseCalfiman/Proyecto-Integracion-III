import React, { useState } from 'react';
import {
  User, Bell, Globe, Shield, Settings, Search, HelpCircle,
  Download, Camera as CameraIcon, Eye, EyeOff, Save, Check,
} from 'lucide-react';
import { useAuth } from '../hooks/useAuth';

// ============================================================
// COMPONENTE
// ============================================================
const Configuracion = () => {
  const { user } = useAuth();
  const esGerente = user?.rol === 'gerente';

  // ==========================================================
  // ESTADO DEL FORMULARIO
  // ==========================================================
  const [perfil, setPerfil] = useState({
    nombre: user?.nombre || 'Carlos Mendoza',
    email: user?.email || 'c.mendoza@cryometric.net',
    rol: user?.rol || 'gerente',
  });

  const [password, setPassword] = useState({
    actual: '',
    nueva: '',
    confirmar: '',
  });
  const [mostrarPassword, setMostrarPassword] = useState(false);

  const [notificaciones, setNotificaciones] = useState({
    critica: { email: true },
    advertencia: { email: true },
    info: { email: false },
  });

  const [regional, setRegional] = useState({
    idioma: 'es-CL',
    zona_horaria: 'America/Santiago',
    unidad_temp: 'celsius',
  });

  const [seguridad, setSeguridad] = useState({
    timeout_min: 30,
  });

  const [parametros, setParametros] = useState({
    sampling_rate_seg: 5,
    latencia_max_ms: 150,
  });

  const [guardado, setGuardado] = useState(false);

  // ==========================================================
  // GUARDAR
  // ==========================================================
  const handleGuardar = async () => {
    // TODO: llamar a la API para guardar los cambios
    setGuardado(true);
    setTimeout(() => setGuardado(false), 2000);
  };

  return (
    <div>
      {/* ==================================================== */}
      {/* HEADER SUPERIOR */}
      {/* ==================================================== */}
      <div className="flex items-center justify-end gap-3 mb-6">
        <button className="relative p-2 rounded-full hover:bg-gray-100">
          <Bell size={20} className="text-gray-600" />
          <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></span>
        </button>
        <button className="p-2 rounded-full hover:bg-gray-100">
          <HelpCircle size={20} className="text-gray-600" />
        </button>
        <button className="flex items-center gap-2 bg-green-500 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-600">
          <Download size={16} />
          Descargar Reporte
        </button>
        <div className="w-9 h-9 rounded-full bg-gray-200 flex items-center justify-center">
          <User size={18} className="text-gray-600" />
        </div>
      </div>

      {/* ==================================================== */}
      {/* TÍTULO */}
      {/* ==================================================== */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Configuración del Sistema</h1>
          <p className="text-sm text-gray-500">
            Administra tu cuenta, preferencias y parámetros del sistema.
          </p>
        </div>
        <button
          onClick={handleGuardar}
          className="flex items-center gap-2 text-sm font-medium text-green-600 hover:text-green-700"
        >
          {guardado ? <Check size={16} /> : <Save size={16} />}
          {guardado ? 'Guardado' : 'Guardar Cambios'}
        </button>
      </div>

      {/* ==================================================== */}
      {/* PERFIL DE USUARIO */}
      {/* ==================================================== */}
      <div className="bg-white p-6 rounded-lg shadow-md mb-6">
        <div className="flex items-center gap-2 mb-6">
          <User size={18} className="text-green-600" />
          <h2 className="font-semibold text-gray-800">Perfil de Usuario</h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Avatar */}
          <div className="flex flex-col items-center">
            <div className="w-28 h-28 rounded-lg bg-gray-100 flex items-center justify-center mb-3">
              <CameraIcon size={32} className="text-gray-400" />
            </div>
            <button className="text-xs text-green-600 hover:text-green-700 font-medium">
              Cambiar Avatar
            </button>
          </div>

          {/* Datos */}
          <div className="md:col-span-2 grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Nombre Completo</label>
              <input
                type="text"
                value={perfil.nombre}
                onChange={(e) => setPerfil({ ...perfil, nombre: e.target.value })}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Correo Electrónico</label>
              <input
                type="email"
                value={perfil.email}
                onChange={(e) => setPerfil({ ...perfil, email: e.target.value })}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Rol / Nivel de Acceso</label>
              <input
                type="text"
                value={perfil.rol === 'gerente' ? 'Gerente' : 'Técnico'}
                disabled
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-gray-50 text-gray-500"
              />
            </div>
          </div>
        </div>

        {/* Cambiar Contraseña */}
        <div className="mt-6 pt-6 border-t border-gray-100">
          <h3 className="text-sm font-medium text-gray-700 mb-4">Cambiar Contraseña</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Contraseña Actual</label>
              <input
                type={mostrarPassword ? 'text' : 'password'}
                value={password.actual}
                onChange={(e) => setPassword({ ...password, actual: e.target.value })}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Nueva Contraseña</label>
              <input
                type={mostrarPassword ? 'text' : 'password'}
                value={password.nueva}
                onChange={(e) => setPassword({ ...password, nueva: e.target.value })}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Confirmar Nueva</label>
              <input
                type={mostrarPassword ? 'text' : 'password'}
                value={password.confirmar}
                onChange={(e) => setPassword({ ...password, confirmar: e.target.value })}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
              />
            </div>
          </div>
          <button
            type="button"
            onClick={() => setMostrarPassword(!mostrarPassword)}
            className="mt-2 flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700"
          >
            {mostrarPassword ? <EyeOff size={12} /> : <Eye size={12} />}
            {mostrarPassword ? 'Ocultar' : 'Mostrar'} contraseñas
          </button>
        </div>
      </div>

      {/* ==================================================== */}
      {/* PREFERENCIAS DE NOTIFICACIÓN */}
      {/* ==================================================== */}
      <div className="bg-white p-6 rounded-lg shadow-md mb-6">
        <div className="flex items-center gap-2 mb-6">
          <Bell size={18} className="text-green-600" />
          <h2 className="font-semibold text-gray-800">Preferencias de Notificación</h2>
        </div>

        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-gray-500 uppercase">
              <th className="pb-3 font-medium">Tipo de Alerta</th>
              <th className="pb-3 font-medium text-center">Email</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            <tr>
              <td className="py-3 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-red-500"></span>
                <span className="text-gray-700">Crítica (Violación HACCP)</span>
              </td>
              <td className="py-3 text-center">
                <input
                  type="checkbox"
                  checked={notificaciones.critica.email}
                  onChange={(e) =>
                    setNotificaciones({
                      ...notificaciones,
                      critica: { email: e.target.checked },
                    })
                  }
                  className="accent-green-500"
                />
              </td>
            </tr>
            <tr>
              <td className="py-3 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-yellow-500"></span>
                <span className="text-gray-700">Advertencia (Umbral Cercano)</span>
              </td>
              <td className="py-3 text-center">
                <input
                  type="checkbox"
                  checked={notificaciones.advertencia.email}
                  onChange={(e) =>
                    setNotificaciones({
                      ...notificaciones,
                      advertencia: { email: e.target.checked },
                    })
                  }
                  className="accent-green-500"
                />
              </td>
            </tr>
            <tr>
              <td className="py-3 flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-blue-500"></span>
                <span className="text-gray-700">Info (Actualizaciones del Sistema)</span>
              </td>
              <td className="py-3 text-center">
                <input
                  type="checkbox"
                  checked={notificaciones.info.email}
                  onChange={(e) =>
                    setNotificaciones({
                      ...notificaciones,
                      info: { email: e.target.checked },
                    })
                  }
                  className="accent-green-500"
                />
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* ==================================================== */}
      {/* REGIONAL Y LOCALIZACIÓN */}
      {/* ==================================================== */}
      <div className="bg-white p-6 rounded-lg shadow-md mb-6">
        <div className="flex items-center gap-2 mb-6">
          <Globe size={18} className="text-green-600" />
          <h2 className="font-semibold text-gray-800">Regional y Localización</h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Idioma</label>
            <select
              value={regional.idioma}
              onChange={(e) => setRegional({ ...regional, idioma: e.target.value })}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
            >
              <option value="es-CL">Español (Chile)</option>
              <option value="en-US">English (US)</option>
            </select>
          </div>

          <div>
            <label className="block text-xs text-gray-500 mb-1">Zona Horaria</label>
            <select
              value={regional.zona_horaria}
              onChange={(e) => setRegional({ ...regional, zona_horaria: e.target.value })}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
            >
              <option value="America/Santiago">(UTC-03:00) Santiago</option>
              <option value="America/Buenos_Aires">(UTC-03:00) Buenos Aires</option>
              <option value="America/Lima">(UTC-05:00) Lima</option>
            </select>
          </div>

          <div className="md:col-span-2">
            <label className="block text-xs text-gray-500 mb-2">Unidades de Temperatura</label>
            <div className="flex gap-6">
              <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                <input
                  type="radio"
                  name="temp"
                  value="celsius"
                  checked={regional.unidad_temp === 'celsius'}
                  onChange={(e) => setRegional({ ...regional, unidad_temp: e.target.value })}
                  className="accent-green-500"
                />
                Celsius (°C)
              </label>
              <label className="flex items-center gap-2 text-sm text-gray-700 cursor-pointer">
                <input
                  type="radio"
                  name="temp"
                  value="fahrenheit"
                  checked={regional.unidad_temp === 'fahrenheit'}
                  onChange={(e) => setRegional({ ...regional, unidad_temp: e.target.value })}
                  className="accent-green-500"
                />
                Fahrenheit (°F)
              </label>
            </div>
          </div>
        </div>
      </div>

      {/* ==================================================== */}
      {/* SEGURIDAD */}
      {/* ==================================================== */}
      <div className="bg-white p-6 rounded-lg shadow-md mb-6">
        <div className="flex items-center gap-2 mb-6">
          <Shield size={18} className="text-green-600" />
          <h2 className="font-semibold text-gray-800">Seguridad</h2>
        </div>

        <div className="max-w-xs">
          <label className="block text-xs text-gray-500 mb-1">
            Timeout de Sesión (Minutos)
          </label>
          <input
            type="number"
            min="5"
            max="120"
            value={seguridad.timeout_min}
            onChange={(e) => setSeguridad({ ...seguridad, timeout_min: e.target.value })}
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
          />
          <p className="text-xs text-gray-400 mt-1">
            Cierre de sesión automático tras inactividad.
          </p>
        </div>
      </div>

      {/* ==================================================== */}
      {/* PARÁMETROS DEL SISTEMA (SOLO GERENTE) */}
      {/* ==================================================== */}
      {esGerente && (
        <div className="bg-white p-6 rounded-lg shadow-md">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-2">
              <Settings size={18} className="text-green-600" />
              <h2 className="font-semibold text-gray-800">Parámetros del Sistema</h2>
            </div>
            <span className="text-xs text-blue-700 bg-blue-50 px-3 py-1 rounded-full font-medium">
              Solo Gerente
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Sampling Rate */}
            <div className="border border-gray-200 rounded-lg p-4">
              <label className="block text-xs text-gray-500 mb-2">
                Frecuencia de Muestreo de Sensores
              </label>
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min="1"
                  max="30"
                  value={parametros.sampling_rate_seg}
                  onChange={(e) =>
                    setParametros({ ...parametros, sampling_rate_seg: parseInt(e.target.value) })
                  }
                  className="flex-1 accent-green-500"
                />
                <span className="text-sm font-medium text-gray-700 w-12 text-right">
                  {parametros.sampling_rate_seg}s
                </span>
              </div>
              <p className="text-xs text-gray-400 mt-2">
                Frecuencia de recolección de datos de los sensores activos.
              </p>
            </div>

            {/* Latencia */}
            <div className="border border-gray-200 rounded-lg p-4">
              <label className="block text-xs text-gray-500 mb-2">
                Umbral de Latencia de Red (ms)
              </label>
              <div className="flex items-center gap-3">
                <input
                  type="number"
                  value={parametros.latencia_max_ms}
                  onChange={(e) =>
                    setParametros({ ...parametros, latencia_max_ms: parseInt(e.target.value) })
                  }
                  className="w-24 border border-gray-200 rounded-lg px-3 py-2 text-sm"
                />
                <span className="text-sm text-gray-500">ms</span>
              </div>
              <p className="text-xs text-gray-400 mt-2">
                Alerta si la latencia supera este umbral.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Configuracion;