import React, { useState } from 'react';
import { TrendingUp, Download, Lightbulb } from 'lucide-react';
import { useFetch } from '../../hooks/useApi';
import { getRecomendacionesAhorro, exportarReporte } from '../../api/optimizacion';
import { formatCLP } from '../../utils/formatters';

const MOCK_RECOMENDACIONES = [
  { id: 1, accion: 'Apagar compresor auxiliar en horario punta (18:00-23:00)', porcentaje_ahorro: 12.5, monto_clp: 84500, justificacion: 'El consumo histórico muestra que el compresor auxiliar opera sin carga crítica durante horario punta, donde la tarifa eléctrica es más alta.', estado: 'pendiente' },
  { id: 2, accion: 'Ajustar setpoint de Cámara Secundaria 01 de -2°C a -1°C', porcentaje_ahorro: 6.2, monto_clp: 32100, justificacion: 'El margen respecto al límite HACCP permite subir el setpoint sin riesgo, reduciendo ciclos de refrigeración.', estado: 'aplicada' },
  { id: 3, accion: 'Reprogramar deshielo automático a horario de menor demanda', porcentaje_ahorro: 4.8, monto_clp: 21800, justificacion: 'Prophet proyecta menor consumo base entre las 03:00 y 05:00, ideal para concentrar los ciclos de deshielo.', estado: 'pendiente' },
];

// Optimización y Ahorro (SOLO GERENTE) — CU-07 / CU-08 / CU-15.
const Ahorro = () => {
  const { data: recomendaciones, loading, isFallback } = useFetch(getRecomendacionesAhorro, [], MOCK_RECOMENDACIONES);
  const [exportando, setExportando] = useState(false);

  const lista = recomendaciones || [];
  const totalAhorro = lista.reduce((acc, r) => acc + (r.monto_clp || 0), 0);

  const handleExportar = async (formato) => {
    setExportando(true);
    try {
      const blob = await exportarReporte(formato);
      const url = window.URL.createObjectURL(new Blob([blob]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `optimizacion.${formato}`);
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
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Optimización y Ahorro</h1>
          <p className="text-sm text-gray-500">Recomendaciones generadas a partir del consumo histórico (Prophet)</p>
        </div>
        <div className="flex gap-2">
          <button disabled={exportando} onClick={() => handleExportar('csv')}
            className="flex items-center gap-1 text-xs px-3 py-2 rounded-lg border border-gray-200 hover:bg-gray-50">
            <Download size={14} /> CSV
          </button>
          <button disabled={exportando} onClick={() => handleExportar('pdf')}
            className="flex items-center gap-1 text-xs px-3 py-2 rounded-lg border border-gray-200 hover:bg-gray-50">
            <Download size={14} /> PDF
          </button>
        </div>
      </div>

      {isFallback && (
        <div className="text-xs text-yellow-600 bg-yellow-50 px-3 py-2 rounded-lg mb-4 inline-block">
          Mostrando datos de ejemplo (sin conexión con la API)
        </div>
      )}

      <div className="bg-white p-6 rounded-lg shadow-md mb-6 flex items-center gap-4">
        <div className="p-3 rounded-lg bg-green-50 text-green-600">
          <TrendingUp size={24} />
        </div>
        <div>
          <p className="text-xs text-gray-500 uppercase tracking-wide">Ahorro potencial total identificado</p>
          <p className="text-3xl font-bold text-gray-800">{formatCLP(totalAhorro)}</p>
        </div>
      </div>

      {loading ? (
        <p className="text-sm text-gray-500">Cargando recomendaciones...</p>
      ) : lista.length === 0 ? (
        <p className="text-sm text-gray-500">Aún no hay recomendaciones de ahorro disponibles.</p>
      ) : (
        <div className="space-y-4">
          {lista.map((r) => (
            <div key={r.id} className="bg-white p-6 rounded-lg shadow-md">
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-3">
                  <div className="p-2 rounded-lg bg-yellow-50 text-yellow-600 mt-0.5">
                    <Lightbulb size={18} />
                  </div>
                  <div>
                    <p className="font-medium text-gray-800">{r.accion}</p>
                    <p className="text-sm text-gray-500 mt-1">{r.justificacion}</p>
                  </div>
                </div>
                <span className={`text-xs px-2 py-1 rounded-full shrink-0 ${
                  r.estado === 'aplicada' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                }`}>
                  {r.estado === 'aplicada' ? 'Aplicada' : 'Pendiente'}
                </span>
              </div>
              <div className="flex gap-6 mt-4 pl-11 text-sm">
                <div><span className="text-gray-400">Ahorro estimado: </span><span className="font-semibold text-green-600">{r.porcentaje_ahorro}%</span></div>
                <div><span className="text-gray-400">Monto: </span><span className="font-semibold text-gray-800">{formatCLP(r.monto_clp)}</span></div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default Ahorro;
