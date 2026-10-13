import React, { useState } from 'react';
import {
  Wrench, RefreshCw, Server, CheckCircle2, XCircle, AlertTriangle,
  Wifi, WifiOff, Thermometer, Droplet, DoorOpen,
  Bell, HelpCircle, Download, User, MoreVertical,
  Eye,
} from 'lucide-react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import { useFetch } from '../../hooks/useApi';
import {
  getGateways, getAlertasSistema, getTraficoRed,
  getSensores, verificarSalud,
} from '../../api/panelTecnico';

// ============================================================
// DATOS MOCK (fallback mientras Diego no tenga los endpoints)
// ============================================================
const MOCK_GATEWAYS = [
  { id: 'GTW-NORTE-01', nombre: 'Cámara Principal 01', estado: 'online', ping_ms: 12 },
  { id: 'SN-902', nombre: 'Cámara Congelación', estado: 'offline', ultima_conexion: 'Hace 42m' },
  { id: 'GTW-SUR-03', nombre: 'Túnel de Enfriamiento', estado: 'online', ping_ms: 18 },
];

const MOCK_ALERTAS = [
  { id: 1, tipo: 'critica', codigo: 'CRITICAL', mensaje: 'Gateway SN-902 offline. Fallo de heartbeat.', fecha: '10:42 AM' },
  { id: 2, tipo: 'advertencia', codigo: 'WARNING', mensaje: 'Sensor SN-102 (Cámara 4) calibración vencida hace 3 días.', fecha: '09:15 AM' },
  { id: 3, tipo: 'info', codigo: 'INFO', mensaje: 'Backup de base de datos completado exitosamente (1.2GB).', fecha: '03:00 AM' },
  { id: 4, tipo: 'advertencia', codigo: 'WARNING', mensaje: 'Latencia alta detectada en nodo Edge-02 (>500ms).', fecha: '7:45 PM' },
];

const MOCK_TRAFICO = [
  { hora: '-6h', rx: 120, tx: 80 },
  { hora: '-5h', rx: 180, tx: 120 },
  { hora: '-4h', rx: 240, tx: 160 },
  { hora: '-3h', rx: 200, tx: 140 },
  { hora: '-2h', rx: 280, tx: 190 },
  { hora: '-1h', rx: 260, tx: 170 },
  { hora: 'Ahora', rx: 240, tx: 150 },
];

const MOCK_SENSORES = [
  { id: 'SN-101', ubicacion: 'Cámara Principal A', tipo: 'Temp/Hum', bateria: 98, ultima_lectura: 'Hace 2s', estado: 'ok' },
  { id: 'SN-102', ubicacion: 'Cámara 4 (Congelados)', tipo: 'Temp PT100', bateria: 74, ultima_lectura: 'Hace 1m', estado: 'calibracion' },
  { id: 'SN-103', ubicacion: 'Pre-Cámara Sur', tipo: 'Apertura Puerta', bateria: 32, ultima_lectura: 'Hace 14d', estado: 'ok' },
];

// ============================================================
// CONFIGURACIÓN DE COLORES
// ============================================================
const gatewayConfig = {
  online: { color: 'green', icon: Wifi, label: 'Online' },
  offline: { color: 'red', icon: WifiOff, label: 'Offline' },
};

const alertaConfig = {
  critica: { color: 'red', bg: 'bg-red-50', border: 'border-red-200' },
  advertencia: { color: 'yellow', bg: 'bg-yellow-50', border: 'border-yellow-200' },
  info: { color: 'blue', bg: 'bg-blue-50', border: 'border-blue-200' },
};

const sensorIcono = {
  'Temp/Hum': Thermometer,
  'Temp PT100': Thermometer,
  'Apertura Puerta': DoorOpen,
};

// ============================================================
// COMPONENTE
// ============================================================
const PanelTecnico = () => {
  const [verificando, setVerificando] = useState(false);

  // ==========================================================
  // CARGAR DATOS DESDE LA API
  // ==========================================================
  const { data: gateways } = useFetch(getGateways, [], MOCK_GATEWAYS);
  const { data: alertas } = useFetch(getAlertasSistema, [], MOCK_ALERTAS);
  const { data: trafico } = useFetch(getTraficoRed, [], MOCK_TRAFICO);
  const { data: sensores, reload: reloadSensores } = useFetch(getSensores, [], MOCK_SENSORES);

  const listaGateways = Array.isArray(gateways) ? gateways : [];
  const listaAlertas = Array.isArray(alertas) ? alertas : [];
  const listaSensores = Array.isArray(sensores) ? sensores : [];
  const datosTrafico = Array.isArray(trafico) && trafico.length > 0 ? trafico : MOCK_TRAFICO;

  // ==========================================================
  // VERIFICAR SALUD
  // ==========================================================
  const verificarSaludSistema = async () => {
    setVerificando(true);
    try {
      await verificarSalud();
      reloadSensores();
    } catch (err) {
      alert('No se pudo verificar la salud del sistema.');
    } finally {
      setVerificando(false);
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
        <h1 className="text-2xl font-bold text-gray-800">Panel de Control Técnico</h1>
        <p className="text-sm text-gray-500">Monitoreo de infraestructura y salud del sistema</p>
      </div>

      {/* ==================================================== */}
      {/* SECCIÓN 1: GATEWAYS + ALERTAS */}
      {/* ==================================================== */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        {/* Gateways (2/3) */}
        <div className="lg:col-span-2 bg-white p-6 rounded-lg shadow-md">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Server size={18} className="text-green-600" />
              <h2 className="font-semibold text-gray-800">Estado de Gateways</h2>
            </div>
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1 text-xs text-green-700 bg-green-50 px-3 py-1 rounded-full">
                <CheckCircle2 size={12} />
                98.9% UPTIME
              </span>
              <button
                onClick={verificarSaludSistema}
                disabled={verificando}
                className="p-1.5 rounded-lg hover:bg-gray-100"
              >
                <RefreshCw size={16} className={`text-gray-500 ${verificando ? 'animate-spin' : ''}`} />
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {listaGateways.map((g) => {
              const config = gatewayConfig[g.estado] || gatewayConfig.offline;
              const Icon = config.icon;
              const borderColor = g.estado === 'online' ? 'border-green-200' : 'border-red-200';

              return (
                <div key={g.id} className={`border ${borderColor} rounded-lg p-4`}>
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-mono text-gray-500">{g.id}</span>
                    <Icon
                      size={16}
                      className={g.estado === 'online' ? 'text-green-600' : 'text-red-600'}
                    />
                  </div>
                  <p className="text-sm font-medium text-gray-700 mb-1">{g.nombre}</p>
                  <p
                    className={`text-lg font-bold ${
                      g.estado === 'online' ? 'text-green-600' : 'text-red-600'
                    }`}
                  >
                    {config.label}
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    {g.estado === 'online' ? `${g.ping_ms}ms ping` : g.ultima_conexion}
                  </p>
                </div>
              );
            })}
          </div>
        </div>

        {/* Alertas del sistema (1/3) */}
        <div className="lg:col-span-1 bg-white p-6 rounded-lg shadow-md">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Bell size={18} className="text-yellow-600" />
              <h2 className="font-semibold text-gray-800">Alertas del Sistema</h2>
            </div>
            <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
              {listaAlertas.length} Nuevas
            </span>
          </div>

          <div className="space-y-3">
            {listaAlertas.map((a) => {
              const config = alertaConfig[a.tipo] || alertaConfig.info;
              return (
                <div
                  key={a.id}
                  className={`${config.bg} border ${config.border} rounded-lg p-3`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span
                      className={`text-xs font-bold ${
                        a.tipo === 'critica'
                          ? 'text-red-600'
                          : a.tipo === 'advertencia'
                          ? 'text-yellow-700'
                          : 'text-blue-700'
                      }`}
                    >
                      {a.codigo}
                    </span>
                    <span className="text-xs text-gray-500">{a.fecha}</span>
                  </div>
                  <p className="text-xs text-gray-700">{a.mensaje}</p>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* ==================================================== */}
      {/* SECCIÓN 2: TRÁFICO DE RED + MENÚ DE CALIBRACIÓN */}
      {/* ==================================================== */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        {/* Tráfico de red (2/3) */}
        <div className="lg:col-span-2 bg-white p-6 rounded-lg shadow-md">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-gray-800">Tráfico de Red (Últimas 6H)</h2>
            <div className="flex items-center gap-3 text-xs">
              <div className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-green-500"></span>
                <span className="text-gray-600">RX</span>
              </div>
              <div className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-blue-500"></span>
                <span className="text-gray-600">TX</span>
              </div>
            </div>
          </div>

          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={datosTrafico}>
              <defs>
                <linearGradient id="colorRx" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="colorTx" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="hora" stroke="#9ca3af" tick={{ fontSize: 11 }} />
              <YAxis stroke="#9ca3af" tick={{ fontSize: 11 }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#fff',
                  border: '1px solid #e5e7eb',
                  borderRadius: '8px',
                  fontSize: '12px',
                }}
              />
              <Area
                type="monotone"
                dataKey="rx"
                stroke="#10b981"
                fill="url(#colorRx)"
                strokeWidth={2}
              />
              <Area
                type="monotone"
                dataKey="tx"
                stroke="#3b82f6"
                fill="url(#colorTx)"
                strokeWidth={2}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Menú de calibración (1/3) */}
        <div className="lg:col-span-1 bg-white p-6 rounded-lg shadow-md">
          <div className="flex items-center gap-2 mb-4">
            <Wrench size={18} className="text-green-600" />
            <h2 className="font-semibold text-gray-800">Menú de Calibración</h2>
          </div>

          <div className="space-y-3">
            <button className="w-full flex items-center gap-3 p-3 border border-gray-200 rounded-lg hover:bg-gray-50 text-left">
              <Thermometer size={20} className="text-green-600" />
              <div>
                <p className="text-sm font-medium text-gray-800">Sensores de Temp.</p>
                <p className="text-xs text-gray-500">Calibración de punto cero</p>
              </div>
            </button>

            <button className="w-full flex items-center gap-3 p-3 border border-gray-200 rounded-lg hover:bg-gray-50 text-left">
              <Droplet size={20} className="text-blue-600" />
              <div>
                <p className="text-sm font-medium text-gray-800">Sensores de Humedad</p>
                <p className="text-xs text-gray-500">Ajuste de histéresis</p>
              </div>
            </button>

            <button className="w-full flex items-center gap-3 p-3 border border-gray-200 rounded-lg hover:bg-gray-50 text-left">
              <Server size={20} className="text-gray-600" />
              <div>
                <p className="text-sm font-medium text-gray-800">Microcontroladores</p>
                <p className="text-xs text-gray-500">Revisión y diagnóstico</p>
              </div>
            </button>
          </div>

          <p className="text-xs text-gray-400 mt-4">
            Inicie rutinas de mantenimiento preventivo
          </p>
        </div>
      </div>

      {/* ==================================================== */}
      {/* SECCIÓN 3: INVENTARIO DE SENSORES */}
      {/* ==================================================== */}
      <div className="bg-white rounded-lg shadow-md overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <Thermometer size={18} className="text-green-600" />
            <h2 className="font-semibold text-gray-800">Inventario de Sensores</h2>
          </div>
          <button className="text-xs text-green-600 hover:text-green-700 font-medium">
            Ver Todos
          </button>
        </div>

        <table className="w-full text-sm">
          <thead className="bg-gray-50">
            <tr className="text-left text-gray-500 uppercase text-xs">
              <th className="px-6 py-3 font-medium">ID Sensor</th>
              <th className="px-6 py-3 font-medium">Ubicación</th>
              <th className="px-6 py-3 font-medium">Tipo</th>
              <th className="px-6 py-3 font-medium">Batería</th>
              <th className="px-6 py-3 font-medium">Última Lectura</th>
              <th className="px-6 py-3 font-medium">Acción</th>
            </tr>
          </thead>
          <tbody>
            {listaSensores.map((s) => {
              const IconSensor = sensorIcono[s.tipo] || Thermometer;
              const bateriaColor =
                s.bateria > 70 ? 'bg-green-500' : s.bateria > 40 ? 'bg-yellow-500' : 'bg-red-500';

              return (
                <tr key={s.id} className="border-t border-gray-100 hover:bg-gray-50">
                  <td className="px-6 py-3">
                    <div className="flex items-center gap-2">
                      <span
                        className={`w-2 h-2 rounded-full ${
                          s.estado === 'ok' ? 'bg-green-500' : 'bg-yellow-500'
                        }`}
                      ></span>
                      <span className="font-mono text-xs text-gray-700">{s.id}</span>
                    </div>
                  </td>
                  <td className="px-6 py-3 text-gray-700">
                    <div className="flex items-center gap-2">
                      <IconSensor size={14} className="text-gray-400" />
                      {s.ubicacion}
                    </div>
                  </td>
                  <td className="px-6 py-3">
                    <span className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded">
                      {s.tipo}
                    </span>
                  </td>
                  <td className="px-6 py-3">
                    <div className="flex items-center gap-2">
                      <div className="w-16 bg-gray-200 rounded-full h-1.5">
                        <div
                          className={`h-1.5 rounded-full ${bateriaColor}`}
                          style={{ width: `${s.bateria}%` }}
                        ></div>
                      </div>
                      <span className="text-xs text-gray-600">{s.bateria}%</span>
                    </div>
                  </td>
                  <td className="px-6 py-3 text-xs">
                    {s.estado === 'calibracion' ? (
                      <span className="text-yellow-600 font-medium">
                        ⚠ Calibración requerida
                      </span>
                    ) : (
                      <span className="text-gray-500">{s.ultima_lectura}</span>
                    )}
                  </td>
                  <td className="px-6 py-3">
                    <div className="flex gap-2">
                      <button
                        className="p-1.5 rounded-lg hover:bg-gray-100"
                        title="Ver detalle"
                      >
                        <Eye size={14} className="text-gray-500" />
                      </button>
                      <button
                        className="p-1.5 rounded-lg hover:bg-gray-100"
                        title="Más opciones"
                      >
                        <MoreVertical size={14} className="text-gray-500" />
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default PanelTecnico;