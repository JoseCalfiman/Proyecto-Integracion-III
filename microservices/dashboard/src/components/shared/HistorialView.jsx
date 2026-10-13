import React, { useState } from 'react';
import {
  Download, Calendar, Filter, Search, Bell, HelpCircle, User,
  TrendingUp, AlertTriangle, Clock, Eye, CheckCircle2, MoreVertical,
} from 'lucide-react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ReferenceLine, ResponsiveContainer,
} from 'recharts';
import { useFetch } from '../../hooks/useApi';
import { getHistorial, exportarHistorial } from '../../api/historial';
import { formatDate } from '../../utils/formatters';

// ============================================================
// DATOS MOCK (basados en el MER: tabla predictions)
// ============================================================
const MOCK_PREDICCIONES = [
  {
    id_prediction: 1,
    camara: 'Cámara Principal 01',
    calculated_slope: 0.4,
    projected_temperature: -18.2,
    remaining_time_min: 145,
    risk_level: 'low',
    calculation_date: '2023-10-07T14:32:00',
    id_worker: 'worker-predictivo-1',
  },
  {
    id_prediction: 2,
    camara: 'Túnel de Congelación A',
    calculated_slope: 1.8,
    projected_temperature: -12.5,
    remaining_time_min: 42,
    risk_level: 'medium',
    calculation_date: '2023-10-07T11:15:00',
    id_worker: 'worker-predictivo-1',
  },
  {
    id_prediction: 3,
    camara: 'Cámara Pre-frío 02',
    calculated_slope: 4.2,
    projected_temperature: -4.8,
    remaining_time_min: 12,
    risk_level: 'critical',
    calculation_date: '2023-10-06T23:45:00',
    id_worker: 'worker-predictivo-1',
  },
  {
    id_prediction: 4,
    camara: 'Cámara Principal 01',
    calculated_slope: 0.2,
    projected_temperature: -19.1,
    remaining_time_min: 180,
    risk_level: 'low',
    calculation_date: '2023-10-06T18:20:00',
    id_worker: 'worker-predictivo-1',
  },
];

// ============================================================
// CONFIGURACIÓN DE NIVELES DE RIESGO
// ============================================================
const riesgoConfig = {
  low: { label: 'Bajo', color: 'green' },
  medium: { label: 'Medio', color: 'yellow' },
  high: { label: 'Alto', color: 'orange' },
  critical: { label: 'Crítico', color: 'red' },
};

// ============================================================
// DATOS PARA EL GRÁFICO DE TENDENCIAS
// ============================================================
const MOCK_TENDENCIAS = [
  { dia: 'Lun', tiempo_restante: 180 },
  { dia: 'Mar', tiempo_restante: 150 },
  { dia: 'Mié', tiempo_restante: 120 },
  { dia: 'Jue', tiempo_restante: 145 },
  { dia: 'Vie', tiempo_restante: 160 },
  { dia: 'Sáb', tiempo_restante: 45 },
  { dia: 'Dom', tiempo_restante: 30 },
];

// ============================================================
// COMPONENTE
// ============================================================
const HistorialView = ({ canExport = true }) => {
  const [filtros, setFiltros] = useState({ camara: '', desde: '', hasta: '' });
  const { data: predicciones, loading, isFallback } = useFetch(
    () => getHistorial(filtros),
    [filtros.camara, filtros.desde, filtros.hasta],
    MOCK_PREDICCIONES
  );
  const [exportando, setExportando] = useState(false);

  const lista = Array.isArray(predicciones) ? predicciones : [];

  // ============================================================
  // KPIs (calculados desde la lista)
  // ============================================================
  const totalPredicciones = lista.length;
  const prediccionesCriticas = lista.filter(
    (p) => p.risk_level === 'critical' || p.risk_level === 'high'
  ).length;
  const tiempoPromedio =
    totalPredicciones > 0
      ? Math.round(
          lista.reduce((acc, p) => acc + (p.remaining_time_min || 0), 0) / totalPredicciones
        )
      : 0;
  const precisionModelo = 94.2; // Mock (vendría del backend)

  // ============================================================
  // EXPORTAR
  // ============================================================
  const handleExportar = async (formato) => {
    setExportando(true);
    try {
      const blob = await exportarHistorial(formato, filtros);
      const url = window.URL.createObjectURL(new Blob([blob]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `historial-predicciones.${formato}`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      alert('No se pudo exportar el reporte: el servicio aún no está disponible.');
    } finally {
      setExportando(false);
    }
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
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-800">Historial de Predicciones</h1>
        <p className="text-sm text-gray-500">
          Consulte el registro histórico de proyecciones y estimaciones de tiempo límite HACCP.
        </p>
      </div>

      {isFallback && (
        <div className="text-xs text-yellow-600 bg-yellow-50 px-3 py-2 rounded-lg mb-4 inline-block">
          Mostrando datos de ejemplo (sin conexión con la API)
        </div>
      )}

      {/* ==================================================== */}
      {/* FILTROS */}
      {/* ==================================================== */}
      <div className="bg-white p-4 rounded-lg shadow-md mb-6 flex flex-wrap items-end gap-4">
        <div className="flex-1 min-w-[200px]">
          <label className="block text-xs text-gray-500 mb-1">Seleccionar Cámara</label>
          <select
            value={filtros.camara}
            onChange={(e) => setFiltros({ ...filtros, camara: e.target.value })}
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm"
          >
            <option value="">Cámara Principal 01</option>
            <option value="camara-02">Cámara Principal 02</option>
            <option value="tunel-01">Túnel de Congelación A</option>
            <option value="prefrio-02">Cámara Pre-frío 02</option>
          </select>
        </div>

        <div className="flex-1 min-w-[280px]">
          <label className="block text-xs text-gray-500 mb-1">Rango de Fechas</label>
          <div className="flex items-center gap-2">
            <div className="relative flex-1">
              <Calendar size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="date"
                value={filtros.desde}
                onChange={(e) => setFiltros({ ...filtros, desde: e.target.value })}
                className="w-full pl-9 pr-3 py-2 border border-gray-200 rounded-lg text-sm"
              />
            </div>
            <span className="text-gray-400">-</span>
            <div className="relative flex-1">
              <Calendar size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="date"
                value={filtros.hasta}
                onChange={(e) => setFiltros({ ...filtros, hasta: e.target.value })}
                className="w-full pl-9 pr-3 py-2 border border-gray-200 rounded-lg text-sm"
              />
            </div>
          </div>
        </div>

        <button className="flex items-center gap-2 bg-gray-100 hover:bg-gray-200 text-gray-700 px-4 py-2 rounded-lg text-sm font-medium">
          <Filter size={16} />
          Aplicar
        </button>
      </div>

      {/* ==================================================== */}
      {/* KPIs */}
      {/* ==================================================== */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        <div className="bg-white p-6 rounded-lg shadow-md border-l-4 border-green-500">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp size={16} className="text-green-600" />
            <p className="text-xs text-gray-500 font-medium uppercase">Precisión del Modelo</p>
          </div>
          <p className="text-3xl font-bold text-gray-800">{precisionModelo}%</p>
          <p className="text-xs text-green-600 mt-1">↗ +1.2% este mes</p>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-md border-l-4 border-red-500">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle size={16} className="text-red-600" />
            <p className="text-xs text-gray-500 font-medium uppercase">Predicciones Críticas</p>
          </div>
          <p className="text-3xl font-bold text-gray-800">{prediccionesCriticas}</p>
          <p className="text-xs text-gray-500 mt-1">Total en el período seleccionado</p>
        </div>

        <div className="bg-white p-6 rounded-lg shadow-md border-l-4 border-yellow-500">
          <div className="flex items-center gap-2 mb-2">
            <Clock size={16} className="text-yellow-600" />
            <p className="text-xs text-gray-500 font-medium uppercase">T. de Respuesta Promedio</p>
          </div>
          <p className="text-3xl font-bold text-gray-800">{tiempoPromedio}m</p>
          <p className="text-xs text-gray-500 mt-1">Tiempo para acción correctiva</p>
        </div>
      </div>

      {/* ==================================================== */}
      {/* GRÁFICO DE TENDENCIAS */}
      {/* ==================================================== */}
      <div className="bg-white p-6 rounded-lg shadow-md mb-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-lg font-semibold text-gray-800">Tendencias de Tiempo Estimado</h2>
            <p className="text-xs text-gray-500">
              Tiempo estimado hasta límite HACCP (minutos) a lo largo del tiempo
            </p>
          </div>
          <button className="p-2 rounded-lg hover:bg-gray-100">
            <MoreVertical size={16} className="text-gray-400" />
          </button>
        </div>

        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={MOCK_TENDENCIAS}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis dataKey="dia" stroke="#9ca3af" tick={{ fontSize: 11 }} />
            <YAxis
              stroke="#9ca3af"
              tick={{ fontSize: 11 }}
              label={{ value: 'minutos', angle: -90, position: 'insideLeft', fontSize: 11 }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#fff',
                border: '1px solid #e5e7eb',
                borderRadius: '8px',
                fontSize: '12px',
              }}
              formatter={(value) => [`${value} min`, 'Tiempo restante']}
            />
            <ReferenceLine y={40} stroke="#ef4444" strokeDasharray="5 5" strokeWidth={1.5} />
            <Line
              type="monotone"
              dataKey="tiempo_restante"
              stroke="#10b981"
              strokeWidth={2.5}
              dot={false}
              activeDot={{ r: 5 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* ==================================================== */}
      {/* REGISTRO DETALLADO */}
      {/* ==================================================== */}
      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <h2 className="font-semibold text-gray-800">Registro Detallado</h2>
          {canExport && (
            <div className="flex gap-2">
              <button
                disabled={exportando}
                onClick={() => handleExportar('csv')}
                className="flex items-center gap-1 text-xs px-3 py-1.5 rounded-lg border border-gray-200 hover:bg-gray-50"
              >
                <Download size={14} /> CSV
              </button>
              <button
                disabled={exportando}
                onClick={() => handleExportar('pdf')}
                className="flex items-center gap-1 text-xs px-3 py-1.5 rounded-lg border border-gray-200 hover:bg-gray-50"
              >
                <Download size={14} /> PDF
              </button>
            </div>
          )}
        </div>

        {loading ? (
          <p className="p-6 text-sm text-gray-500">Cargando predicciones...</p>
        ) : lista.length === 0 ? (
          <p className="p-6 text-sm text-gray-500">No hay predicciones registradas.</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr className="text-left text-gray-500 uppercase text-xs">
                <th className="px-6 py-3 font-medium">Fecha / Hora</th>
                <th className="px-6 py-3 font-medium">Cámara</th>
                <th className="px-6 py-3 font-medium">Pendiente (°C/h)</th>
                <th className="px-6 py-3 font-medium">Temp. Proyectada (°C)</th>
                <th className="px-6 py-3 font-medium">Tiempo Restante (min)</th>
                <th className="px-6 py-3 font-medium">Nivel de Riesgo</th>
                <th className="px-6 py-3 font-medium">Sincronización</th>
                <th className="px-6 py-3 font-medium">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {lista.map((p) => {
                const riesgo = riesgoConfig[p.risk_level] || riesgoConfig.low;

                return (
                  <tr key={p.id_prediction} className="border-t border-gray-100 hover:bg-gray-50">
                    <td className="px-6 py-3 text-gray-500 text-xs">
                      {new Date(p.calculation_date).toLocaleDateString('es-CL', {
                        day: '2-digit',
                        month: '2-digit',
                        year: '2-digit',
                      })}
                      <br />
                      {new Date(p.calculation_date).toLocaleTimeString('es-CL', {
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </td>
                    <td className="px-6 py-3 font-medium text-gray-800">{p.camara}</td>
                    <td className="px-6 py-3 text-gray-700">+{p.calculated_slope}</td>
                    <td className="px-6 py-3 text-gray-700">{p.projected_temperature}</td>
                    <td className="px-6 py-3 font-semibold text-gray-800">
                      {p.remaining_time_min}
                    </td>
                    <td className="px-6 py-3">
                      <span
                        className={`text-xs font-medium px-2 py-1 rounded ${
                          riesgo.color === 'green'
                            ? 'bg-green-100 text-green-700'
                            : riesgo.color === 'yellow'
                            ? 'bg-yellow-100 text-yellow-700'
                            : riesgo.color === 'orange'
                            ? 'bg-orange-100 text-orange-700'
                            : 'bg-red-100 text-red-700'
                        }`}
                      >
                        {riesgo.label}
                      </span>
                    </td>
                    <td className="px-6 py-3">
                      <span className="inline-flex items-center gap-1 text-xs text-green-600">
                        <CheckCircle2 size={14} />
                        Publicado
                      </span>
                    </td>
                    <td className="px-6 py-3">
                      <button className="p-1.5 rounded-lg hover:bg-gray-100" title="Ver detalle">
                        <Eye size={14} className="text-gray-500" />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}

        {/* Footer con contador */}
        <div className="flex items-center justify-between px-6 py-3 border-t border-gray-100 text-xs text-gray-500">
          <span>
            Mostrando {lista.length} de {lista.length} registros
          </span>
          <div className="flex gap-2">
            <button className="px-3 py-1 rounded border border-gray-200 hover:bg-gray-50 disabled:opacity-50" disabled>
              Anterior
            </button>
            <button className="px-3 py-1 rounded border border-gray-200 hover:bg-gray-50">
              Siguiente
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default HistorialView;