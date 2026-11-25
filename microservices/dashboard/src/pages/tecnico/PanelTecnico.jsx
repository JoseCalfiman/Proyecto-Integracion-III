import React, { useState } from 'react';
import {
  Activity,
  AlertTriangle,
  Bell,
  HelpCircle,
  RefreshCw,
  Server,
  Thermometer,
  Wifi,
  WifiOff,
} from 'lucide-react';
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { useFetch } from '../../hooks/useApi';
import {
  getAlertasSistema,
  getCamarasTecnico,
  getGateways,
  getSensores,
  getTemperaturasTecnico,
  verificarSalud,
} from '../../api/panelTecnico';
import {
  prepararAlertas,
  prepararCamaras,
  prepararSensores,
  prepararTemperaturas,
} from '../../utils/panelTecnicoReal';
import DiagnosticoCamara from './DiagnosticoCamara';

// A3: datos reales del panel técnico. A4: diagnóstico individual por cámara.
// No se utilizan MOCK_* ni datos de respaldo ficticios.
// IMPORTANTE: cámara habilitada != gateway conectado; temperatura != tráfico RX/TX.

const nivel = {
  critical: 'bg-red-50 border-red-200 text-red-700',
  high: 'bg-red-50 border-red-200 text-red-700',
  medium: 'bg-amber-50 border-amber-200 text-amber-800',
  low: 'bg-blue-50 border-blue-200 text-blue-700',
};

const gatewayConfig = {
  online: {
    icon: Wifi,
    label: 'Online',
    className: 'text-green-600',
    badgeClass: 'bg-green-50 text-green-700',
  },
  offline: {
    icon: WifiOff,
    label: 'Offline',
    className: 'text-red-600',
    badgeClass: 'bg-red-50 text-red-700',
  },
  unknown: {
    icon: HelpCircle,
    label: 'Conexión no informada',
    className: 'text-gray-500',
    badgeClass: 'bg-gray-100 text-gray-700',
  },
};

const fechaLocal = (valor) => {
  if (!valor || Number.isNaN(Date.parse(valor))) return 'Fecha no disponible';
  return new Date(valor).toLocaleString('es-CL');
};

// No confundir un error HTTP con una lista vacía legítima.
const EstadoConsulta = ({ loading, error, empty, emptyMessage, children }) => {
  if (loading) {
    return <p className="text-sm text-gray-500" role="status">Consultando datos reales…</p>;
  }

  if (error) {
    return (
      <div
        role="alert"
        className="flex gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900"
      >
        <AlertTriangle size={18} className="mt-0.5 shrink-0" />
        <p>{error}</p>
      </div>
    );
  }

  if (empty) return <p className="text-sm text-gray-500">{emptyMessage}</p>;
  return children;
};

const PanelTecnico = () => {
  const [actualizando, setActualizando] = useState(false);
  const [vistaActiva, setVistaActiva] = useState('general');
  const [verificandoSalud, setVerificandoSalud] = useState(false);
  const [salud, setSalud] = useState(null);
  const [errorSalud, setErrorSalud] = useState('');

  // A3: datos reales del sistema.
  const camarasConsulta = useFetch(getCamarasTecnico, []);
  const alertasConsulta = useFetch(getAlertasSistema, []);
  const temperaturaConsulta = useFetch(getTemperaturasTecnico, []);
  const sensoresConsulta = useFetch(getSensores, []);

  // Diego: gateways. Si D6 aún no publica la ruta, se muestra el error de API.
  const gatewaysConsulta = useFetch(getGateways, []);

  const camaras = prepararCamaras(
    Array.isArray(camarasConsulta.data) ? camarasConsulta.data : [],
  );
  const alertas = prepararAlertas(
    Array.isArray(alertasConsulta.data) ? alertasConsulta.data : [],
  );
  const temperaturas = prepararTemperaturas(
    Array.isArray(temperaturaConsulta.data) ? temperaturaConsulta.data : [],
  );
  const sensores = prepararSensores(
    Array.isArray(sensoresConsulta.data) ? sensoresConsulta.data : [],
  );
  const gateways = Array.isArray(gatewaysConsulta.data) ? gatewaysConsulta.data : [];

  const actualizar = async () => {
    setActualizando(true);
    try {
      await Promise.allSettled([
        camarasConsulta.reload(),
        alertasConsulta.reload(),
        temperaturaConsulta.reload(),
        sensoresConsulta.reload(),
        gatewaysConsulta.reload(),
      ]);
    } finally {
      setActualizando(false);
    }
  };

  // La respuesta de /panel/health no tiene un esquema declarado en panelTecnico.js.
  // Por eso se leen status/checks de forma defensiva, sin asumir que siempre existan.
  const verificarSaludSistema = async () => {
    setVerificandoSalud(true);
    setErrorSalud('');
    try {
      const resultado = await verificarSalud();
      setSalud(resultado ?? null);

      await Promise.allSettled([
        gatewaysConsulta.reload(),
        alertasConsulta.reload(),
        sensoresConsulta.reload(),
      ]);
    } catch (error) {
      setSalud(null);
      setErrorSalud(
        error?.message || 'No se pudo verificar la salud del panel.',
      );
    } finally {
      setVerificandoSalud(false);
    }
  };

  const checksSalud = salud?.checks && typeof salud.checks === 'object'
    ? Object.entries(salud.checks)
    : [];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Panel de Control Técnico</h1>
          <p className="text-sm text-gray-500">
            Datos consultados desde FastAPI y TimescaleDB · sin simulaciones de respaldo
          </p>
        </div>

        {vistaActiva === 'general' && (
          <button
            type="button"
            onClick={actualizar}
            disabled={actualizando}
            className="inline-flex items-center gap-2 rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
          >
            <RefreshCw size={16} className={actualizando ? 'animate-spin' : ''} />
            {actualizando ? 'Actualizando…' : 'Actualizar datos'}
          </button>
        )}
      </div>

      <div
        className="flex flex-wrap gap-2 border-b border-gray-200"
        role="tablist"
        aria-label="Secciones del panel técnico"
      >
        <button
          type="button"
          role="tab"
          id="tab-tecnico-general"
          aria-selected={vistaActiva === 'general'}
          aria-controls="panel-tecnico-general"
          tabIndex={vistaActiva === 'general' ? 0 : -1}
          onClick={() => setVistaActiva('general')}
          className={`inline-flex items-center gap-2 rounded-t-lg border-b-2 px-4 py-3 text-sm font-medium transition-colors ${
            vistaActiva === 'general'
              ? 'border-green-600 bg-green-50 text-green-700'
              : 'border-transparent text-gray-500 hover:bg-gray-50 hover:text-gray-700'
          }`}
        >
          <Server size={16} />
          Vista general
          <span className="rounded-full bg-white/80 px-2 py-0.5 text-xs">A3</span>
        </button>

        <button
          type="button"
          role="tab"
          id="tab-tecnico-diagnostico"
          aria-selected={vistaActiva === 'diagnostico'}
          aria-controls="panel-tecnico-diagnostico"
          tabIndex={vistaActiva === 'diagnostico' ? 0 : -1}
          onClick={() => setVistaActiva('diagnostico')}
          className={`inline-flex items-center gap-2 rounded-t-lg border-b-2 px-4 py-3 text-sm font-medium transition-colors ${
            vistaActiva === 'diagnostico'
              ? 'border-blue-600 bg-blue-50 text-blue-700'
              : 'border-transparent text-gray-500 hover:bg-gray-50 hover:text-gray-700'
          }`}
        >
          <Activity size={16} />
          Diagnóstico por cámara
          <span className="rounded-full bg-white/80 px-2 py-0.5 text-xs">A4</span>
        </button>
      </div>

      {vistaActiva === 'general' ? (
        <div
          id="panel-tecnico-general"
          role="tabpanel"
          aria-labelledby="tab-tecnico-general"
          className="space-y-6"
        >

          {/* Integración de Diego: gateways + comprobación de salud. */}
          <section
            className="rounded-lg bg-white p-6 shadow-md"
            aria-label="Estado de gateways y salud del panel"
          >
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="font-semibold text-gray-800">Conectividad e Ingesta</h2>
                <p className="mt-1 text-xs text-gray-500">
                  Gateways: GET /api/v1/panel/gateways · Salud: GET /api/v1/panel/health
                </p>
              </div>
              <button
                type="button"
                onClick={verificarSaludSistema}
                disabled={verificandoSalud}
                className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <RefreshCw size={15} className={verificandoSalud ? 'animate-spin' : ''} />
                {verificandoSalud ? 'Verificando…' : 'Verificar salud'}
              </button>
            </div>

            <div className="grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,2fr)_minmax(260px,1fr)]">
              <div>
                <div className="mb-3 flex items-center gap-2">
                  <Server size={18} className="text-green-600" />
                  <h3 className="font-medium text-gray-800">Estado de Gateways</h3>
                  {!gatewaysConsulta.loading && !gatewaysConsulta.error && (
                    <span className="ml-auto text-xs text-gray-500">
                      {gateways.length} en la respuesta
                    </span>
                  )}
                </div>

                <p className="mb-3 text-xs text-gray-500">
                  Se muestra el estado informado por el backend. El campo «Activa/Inactiva»
                  corresponde a la propiedad active y no reemplaza el estado de conexión.
                </p>

                <EstadoConsulta
                  loading={gatewaysConsulta.loading}
                  error={gatewaysConsulta.error}
                  empty={!gateways.length}
                  emptyMessage="La API no devolvió gateways registrados."
                >
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
                    {gateways.map((gateway, index) => {
                      const estado = String(gateway.estado || 'unknown').toLowerCase();
                      const config = gatewayConfig[estado] || gatewayConfig.unknown;
                      const IconoEstado = config.icon;

                      return (
                        <article
                          key={gateway.id ?? gateway.nombre ?? index}
                          className="rounded-lg border border-gray-200 p-4"
                        >
                          <div className="flex items-center justify-between gap-2">
                            <span className="break-all font-mono text-xs text-gray-500">
                              {gateway.id || 'ID no informado'}
                            </span>
                            <IconoEstado size={17} className={config.className} />
                          </div>

                          <p className="mt-2 font-medium text-gray-800">
                            {gateway.nombre || 'Gateway sin nombre'}
                          </p>

                          <span className={`mt-2 inline-flex rounded-full px-2 py-1 text-xs font-medium ${config.badgeClass}`}>
                            {config.label}
                          </span>

                          <p className="mt-2 text-xs text-gray-500">
                            Última conexión: {gateway.ultima_conexion || 'Sin registros'}
                          </p>
                          <p className="mt-1 text-xs text-gray-500">
                            Sensores: {gateway.sensores ?? 'No informado'} ·{' '}
                            {gateway.active === true
                              ? 'Activa'
                              : gateway.active === false
                                ? 'Inactiva'
                                : 'Estado administrativo no informado'}
                          </p>
                        </article>
                      );
                    })}
                  </div>
                </EstadoConsulta>
              </div>

              <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
                <div className="mb-3 flex items-center gap-2">
                  <Activity size={18} className="text-blue-600" />
                  <h3 className="font-medium text-gray-800">Salud del panel / Ingesta</h3>
                </div>

                <EstadoConsulta
                  loading={verificandoSalud}
                  error={errorSalud}
                  empty={!salud}
                  emptyMessage="Aún no se ha ejecutado la verificación de salud."
                >
                  <p className="text-sm text-gray-700">
                    Estado:{' '}
                    <strong>{salud?.status ?? 'No informado por la API'}</strong>
                  </p>

                  {checksSalud.length > 0 ? (
                    <ul className="mt-3 space-y-2">
                      {checksSalud.map(([nombre, estado]) => (
                        <li
                          key={nombre}
                          className="flex items-center justify-between gap-3 border-t border-gray-200 pt-2 text-sm"
                        >
                          <span className="break-all text-gray-600">{nombre}</span>
                          <span className="font-medium text-gray-800">
                            {typeof estado === 'string' || typeof estado === 'number'
                              ? String(estado)
                              : JSON.stringify(estado)}
                          </span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="mt-2 text-xs text-gray-500">
                      La API no entregó un objeto checks en esta respuesta.
                    </p>
                  )}
                </EstadoConsulta>
              </div>
            </div>
          </section>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            <section
              className="rounded-lg bg-white p-6 shadow-md lg:col-span-2"
              aria-label="Cámaras registradas"
            >
              <div className="mb-3 flex items-center gap-2">
                <Server size={19} className="text-green-600" />
                <h2 className="font-semibold text-gray-800">Cámaras registradas</h2>
                {!camarasConsulta.error && !camarasConsulta.loading && (
                  <span className="ml-auto text-xs text-gray-500">
                    {camaras.length} en la respuesta
                  </span>
                )}
              </div>

              <p className="mb-4 text-xs text-gray-500">
                Fuente: GET /api/v1/chambers. «Habilitada» es un estado de registro,
                no demuestra conexión MQTT, ping ni uptime del gateway.
              </p>

              <EstadoConsulta
                loading={camarasConsulta.loading}
                error={camarasConsulta.error}
                empty={!camaras.length}
                emptyMessage="No hay cámaras en el listado devuelto por el backend."
              >
                <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                  {camaras.map((camara) => (
                    <article
                      key={camara.id}
                      className="min-w-0 rounded-lg border border-gray-200 p-4"
                    >
                      <p className="break-all font-mono text-xs text-gray-400">
                        {camara.id}
                      </p>
                      <p className="mt-1 font-medium text-gray-800">{camara.nombre}</p>
                      <p className="text-xs text-gray-500">
                        {camara.ubicacion || 'Ubicación no registrada'}
                      </p>
                      <span
                        className={`mt-2 inline-block rounded-full px-2 py-1 text-xs ${
                          camara.habilitada === true
                            ? 'bg-green-50 text-green-700'
                            : camara.habilitada === false
                              ? 'bg-gray-100 text-gray-700'
                              : 'bg-amber-50 text-amber-800'
                        }`}
                      >
                        {camara.habilitada === true
                          ? 'Habilitada'
                          : camara.habilitada === false
                            ? 'Deshabilitada'
                            : 'Estado no informado'}
                      </span>
                    </article>
                  ))}
                </div>
              </EstadoConsulta>
            </section>

            <section
              className="rounded-lg bg-white p-6 shadow-md"
              aria-label="Alertas recientes"
            >
              <div className="mb-3 flex items-center gap-2">
                <Bell size={19} className="text-amber-600" />
                <h2 className="font-semibold text-gray-800">Alertas recientes</h2>
              </div>

              <p className="mb-4 text-xs text-gray-500">
                Fuente: GET /api/v1/alerts?limit=20. Incluye todos los estados;
                no representa el total histórico ni «alertas nuevas».
              </p>

              <EstadoConsulta
                loading={alertasConsulta.loading}
                error={alertasConsulta.error}
                empty={!alertas.length}
                emptyMessage="La API no devolvió alertas en la consulta actual."
              >
                <div className="max-h-96 space-y-3 overflow-y-auto">
                  {alertas.map((alerta) => (
                    <article
                      key={alerta.id}
                      className={`rounded-lg border p-3 ${
                        nivel[alerta.severidad] || 'border-gray-200 bg-gray-50 text-gray-800'
                      }`}
                    >
                      <div className="flex flex-wrap justify-between gap-2 text-xs font-semibold">
                        <span>{alerta.severidad || 'Severidad no informada'}</span>
                        <span>{alerta.estado || 'Estado no informado'}</span>
                      </div>
                      <p className="mt-2 text-sm">{alerta.mensaje}</p>
                      <p className="mt-1 break-all text-xs opacity-75">
                        Cámara: {alerta.camara || 'No informada'}
                      </p>
                      <p className="mt-1 text-xs opacity-75">{fechaLocal(alerta.fecha)}</p>
                    </article>
                  ))}
                </div>
              </EstadoConsulta>
            </section>
          </div>

          <section
            className="rounded-lg bg-white p-6 shadow-md"
            aria-label="Temperatura de las últimas seis horas"
          >
            <div className="mb-2 flex items-center gap-2">
              <Activity size={19} className="text-green-600" />
              <h2 className="font-semibold text-gray-800">
                Temperatura de la planta · últimas 6 horas
              </h2>
            </div>

            <p className="mb-4 text-xs text-gray-500">
              Fuente: GET /api/v1/dashboard/temperature?minutes=360. Media simple de las
              temperaturas promedio por cámara en cada intervalo (°C). No son bytes RX/TX
              ni tráfico de red.
            </p>

            <EstadoConsulta
              loading={temperaturaConsulta.loading}
              error={temperaturaConsulta.error}
              empty={!temperaturas.length}
              emptyMessage="No hay lecturas de temperatura en las últimas seis horas."
            >
              <div style={{ width: '100%', height: 240 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart
                    data={temperaturas}
                    margin={{ top: 5, right: 16, left: 2, bottom: 5 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                    <XAxis
                      dataKey="hora"
                      stroke="#6b7280"
                      tick={{ fontSize: 11 }}
                      minTickGap={24}
                    />
                    <YAxis
                      stroke="#6b7280"
                      tick={{ fontSize: 11 }}
                      unit=" °C"
                      width={62}
                      domain={['auto', 'auto']}
                    />
                    <Tooltip
                      formatter={(valor, nombre) => [
                        `${Number(valor).toLocaleString('es-CL', { maximumFractionDigits: 2 })} °C`,
                        nombre,
                      ]}
                      labelFormatter={(_, payload) => (
                        payload?.[0]?.payload?.timestamp
                          ? fechaLocal(payload[0].payload.timestamp)
                          : ''
                      )}
                    />
                    <Line
                      type="monotone"
                      dataKey="temperatura"
                      name="Temperatura media"
                      stroke="#059669"
                      strokeWidth={2}
                      dot={false}
                      connectNulls={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
              <p className="mt-2 text-xs text-gray-500">
                Se grafican {temperaturas.length} intervalos con lecturas. Los intervalos
                sin datos no se inventan.
              </p>
            </EstadoConsulta>
          </section>

          <section
            className="rounded-lg bg-white p-6 shadow-md"
            aria-label="Inventario de sensores"
          >
            <div className="mb-2 flex items-center gap-2">
              <Thermometer size={19} className="text-green-600" />
              <h2 className="font-semibold text-gray-800">Inventario de sensores</h2>
            </div>

            <p className="mb-4 text-xs text-gray-500">
              Fuente prevista: GET /api/v1/panel/sensores (tarea D6). Si esta ruta no está
              publicada, se informa el problema en vez de mostrar sensores o baterías ficticias.
            </p>

            <EstadoConsulta
              loading={sensoresConsulta.loading}
              error={sensoresConsulta.error}
              empty={!sensores.length}
              emptyMessage="No se encontraron sensores registrados. No se presupone ningún sensor conectado."
            >
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b text-xs uppercase text-gray-500">
                      <th className="py-3 pr-4">Sensor</th>
                      <th className="py-3 pr-4">Ubicación</th>
                      <th className="py-3 pr-4">Tipo</th>
                      <th className="py-3 pr-4">Batería</th>
                      <th className="py-3 pr-4">Última lectura</th>
                      <th className="py-3">Estado</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sensores.map((sensor, index) => (
                      <tr
                        key={sensor.id ?? index}
                        className="border-b border-gray-100 text-gray-700"
                      >
                        <td className="py-3 pr-4 font-mono text-xs">{sensor.id ?? '—'}</td>
                        <td className="py-3 pr-4">{sensor.ubicacion ?? '—'}</td>
                        <td className="py-3 pr-4">{sensor.tipo ?? '—'}</td>
                        <td className="py-3 pr-4">
                          {sensor.bateria == null ? 'No reportada' : `${sensor.bateria}%`}
                        </td>
                        <td className="py-3 pr-4">{sensor.ultimaLectura ?? 'No reportada'}</td>
                        <td className="py-3">{sensor.estado ?? 'No informado'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </EstadoConsulta>
          </section>
        </div>
      ) : (
        <div
          id="panel-tecnico-diagnostico"
          role="tabpanel"
          aria-labelledby="tab-tecnico-diagnostico"
        >
          <DiagnosticoCamara camaras={camaras} />
        </div>
      )}
    </div>
  );
};

export default PanelTecnico;