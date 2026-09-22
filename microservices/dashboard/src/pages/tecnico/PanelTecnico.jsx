import React, { useState } from 'react';
import { Wrench, RefreshCw, Server, CheckCircle2, XCircle, AlertTriangle } from 'lucide-react';

const MOCK_SERVICIOS = [
  { nombre: 'Ingesta (FastAPI)', estado: 'ok', ultima_verificacion: 'hace 5s' },
  { nombre: 'Worker Predictivo', estado: 'ok', ultima_verificacion: 'hace 8s' },
  { nombre: 'Worker HACCP', estado: 'ok', ultima_verificacion: 'hace 8s' },
  { nombre: 'Worker Optimización', estado: 'advertencia', ultima_verificacion: 'hace 6h' },
  { nombre: 'Broker Mosquitto', estado: 'ok', ultima_verificacion: 'hace 3s' },
  { nombre: 'Kafka', estado: 'ok', ultima_verificacion: 'hace 3s' },
];

const estadoInfo = {
  ok: { icon: CheckCircle2, color: 'text-green-600 bg-green-50', label: 'Operativo' },
  advertencia: { icon: AlertTriangle, color: 'text-yellow-600 bg-yellow-50', label: 'Advertencia' },
  caido: { icon: XCircle, color: 'text-red-600 bg-red-50', label: 'Caído' },
};

// Panel Técnico (SOLO TÉCNICO) — herramientas de mantenimiento y diagnóstico.
// Cada microservicio expone /health (RNF-tolerancia a fallos); esta vista
// resume ese estado y ofrece acciones operativas rápidas.
const PanelTecnico = () => {
  const [servicios, setServicios] = useState(MOCK_SERVICIOS);
  const [verificando, setVerificando] = useState(false);

  const verificarSalud = async () => {
    setVerificando(true);
    // En producción: GET /health de cada microservicio.
    await new Promise((r) => setTimeout(r, 800));
    setServicios((s) => s.map((srv) => ({ ...srv, ultima_verificacion: 'hace 1s' })));
    setVerificando(false);
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Panel Técnico</h1>
          <p className="text-sm text-gray-500">Herramientas de mantenimiento y diagnóstico del sistema</p>
        </div>
        <button onClick={verificarSalud} disabled={verificando}
          className="flex items-center gap-2 text-sm px-4 py-2 rounded-lg border border-gray-200 hover:bg-gray-50">
          <RefreshCw size={16} className={verificando ? 'animate-spin' : ''} /> Verificar salud
        </button>
      </div>

      <div className="bg-white rounded-lg shadow-md overflow-hidden mb-6">
        <div className="px-6 py-4 border-b border-gray-100 flex items-center gap-2">
          <Server size={18} className="text-gray-500" />
          <h2 className="text-lg font-semibold text-gray-700">Estado de microservicios</h2>
        </div>
        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr className="text-left text-gray-500">
              <th className="px-6 py-3 font-medium">Servicio</th>
              <th className="px-6 py-3 font-medium">Estado</th>
              <th className="px-6 py-3 font-medium">Última verificación</th>
            </tr>
          </thead>
          <tbody>
            {servicios.map((s) => {
              const info = estadoInfo[s.estado];
              const Icon = info.icon;
              return (
                <tr key={s.nombre} className="border-t border-gray-100">
                  <td className="px-6 py-3">{s.nombre}</td>
                  <td className="px-6 py-3">
                    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs ${info.color}`}>
                      <Icon size={12} /> {info.label}
                    </span>
                  </td>
                  <td className="px-6 py-3 text-gray-500">{s.ultima_verificacion}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="bg-white p-6 rounded-lg shadow-md">
        <div className="flex items-center gap-2 mb-4">
          <Wrench size={18} className="text-gray-500" />
          <h2 className="text-lg font-semibold text-gray-700">Acciones de mantenimiento</h2>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <button className="text-sm text-left px-4 py-3 rounded-lg border border-gray-200 hover:bg-gray-50">
            Reintentar reconexión MQTT (Mosquitto)
          </button>
          <button className="text-sm text-left px-4 py-3 rounded-lg border border-gray-200 hover:bg-gray-50">
            Forzar recálculo del Worker de Optimización
          </button>
          <button className="text-sm text-left px-4 py-3 rounded-lg border border-gray-200 hover:bg-gray-50">
            Ver logs de ingesta recientes
          </button>
          <button className="text-sm text-left px-4 py-3 rounded-lg border border-gray-200 hover:bg-gray-50">
            Actualizar manualmente precio de energía (CNE)
          </button>
        </div>
      </div>
    </div>
  );
};

export default PanelTecnico;
