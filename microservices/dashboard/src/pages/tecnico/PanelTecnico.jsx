import React, { useState } from 'react';

import {

  Activity, AlertTriangle, Bell, RefreshCw, Server, Thermometer,

} from 'lucide-react';

import {

  CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,

} from 'recharts';

import { useFetch } from '../../hooks/useApi';

import EstadoSistema from '../../components/shared/EstadoSistema';

import {

  getCamarasTecnico, getAlertasSistema, getTemperaturasTecnico, getSensores,

} from '../../api/panelTecnico';

import {
  prepararCamaras, prepararAlertas, prepararTemperaturas, prepararSensores,
} from '../../utils/panelTecnicoReal';
import DiagnosticoCamara from './DiagnosticoCamara';



// Sprint 3 · A3 — Ningún dato visible de este panel se obtiene de MOCK_*.

// IMPORTANTE: cámara habilitada != gateway conectado; temperatura != tráfico RX/TX.

const nivel = {

  critical: 'bg-red-50 border-red-200 text-red-700',

  high: 'bg-red-50 border-red-200 text-red-700',

  medium: 'bg-amber-50 border-amber-200 text-amber-800',

  low: 'bg-blue-50 border-blue-200 text-blue-700',

};



const fechaLocal = (valor) => {

  if (!valor || Number.isNaN(Date.parse(valor))) return 'Fecha no disponible';

  return new Date(valor).toLocaleString('es-CL');

};



// No confundir un error HTTP con una lista vacía legítima.

const EstadoConsulta = ({ loading, error, empty, emptyMessage, children }) => {

  if (loading) return <p className="text-sm text-gray-500" role="status">Consultando datos reales…</p>;

  if (error) return (

    <div role="alert" className="flex gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">

      <AlertTriangle size={18} className="shrink-0 mt-0.5" />

      <p>No se pudieron obtener datos de esta sección: {error}</p>

    </div>

  );

  if (empty) return <p className="text-sm text-gray-500">{emptyMessage}</p>;

  return children;

};



const PanelTecnico = () => {

  const [actualizando, setActualizando] = useState(false);
  const [vistaActiva, setVistaActiva] = useState('general');



// useFetch no recibe fallbackData. En error NO mostramos datos ficticios.

  const camarasConsulta = useFetch(getCamarasTecnico, []);

  const alertasConsulta = useFetch(getAlertasSistema, []);

  const temperaturaConsulta = useFetch(getTemperaturasTecnico, []);

  const sensoresConsulta = useFetch(getSensores, []);



  const camaras = prepararCamaras(Array.isArray(camarasConsulta.data) ? camarasConsulta.data : []);

  const alertas = prepararAlertas(Array.isArray(alertasConsulta.data) ? alertasConsulta.data : []);

  const temperaturas = prepararTemperaturas(Array.isArray(temperaturaConsulta.data) ? temperaturaConsulta.data : []);

  const sensores = prepararSensores(Array.isArray(sensoresConsulta.data) ? sensoresConsulta.data : []);



  const actualizar = async () => {

    setActualizando(true);

    try {

      await Promise.allSettled([

        camarasConsulta.reload(), alertasConsulta.reload(),

        temperaturaConsulta.reload(), sensoresConsulta.reload(),

      ]);

    } finally {

      setActualizando(false);

    }

  };



  return (

    <div className="space-y-6">

      <div className="flex flex-wrap items-start justify-between gap-3">

        <div>

          <h1 className="text-2xl font-bold text-gray-800">Panel de Control Técnico</h1>

          <p className="text-sm text-gray-500">

            Datos reales consultados desde FastAPI y TimescaleDB · sin simulaciones de respaldo

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
        </button>
      </div>

      {vistaActiva === 'general' ? (
        <div id="panel-tecnico-general" role="tabpanel" aria-labelledby="tab-tecnico-general" className="space-y-6">
          {/* Estado del System Controller: se conserva el componente original. */}
          <EstadoSistema />



      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">

        <section className="rounded-lg bg-white p-6 shadow-md lg:col-span-2" aria-label="Cámaras registradas">

          <div className="mb-3 flex items-center gap-2">

            <Server size={19} className="text-green-600" />

            <h2 className="font-semibold text-gray-800">Cámaras registradas</h2>

            {!camarasConsulta.error && !camarasConsulta.loading && (

              <span className="ml-auto text-xs text-gray-500">{camaras.length} en la respuesta</span>

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

              {camaras.map((c) => (

                <article key={c.id} className="min-w-0 rounded-lg border border-gray-200 p-4">

                  <p className="break-all font-mono text-xs text-gray-400">{c.id}</p>

                  <p className="mt-1 font-medium text-gray-800">{c.nombre}</p>

                  <p className="text-xs text-gray-500">{c.ubicacion || 'Ubicación no registrada'}</p>

                  <span className={`mt-2 inline-block rounded-full px-2 py-1 text-xs ${

                    c.habilitada === true ? 'bg-green-50 text-green-700'

                      : c.habilitada === false ? 'bg-gray-100 text-gray-700'

                        : 'bg-amber-50 text-amber-800'

                  }`}>

                    {c.habilitada === true ? 'Habilitada' : c.habilitada === false ? 'Deshabilitada' : 'Estado no informado'}

                  </span>

                </article>

              ))}

            </div>

          </EstadoConsulta>

        </section>



        <section className="rounded-lg bg-white p-6 shadow-md" aria-label="Alertas recientes">

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

              {alertas.map((a) => (

                <article key={a.id} className={`rounded-lg border p-3 ${nivel[a.severidad] || 'bg-gray-50 border-gray-200 text-gray-800'}`}>

                  <div className="flex flex-wrap justify-between gap-2 text-xs font-semibold">

                    <span>{a.severidad || 'Severidad no informada'}</span>

                    <span>{a.estado || 'Estado no informado'}</span>

                  </div>

                  <p className="mt-2 text-sm">{a.mensaje}</p>

                  <p className="mt-1 break-all text-xs opacity-75">Cámara: {a.camara || 'No informada'}</p>

                  <p className="mt-1 text-xs opacity-75">{fechaLocal(a.fecha)}</p>

                </article>

              ))}

            </div>

          </EstadoConsulta>

        </section>

      </div>



      <section className="rounded-lg bg-white p-6 shadow-md" aria-label="Temperatura de las últimas seis horas">

        <div className="mb-2 flex items-center gap-2">

          <Activity size={19} className="text-green-600" />

          <h2 className="font-semibold text-gray-800">Temperatura de la planta · últimas 6 horas</h2>

        </div>

        <p className="mb-4 text-xs text-gray-500">

          Fuente: GET /api/v1/dashboard/temperature?minutes=360. Media simple de las

          temperaturas promedio por cámara en cada intervalo (°C). No son bytes RX/TX ni tráfico de red.

        </p>

        <EstadoConsulta

          loading={temperaturaConsulta.loading}

          error={temperaturaConsulta.error}

          empty={!temperaturas.length}

          emptyMessage="No hay lecturas de temperatura en las últimas seis horas."

        >

          <div style={{ width: '100%', height: 240 }}>

            <ResponsiveContainer width="100%" height="100%">

              <LineChart data={temperaturas} margin={{ top: 5, right: 16, left: 2, bottom: 5 }}>

                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />

                <XAxis dataKey="hora" stroke="#6b7280" tick={{ fontSize: 11 }} minTickGap={24} />

                <YAxis stroke="#6b7280" tick={{ fontSize: 11 }} unit=" °C" width={62} domain={['auto', 'auto']} />

                <Tooltip

                  formatter={(v, nombre) => [Number(v).toLocaleString('es-CL', { maximumFractionDigits: 2 }) + ' °C', nombre]}

                  labelFormatter={(_, payload) => payload?.[0]?.payload?.timestamp

                    ? fechaLocal(payload[0].payload.timestamp) : ''}

                />

                <Line type="monotone" dataKey="temperatura" name="Temperatura media" stroke="#059669" strokeWidth={2} dot={false} connectNulls={false} />

              </LineChart>

            </ResponsiveContainer>

          </div>

          <p className="mt-2 text-xs text-gray-500">

            Se grafican {temperaturas.length} intervalos con lecturas. Los intervalos sin datos no se inventan.

          </p>

        </EstadoConsulta>

      </section>



      <section className="rounded-lg bg-white p-6 shadow-md" aria-label="Inventario de sensores">

        <div className="mb-2 flex items-center gap-2">

          <Thermometer size={19} className="text-green-600" />

          <h2 className="font-semibold text-gray-800">Inventario de sensores</h2>

        </div>

        <p className="mb-4 text-xs text-gray-500">

          Fuente prevista: GET /api/v1/panel/sensores (tarea D6 de Diego).

          Si esta ruta no está publicada, se informa el problema en vez de mostrar SN-101, baterías o calibraciones ficticias.

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

                {sensores.map((s, i) => (

                  <tr key={s.id ?? i} className="border-b border-gray-100 text-gray-700">

                    <td className="py-3 pr-4 font-mono text-xs">{s.id ?? '—'}</td>

                    <td className="py-3 pr-4">{s.ubicacion ?? '—'}</td>

                    <td className="py-3 pr-4">{s.tipo ?? '—'}</td>

                    <td className="py-3 pr-4">{s.bateria === null ? 'No reportada' : `${s.bateria}%`}</td>

                    <td className="py-3 pr-4">{s.ultimaLectura ?? 'No reportada'}</td>

                    <td className="py-3">{s.estado ?? 'No informado'}</td>

                  </tr>

                ))}

              </tbody>

            </table>

          </div>

        </EstadoConsulta>

      </section>
        </div>
      ) : (
        <div id="panel-tecnico-diagnostico" role="tabpanel" aria-labelledby="tab-tecnico-diagnostico">
          <DiagnosticoCamara camaras={camaras} />
        </div>
      )}
    </div>
  );
};

export default PanelTecnico;