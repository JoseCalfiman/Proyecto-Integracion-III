import React, { useState } from 'react';
import { Download, Calendar, Filter } from 'lucide-react';
import { useFetch } from '../../hooks/useApi';
import { getHistorial, exportarHistorial } from '../../api/historial';
import { formatDate } from '../../utils/formatters';

const MOCK_HISTORIAL = Array.from({ length: 8 }).map((_, i) => ({
  id: i + 1,
  camara: i % 2 === 0 ? 'Cámara Principal 01' : 'Cámara Principal 02',
  temperatura: (Math.random() * 6 - 2).toFixed(1),
  consumo_kw: (1 + Math.random()).toFixed(2),
  timestamp: new Date(Date.now() - i * 3600e3).toISOString(),
}));

// Historial de mediciones (CU-14) + exportación de reportes (CU-15).
const HistorialView = ({ canExport = true }) => {
  const [filtros, setFiltros] = useState({ camara: '', desde: '', hasta: '' });
  const { data: registros, loading, isFallback } = useFetch(
    () => getHistorial(filtros),
    [filtros.camara, filtros.desde, filtros.hasta],
    MOCK_HISTORIAL
  );
  const [exportando, setExportando] = useState(false);

  const descargarBlob = (blob, filename) => {
    const url = window.URL.createObjectURL(new Blob([blob]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    link.remove();
  };

  const handleExportar = async (formato) => {
    setExportando(true);
    try {
      const blob = await exportarHistorial(formato, filtros);
      descargarBlob(blob, `historial.${formato}`);
    } catch (err) {
      alert('No se pudo exportar el reporte: el servicio aún no está disponible.');
    } finally {
      setExportando(false);
    }
  };

  const lista = registros || [];

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Historial y Reportes</h1>
          <p className="text-sm text-gray-500">Mediciones de temperatura y consumo eléctrico</p>
        </div>
        {isFallback && (
          <span className="text-xs text-yellow-600 bg-yellow-50 px-3 py-1 rounded-full">
            Mostrando datos de ejemplo (sin conexión con la API)
          </span>
        )}
      </div>

      <div className="bg-white p-4 rounded-lg shadow-md mb-6 flex flex-wrap items-end gap-3">
        <div className="flex items-center gap-2">
          <Filter size={16} className="text-gray-400" />
          <input
            type="text" placeholder="Cámara..."
            value={filtros.camara}
            onChange={(e) => setFiltros({ ...filtros, camara: e.target.value })}
            className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm"
          />
        </div>
        <div className="flex items-center gap-2">
          <Calendar size={16} className="text-gray-400" />
          <input type="date" value={filtros.desde} onChange={(e) => setFiltros({ ...filtros, desde: e.target.value })}
            className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm" />
          <span className="text-gray-400 text-sm">a</span>
          <input type="date" value={filtros.hasta} onChange={(e) => setFiltros({ ...filtros, hasta: e.target.value })}
            className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm" />
        </div>
        {canExport && (
          <div className="ml-auto flex gap-2">
            <button disabled={exportando} onClick={() => handleExportar('csv')}
              className="flex items-center gap-1 text-xs px-3 py-2 rounded-lg border border-gray-200 hover:bg-gray-50">
              <Download size={14} /> CSV
            </button>
            <button disabled={exportando} onClick={() => handleExportar('pdf')}
              className="flex items-center gap-1 text-xs px-3 py-2 rounded-lg border border-gray-200 hover:bg-gray-50">
              <Download size={14} /> PDF
            </button>
          </div>
        )}
      </div>

      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        {loading ? (
          <p className="p-6 text-sm text-gray-500">Cargando historial...</p>
        ) : lista.length === 0 ? (
          <p className="p-6 text-sm text-gray-500">No se encontraron datos en el período seleccionado.</p>
        ) : (
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr className="text-left text-gray-500">
                <th className="px-6 py-3 font-medium">Cámara</th>
                <th className="px-6 py-3 font-medium">Temperatura</th>
                <th className="px-6 py-3 font-medium">Consumo</th>
                <th className="px-6 py-3 font-medium">Fecha</th>
              </tr>
            </thead>
            <tbody>
              {lista.map((r) => (
                <tr key={r.id} className="border-t border-gray-100">
                  <td className="px-6 py-3">{r.camara}</td>
                  <td className="px-6 py-3">{r.temperatura}°C</td>
                  <td className="px-6 py-3">{r.consumo_kw} kW</td>
                  <td className="px-6 py-3 text-gray-500">{formatDate(r.timestamp)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};

export default HistorialView;
