import React, { useState } from 'react';
import {
  CheckCircle2, Filter, ThermometerSnowflake, Search, Bell,
  Download, Eye, Check, AlertTriangle, Info, User, Clock,
} from 'lucide-react';
import Badge from '../ui/Badge';
import { useFetch } from '../../hooks/useApi';
import { getAlertas, reconocerAlerta, resolverAlerta } from '../../api/alertas';
import { formatDate } from '../../utils/formatters';

// DATOS MOCK (mientras Diego no tenga los endpoints listos)
const MOCK_ALERTAS = [
  {
    id: 'ALT-8492',
    camara: 'Cámara Congelación 01',
    mensaje: 'Temperatura excedió límite superior (-18°C) por > 15 min. Actual: -15.3°C',
    temperatura: -15.3,
    severidad: 'critica',
    estado: 'activa',
    timestamp: '2023-10-27T14:23:45',
    auditoria: null,
  },
  {
    id: 'ALT-8491',
    camara: 'Cámara Conservación 02',
    mensaje: 'Fluctuación anómala detectada en ciclo de deshielo. Actual: 3.1°C',
    temperatura: 3.1,
    severidad: 'advertencia',
    estado: 'activa',
    timestamp: '2023-10-27T14:10:12',
    auditoria: null,
  },
  {
    id: 'ALT-8488',
    camara: 'Túnel de Enfriamiento',
    mensaje: 'Caída de presión en compresor A. Revisión en curso por equipo técnico.',
    temperatura: null,
    severidad: 'critica',
    estado: 'reconocida',
    timestamp: '2023-10-27T11:05:00',
    auditoria: {
      reconocida_por: 'Tec. Soto',
      fecha_reconocida: '2023-10-27T11:30:00',
    },
  },
  {
    id: 'ALT-8475',
    camara: 'Cámara Congelación 01',
    mensaje: 'Fallo de sensor puerta abierta (Resuelto).',
    temperatura: null,
    severidad: 'advertencia',
    estado: 'resuelta',
    timestamp: '2023-10-26T22:15:00',
    auditoria: {
      reconocida_por: 'Ing. Martinez',
      fecha_reconocida: '2023-10-26T22:20:00',
      resuelta_por: 'Ing. Martinez',
      fecha_resuelta: '2023-10-26T22:45:00',
    },
  },
];

// ============================================================
// CONFIGURACIÓN DE COLORES
// ============================================================
const severidadConfig = {
  critica: { color: 'red', label: 'Crítica', icon: AlertTriangle },
  advertencia: { color: 'yellow', label: 'Advertencia', icon: Info },
  baja: { color: 'blue', label: 'Baja', icon: Info },
};

const estadoConfig = {
  activa: { color: 'red', label: 'Activa' },
  reconocida: { color: 'yellow', label: 'Reconocida' },
  resuelta: { color: 'green', label: 'Resuelta' },
};


const AlertasView = ({ canManage = false }) => {
  const [filtros, setFiltros] = useState({ camara: '', severidad: '', estado: '' });
  const [busqueda, setBusqueda] = useState('');
  const { data: alertas, loading, isFallback, reload } = useFetch(
    () => getAlertas(filtros),
    [filtros.camara, filtros.severidad, filtros.estado],
    MOCK_ALERTAS
  );
  const [actionLoadingId, setActionLoadingId] = useState(null);

  const handleAccion = async (id, accion) => {
    setActionLoadingId(id);
    try {
      if (accion === 'reconocer') await reconocerAlerta(id);
      else await resolverAlerta(id);
    } catch (err) {
      // Backend aún no disponible
    } finally {
      setActionLoadingId(null);
      reload();
    }
  };

  const lista = Array.isArray(alertas) ? alertas : [];

  // ============================================================
  // KPIs
  // ============================================================
  const activas = lista.filter((a) => a.estado === 'activa').length;
  const reconocidas = lista.filter((a) => a.estado === 'reconocida').length;
  const resueltas24h = lista.filter((a) => a.estado === 'resuelta').length;

  // ============================================================
  // FILTRO DE BÚSQUEDA
  // ============================================================
  const listaFiltrada = lista.filter((a) => {
    if (!busqueda) return true;
    const texto = busqueda.toLowerCase();
    return (
      a.id?.toLowerCase().includes(texto) ||
      a.camara?.toLowerCase().includes(texto) ||
      a.mensaje?.toLowerCase().includes(texto)
    );
  });

  return (
    <div>
      {/* ==================================================== */}
      {/* HEADER SUPERIOR: Búsqueda + Notificaciones + Descargar */}
      {/* ==================================================== */}
      <div className="flex items-center justify-between mb-6">
        <div className="relative flex-1 max-w-md">
          <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="Buscar alertas, cámaras..."
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
          />
        </div>
        <div className="flex items-center gap-3">
          <button className="relative p-2 rounded-full hover:bg-gray-100">
            <Bell size={20} className="text-gray-600" />
            <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></span>
          </button>
          <button className="flex items-center gap-2 bg-green-500 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-600">
            <Download size={16} />
            Descargar Reporte
          </button>
        </div>
      </div>

      {/* ==================================================== */}
      {/* TÍTULO + BOTÓN EXPORTAR */}
      {/* ==================================================== */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Alertas HACCP</h1>
          <p className="text-sm text-gray-500">Gestión y resolución de desviaciones de temperatura.</p>
        </div>
        <button className="flex items-center gap-2 bg-green-500 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-green-600">
          <Download size={16} />
          Exportar Reporte
        </button>
      </div>

      {/* ==================================================== */}
      {/* KPIs */}
      {/* ==================================================== */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        <div className="bg-white p-6 rounded-lg shadow-md">
          <p className="text-xs text-gray-500 font-medium uppercase">Alertas Activas</p>
          <div className="flex items-center justify-between mt-2">
            <p className="text-4xl font-bold text-red-600">{activas || 12}</p>
            <div className="p-3 bg-red-50 rounded-lg">
              <AlertTriangle size={24} className="text-red-600" />
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-md">
          <p className="text-xs text-gray-500 font-medium uppercase">Reconocidas</p>
          <div className="flex items-center justify-between mt-2">
            <p className="text-4xl font-bold text-yellow-600">{reconocidas || 5}</p>
            <div className="p-3 bg-yellow-50 rounded-lg">
              <Eye size={24} className="text-yellow-600" />
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-md">
          <p className="text-xs text-gray-500 font-medium uppercase">Resueltas (24h)</p>
          <div className="flex items-center justify-between mt-2">
            <p className="text-4xl font-bold text-green-600">{resueltas24h || 34}</p>
            <div className="p-3 bg-green-50 rounded-lg">
              <CheckCircle2 size={24} className="text-green-600" />
            </div>
          </div>
        </div>
      </div>

      {/* ==================================================== */}
      {/* FILTROS */}
      {/* ==================================================== */}
      <div className="bg-white p-4 rounded-lg shadow-md mb-6 flex flex-wrap items-center gap-3">
        <select
          value={filtros.camara}
          onChange={(e) => setFiltros({ ...filtros, camara: e.target.value })}
          className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm"
        >
          <option value="">Todas las Cámaras</option>
          <option value="camara-01">Cámara Congelación 01</option>
          <option value="camara-02">Cámara Conservación 02</option>
          <option value="tunel-01">Túnel de Enfriamiento</option>
        </select>

        <select
          value={filtros.estado}
          onChange={(e) => setFiltros({ ...filtros, estado: e.target.value })}
          className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm"
        >
          <option value="">Todos los Estados</option>
          <option value="activa">Activa</option>
          <option value="reconocida">Reconocida</option>
          <option value="resuelta">Resuelta</option>
        </select>

        <select
          value={filtros.severidad}
          onChange={(e) => setFiltros({ ...filtros, severidad: e.target.value })}
          className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm"
        >
          <option value="">Cualquier Severidad</option>
          <option value="critica">Crítica</option>
          <option value="advertencia">Advertencia</option>
        </select>

        <button className="flex items-center gap-2 px-4 py-1.5 border border-gray-200 rounded-lg text-sm text-gray-600 hover:bg-gray-50">
          <Filter size={16} />
          Filtrar
        </button>
      </div>

      {/* ==================================================== */}
      {/* TABLA DE ALERTAS */}
      {/* ==================================================== */}
      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        {loading ? (
          <p className="p-6 text-sm text-gray-500">Cargando alertas...</p>
        ) : listaFiltrada.length === 0 ? (
          <p className="p-6 text-sm text-gray-500">No hay alertas para los filtros seleccionados.</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr className="text-left text-gray-500 uppercase text-xs">
                <th className="px-4 py-3 font-medium">ID</th>
                <th className="px-4 py-3 font-medium">Cámara</th>
                <th className="px-4 py-3 font-medium">Fecha / Hora</th>
                <th className="px-4 py-3 font-medium">Mensaje</th>
                <th className="px-4 py-3 font-medium">Severidad</th>
                <th className="px-4 py-3 font-medium">Estado</th>
                <th className="px-4 py-3 font-medium">Historial / Auditoría</th>
                <th className="px-4 py-3 font-medium">Acción</th>
              </tr>
            </thead>
            <tbody>
              {listaFiltrada.map((a) => {
                const sev = severidadConfig[a.severidad] || severidadConfig.baja;
                const est = estadoConfig[a.estado] || estadoConfig.activa;
                const IconSev = sev.icon;

                return (
                  <tr
                    key={a.id}
                    className={`border-t border-gray-100 ${
                      a.estado === 'activa' && a.severidad === 'critica'
                        ? 'bg-red-50/30'
                        : a.estado === 'activa' && a.severidad === 'advertencia'
                        ? 'bg-yellow-50/30'
                        : ''
                    }`}
                  >
                    <td className="px-4 py-3 font-mono text-xs text-gray-500">{a.id}</td>
                    <td className="px-4 py-3">
                      <p className="font-medium text-gray-800">{a.camara}</p>
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-xs">
                      {new Date(a.timestamp).toLocaleDateString('es-CL')}
                      <br />
                      {new Date(a.timestamp).toLocaleTimeString('es-CL', { hour: '2-digit', minute: '2-digit' })}
                    </td>
                    <td className="px-4 py-3 text-gray-700 max-w-xs">{a.mensaje}</td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center gap-1 text-${sev.color}-600 font-medium`}>
                        <IconSev size={14} />
                        {sev.label}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <Badge color={est.color}>{est.label}</Badge>
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-500">
                      {a.auditoria ? (
                        <div className="space-y-1">
                          {a.auditoria.reconocida_por && (
                            <p>
                              <span className="text-gray-400">Reconocida:</span>{' '}
                              <span className="text-gray-700">{a.auditoria.reconocida_por}</span>
                              <br />
                              <span className="text-gray-400">
                                {new Date(a.auditoria.fecha_reconocida).toLocaleString('es-CL')}
                              </span>
                            </p>
                          )}
                          {a.auditoria.resuelta_por && (
                            <p>
                              <span className="text-gray-400">Resuelta:</span>{' '}
                              <span className="text-gray-700">{a.auditoria.resuelta_por}</span>
                              <br />
                              <span className="text-gray-400">
                                {new Date(a.auditoria.fecha_resuelta).toLocaleString('es-CL')}
                              </span>
                            </p>
                          )}
                        </div>
                      ) : (
                        <span className="text-gray-300 italic">Sin registros</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {canManage ? (
                        <div className="flex items-center gap-2">
                          {a.estado === 'activa' && (
                            <button
                              disabled={actionLoadingId === a.id}
                              onClick={() => handleAccion(a.id, 'reconocer')}
                              className="p-1.5 rounded-lg bg-green-50 text-green-600 hover:bg-green-100"
                              title="Reconocer"
                            >
                              <Check size={16} />
                            </button>
                          )}
                          {a.estado === 'reconocida' && (
                            <button
                              disabled={actionLoadingId === a.id}
                              onClick={() => handleAccion(a.id, 'resolver')}
                              className="p-1.5 rounded-lg bg-green-50 text-green-600 hover:bg-green-100"
                              title="Resolver"
                            >
                              <CheckCircle2 size={16} />
                            </button>
                          )}
                          <button
                            className="p-1.5 rounded-lg bg-gray-50 text-gray-600 hover:bg-gray-100"
                            title="Ver detalle"
                          >
                            <Eye size={16} />
                          </button>
                        </div>
                      ) : (
                        <button
                          className="p-1.5 rounded-lg bg-gray-50 text-gray-600 hover:bg-gray-100"
                          title="Ver detalle"
                        >
                          <Eye size={16} />
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

export default AlertasView;