import React, { useState } from 'react';
import { CheckCircle2, Filter, ThermometerSnowflake } from 'lucide-react';
import Badge from '../ui/Badge';
import { useFetch } from '../../hooks/useApi';
import { getAlertas, reconocerAlerta, resolverAlerta } from '../../api/alertas';
import { formatDate } from '../../utils/formatters';

const MOCK_ALERTAS = [
  { id: 1, camara: 'Cámara Principal 01', temperatura: 5.8, severidad: 'alta', estado: 'activa', timestamp: new Date().toISOString() },
  { id: 2, camara: 'Cámara Principal 02', temperatura: 4.2, severidad: 'media', estado: 'reconocida', timestamp: new Date(Date.now() - 3600e3).toISOString() },
  { id: 3, camara: 'Cámara Secundaria 01', temperatura: 3.1, severidad: 'baja', estado: 'resuelta', timestamp: new Date(Date.now() - 7200e3).toISOString() },
];

const severidadColor = { alta: 'red', media: 'yellow', baja: 'blue' };
const estadoColor = { activa: 'red', reconocida: 'yellow', resuelta: 'green' };

// canManage=true habilita "Reconocer" / "Resolver" (solo rol Técnico, CU-06).
const AlertasView = ({ canManage = false }) => {
  const [filtros, setFiltros] = useState({ camara: '', severidad: '', estado: '' });
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
      // El backend puede no estar disponible aún; igual refrescamos la vista.
    } finally {
      setActionLoadingId(null);
      reload();
    }
  };

  const lista = alertas || [];
  const activas = lista.filter((a) => a.estado === 'activa').length;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Alertas HACCP</h1>
          <p className="text-sm text-gray-500">
            {activas} alerta{activas !== 1 ? 's' : ''} activa{activas !== 1 ? 's' : ''} de {lista.length} registradas
          </p>
        </div>
        {isFallback && (
          <span className="text-xs text-yellow-600 bg-yellow-50 px-3 py-1 rounded-full">
            Mostrando datos de ejemplo (sin conexión con la API)
          </span>
        )}
      </div>

      <div className="bg-white p-4 rounded-lg shadow-md mb-6 flex flex-wrap items-center gap-3">
        <Filter size={16} className="text-gray-400" />
        <input
          type="text"
          placeholder="Filtrar por cámara..."
          value={filtros.camara}
          onChange={(e) => setFiltros({ ...filtros, camara: e.target.value })}
          className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
        />
        <select
          value={filtros.severidad}
          onChange={(e) => setFiltros({ ...filtros, severidad: e.target.value })}
          className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm"
        >
          <option value="">Todas las severidades</option>
          <option value="alta">Alta</option>
          <option value="media">Media</option>
          <option value="baja">Baja</option>
        </select>
        <select
          value={filtros.estado}
          onChange={(e) => setFiltros({ ...filtros, estado: e.target.value })}
          className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm"
        >
          <option value="">Todos los estados</option>
          <option value="activa">Activa</option>
          <option value="reconocida">Reconocida</option>
          <option value="resuelta">Resuelta</option>
        </select>
      </div>

      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        {loading ? (
          <p className="p-6 text-sm text-gray-500">Cargando alertas...</p>
        ) : lista.length === 0 ? (
          <p className="p-6 text-sm text-gray-500">No hay alertas para los filtros seleccionados.</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr className="text-left text-gray-500">
                <th className="px-6 py-3 font-medium">Cámara</th>
                <th className="px-6 py-3 font-medium">Temp.</th>
                <th className="px-6 py-3 font-medium">Severidad</th>
                <th className="px-6 py-3 font-medium">Estado</th>
                <th className="px-6 py-3 font-medium">Fecha</th>
                {canManage && <th className="px-6 py-3 font-medium">Acciones</th>}
              </tr>
            </thead>
            <tbody>
              {lista.map((a) => (
                <tr key={a.id} className="border-t border-gray-100">
                  <td className="px-6 py-3 flex items-center gap-2">
                    <ThermometerSnowflake size={16} className="text-gray-400" />
                    {a.camara}
                  </td>
                  <td className="px-6 py-3">{a.temperatura}°C</td>
                  <td className="px-6 py-3"><Badge color={severidadColor[a.severidad]}>{a.severidad}</Badge></td>
                  <td className="px-6 py-3"><Badge color={estadoColor[a.estado]}>{a.estado}</Badge></td>
                  <td className="px-6 py-3 text-gray-500">{formatDate(a.timestamp)}</td>
                  {canManage && (
                    <td className="px-6 py-3">
                      {a.estado === 'activa' && (
                        <button
                          disabled={actionLoadingId === a.id}
                          onClick={() => handleAccion(a.id, 'reconocer')}
                          className="text-xs px-3 py-1 rounded-lg bg-yellow-50 text-yellow-700 hover:bg-yellow-100"
                        >
                          Reconocer
                        </button>
                      )}
                      {a.estado === 'reconocida' && (
                        <button
                          disabled={actionLoadingId === a.id}
                          onClick={() => handleAccion(a.id, 'resolver')}
                          className="text-xs px-3 py-1 rounded-lg bg-green-50 text-green-700 hover:bg-green-100"
                        >
                          Resolver
                        </button>
                      )}
                      {a.estado === 'resuelta' && (
                        <span className="text-xs text-gray-400 flex items-center gap-1">
                          <CheckCircle2 size={14} /> Cerrada
                        </span>
                      )}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

export default AlertasView;
