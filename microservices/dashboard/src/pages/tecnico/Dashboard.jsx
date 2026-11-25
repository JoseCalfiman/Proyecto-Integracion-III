import React, { useEffect, useMemo, useState } from 'react';
import { Camera, AlertTriangle, Activity, Clock, RefreshCw } from 'lucide-react';
import { Link } from 'react-router-dom';
import MetricCard from '../../components/ui/MetricCard';
import TemperatureChart from '../../components/charts/TemperatureChart';
import PredictionDiagnostics from '../../components/shared/PredictionDiagnostics';
import { getDashboardLive } from '../../api/dashboard';
import { getCamarasTecnico, getSensores, getTemperaturasTecnico } from '../../api/panelTecnico';
import { getReglaDiagnostico } from '../../api/diagnosticoCamara';

const INTERVALO = 15000;
const VENTANA_MIN = 120;
const BUCKET_MS = 120000; // /dashboard/temperature agrupa 120 minutos en intervalos de 2 min.
const ATRASO_MS = 120000; // umbral operativo de frescura, no diagnóstico de desconexión.
const ALL = 'all';
const leerTemperatura = () => getTemperaturasTecnico(VENTANA_MIN);
const numero = (v) => typeof v === 'number' && Number.isFinite(v) ? v.toLocaleString('es-CL', { maximumFractionDigits: 2 }) : '—';
const fecha = (v) => Number.isFinite(Date.parse(v)) ? new Date(v).toLocaleString('es-CL') : 'Sin registro';

// Cada consulta conserva su propio error y hora de éxito. No hay respaldo simulado.
function useConsulta(fetcher, clave, recarga, intervalo = INTERVALO) {
  const [estado, setEstado] = useState(null);
  useEffect(() => {
    let vigente = true;
    let timer;
    const consultar = async () => {
      try {
        const data = await fetcher(clave);
        if (vigente) setEstado({ clave, data, error: null, fecha: Date.now() });
      } catch (error) {
        if (vigente) setEstado((prev) => ({
          clave, data: prev?.clave === clave ? prev.data : null,
          fecha: prev?.clave === clave ? prev.fecha : null,
          error: error?.message || 'No se pudo consultar la API',
        }));
      } finally {
        if (vigente) timer = setTimeout(consultar, intervalo);
      }
    };
    consultar();
    return () => { vigente = false; clearTimeout(timer); };
  }, [fetcher, clave, recarga, intervalo]);
  return estado?.clave === clave ? estado : { data: null, error: null, fecha: null };
}

const lista = (v) => Array.isArray(v) ? v : [];
const carga = (q) => q.data === null && !q.error;
const ErrorConsulta = ({ consulta, nombre }) => consulta.error ? (
  <p role="alert" className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
    {nombre}: {consulta.error}. {consulta.fecha ? `Última consulta exitosa: ${new Date(consulta.fecha).toLocaleTimeString('es-CL')}. Se muestran datos anteriores.` : 'Datos no disponibles.'}
  </p>
) : null;

function frescura(sensor, ahora) {
  const ms = Date.parse(sensor.ultima_lectura);
  if (!Number.isFinite(ms)) return { label: 'Sin lectura registrada', color: 'bg-gray-100 text-gray-700', tipo: 'sin', edad: '—' };
  const edadMs = ahora - ms;
  if (edadMs < 0) return { label: 'Fecha futura', color: 'bg-amber-100 text-amber-800', tipo: 'revisar', edad: '—' };
  const segundos = Math.floor(edadMs / 1000);
  const edad = segundos < 60 ? `${segundos} s` : segundos < 3600 ? `${Math.floor(segundos / 60)} min` : `${Math.floor(segundos / 3600)} h`;
  return edadMs > ATRASO_MS
    ? { label: 'Lectura atrasada', color: 'bg-amber-100 text-amber-800', tipo: 'revisar', edad }
    : { label: 'Lectura reciente', color: 'bg-green-100 text-green-700', tipo: 'reciente', edad };
}

function agruparTemperaturas(rows, ids, instante) {
  const inicio = Math.floor((instante - VENTANA_MIN * 60000) / BUCKET_MS) * BUCKET_MS;
  const fin = Math.floor(instante / BUCKET_MS) * BUCKET_MS;
  const buckets = new Map();
  for (let ms = inicio; ms <= fin; ms += BUCKET_MS) buckets.set(ms, { timestamp: ms });
  const permitidos = new Set(ids);
  for (const row of rows) {
    const ms = Date.parse(row.timestamp);
    if (!buckets.has(ms) || !permitidos.has(row.id_chamber) || typeof row.temperature !== 'number' || !Number.isFinite(row.temperature)) continue;
    buckets.get(ms)[row.id_chamber] = row.temperature;
  }
  return [...buckets.values()];
}

const Dashboard = () => {
  const [recarga, setRecarga] = useState(0);
  const [seleccion, setSeleccion] = useState(ALL);
  const [soloRevision, setSoloRevision] = useState(false);
  const [ahora, setAhora] = useState(Date.now());
  useEffect(() => {
    const timer = setInterval(() => setAhora(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);

  const resumen = useConsulta(getDashboardLive, 'resumen', recarga);
  const camarasConsulta = useConsulta(getCamarasTecnico, 'camaras', recarga);
  const temperatura = useConsulta(leerTemperatura, 'temperaturas', recarga);
  const sensoresConsulta = useConsulta(getSensores, 'sensores', recarga);
  const camaras = lista(camarasConsulta.data);
  const sensores = lista(sensoresConsulta.data);
  const id = seleccion !== ALL && camaras.some((c) => c.id_chamber === seleccion) ? seleccion : ALL;
  // Evita solicitar reglas para la vista general y no confunde límites entre cámaras.
  // El fetcher debe ser estable para no reiniciar el polling con cada render.
  const regla = useConsulta(fetchRegla, id, recarga, 60000);

  const ids = useMemo(() => id === ALL ? lista(camarasConsulta.data).map((c) => c.id_chamber) : [id], [id, camarasConsulta.data]);
  const labels = useMemo(() => Object.fromEntries(lista(camarasConsulta.data).map((c) => [c.id_chamber, c.name || c.id_chamber])), [camarasConsulta.data]);
  const datosGrafico = useMemo(() => agruparTemperaturas(lista(temperatura.data), ids, temperatura.fecha || Date.now()), [temperatura.data, temperatura.fecha, ids]);
  const muestras = id === ALL ? [] : datosGrafico.filter((p) => typeof p[id] === 'number');
  const valores = muestras.map((p) => p[id]);
  const ultimo = muestras.at(-1);
  const reglaActiva = id !== ALL && regla.data?.active === true && !regla.error;
  const minTemp = reglaActiva ? regla.data.min_absolute_temp : undefined;
  const maxTemp = reglaActiva ? regla.data.max_absolute_temp : undefined;
  const sensoresConEstado = sensores.map((s) => ({ ...s, frescura: frescura(s, ahora) }));
  const revisar = sensoresConEstado.filter((s) => s.frescura.tipo !== 'reciente').length;
  const visibles = sensoresConEstado.filter((s) => (id === ALL || s.id_chamber === id) && (!soloRevision || s.frescura.tipo !== 'reciente'));
  const valorSensor = (v) => carga(sensoresConsulta) ? '…' : sensoresConsulta.data === null ? '—' : v;
  const valorResumen = (v) => carga(resumen) ? '…' : numero(v);

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Monitoreo técnico</h1>
          <p className="text-sm text-gray-500">Supervisión térmica, telemetría y diagnóstico operativo · Consulta automática cada 15 s</p>
          <p className="mt-1 text-xs text-gray-500">Última consulta de temperatura: {temperatura.fecha ? new Date(temperatura.fecha).toLocaleTimeString('es-CL') : '—'}</p>
        </div>
        <button type="button" onClick={() => setRecarga((n) => n + 1)} className="inline-flex items-center gap-2 rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700"><RefreshCw size={16} />Actualizar datos</button>
      </header>

      <ErrorConsulta consulta={resumen} nombre="Resumen de planta" />
      <ErrorConsulta consulta={sensoresConsulta} nombre="Inventario de sensores" />
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard title="Cámaras habilitadas" value={valorResumen(resumen.data?.active_chambers)} icon={Camera} color="green" />
        <MetricCard title="Alertas sin reconocer" value={valorResumen(resumen.data?.active_alerts)} icon={AlertTriangle} color="red" />
        <MetricCard title="Sensores registrados" value={valorSensor(sensores.length)} icon={Activity} color="blue" />
        <MetricCard title="Sensores por revisar" value={valorSensor(revisar)} icon={Clock} color="yellow" />
      </div>
      <p className="text-xs text-gray-500">Sensores por revisar: lectura de más de 2 minutos, sin fecha o con fecha futura. No implica que estén desconectados. Cámaras habilitadas no equivale a cámaras conectadas.</p>

      <section className="space-y-4" aria-label="Supervisión térmica por cámara">
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-gray-200 bg-white p-4">
          <div><h2 className="font-semibold text-gray-800">Supervisión por cámara</h2><p className="text-xs text-gray-500">El filtro se aplica al gráfico y a la tabla de sensores.</p></div>
          <label className="flex flex-wrap items-center gap-2 text-sm text-gray-700">Cámara
            <select value={id} onChange={(e) => setSeleccion(e.target.value)} className="max-w-full rounded-lg border border-gray-300 bg-white px-3 py-2">
              <option value={ALL}>Todas las cámaras habilitadas</option>
              {camaras.map((c) => <option key={c.id_chamber} value={c.id_chamber}>{c.name || c.id_chamber}</option>)}
            </select>
          </label>
        </div>
        <ErrorConsulta consulta={camarasConsulta} nombre="Cámaras" />
        <ErrorConsulta consulta={temperatura} nombre="Serie de temperatura" />
        {id !== ALL && <ErrorConsulta consulta={regla} nombre="Regla HACCP" />}
        {id !== ALL && (
          <div className="grid grid-cols-2 gap-3 rounded-lg border border-gray-200 bg-white p-4 lg:grid-cols-4">
            {[
              ['Último promedio', ultimo ? `${numero(ultimo[id])} °C` : '—'],
              ['Mínimo de promedios (2h)', valores.length ? `${numero(Math.min(...valores))} °C` : '—'],
              ['Máximo de promedios (2h)', valores.length ? `${numero(Math.max(...valores))} °C` : '—'],
              ['Intervalos con datos', numero(valores.length)],
            ].map(([label, value]) => <div key={label}><p className="text-xs text-gray-500">{label}</p><p className="mt-1 text-xl font-semibold text-gray-800">{value}</p></div>)}
            <p className="col-span-full text-xs text-gray-500">Último intervalo: {ultimo ? new Date(ultimo.timestamp).toLocaleString('es-CL') : '—'}. Son promedios, no extremos de lecturas individuales. {reglaActiva ? `Tolerancia HACCP: ${numero(regla.data.tolerance_time_min)} min.${regla.data.id_rule == null ? ' Se muestran los valores por defecto de la API.' : ''}` : 'Sin límites HACCP activos confirmados para el gráfico.'}</p>
          </div>
        )}
        <TemperatureChart data={datosGrafico} series={ids} labels={labels} minTemp={minTemp} maxTemp={maxTemp} loading={carga(temperatura) || carga(camarasConsulta)} />
        {id === ALL && <p className="text-xs text-gray-500">Selecciona una cámara para ver sus límites HACCP y estadísticas térmicas individuales.</p>}
      </section>

      <PredictionDiagnostics detailed />

      <section className="rounded-lg bg-white p-4 shadow-md sm:p-6" aria-label="Estado de sensores">
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div><h2 className="text-lg font-semibold text-gray-700">Estado técnico de sensores</h2><p className="text-xs text-gray-500">Inventario real y antigüedad de la última medición registrada.</p></div>
          <label className="flex items-center gap-2 text-sm text-gray-600"><input type="checkbox" checked={soloRevision} onChange={(e) => setSoloRevision(e.target.checked)} />Solo sensores por revisar</label>
        </div>
        {carga(sensoresConsulta) ? <p role="status" className="text-sm text-gray-500">Consultando sensores…</p>
          : sensoresConsulta.data === null ? <p className="text-sm text-gray-500">Inventario no disponible.</p>
          : !visibles.length ? <p className="text-sm text-gray-500">No hay sensores para esta selección.</p>
          : <div className="overflow-x-auto"><table className="w-full min-w-[850px] text-left text-sm">
              <thead className="border-b border-gray-200 text-gray-500"><tr>{['Sensor / modelo', 'Cámara', 'Tipo', 'Identificador MQTT', 'Estado registrado', 'Última lectura', 'Frescura'].map((h) => <th key={h} scope="col" className="p-3 font-medium">{h}</th>)}</tr></thead>
              <tbody>{visibles.map((s) => <tr key={s.id} className="border-b border-gray-100 hover:bg-gray-50">
                <td className="p-3"><span className="font-medium">#{s.id}</span><p className="text-xs text-gray-500">{s.modelo || 'Modelo no informado'}</p></td>
                <td className="p-3">{s.ubicacion || labels[s.id_chamber] || 'Sin cámara'}</td>
                <td className="p-3">{s.tipo || '—'}</td><td className="break-all p-3 font-mono text-xs">{s.mqtt_identifier || '—'}</td>
                <td className="p-3">{s.estado || 'No informado'}</td>
                <td className="p-3 text-gray-600">{fecha(s.ultima_lectura)}<p className="text-xs text-gray-500">Antigüedad: {s.frescura.edad}</p></td>
                <td className="p-3"><span className={`inline-block rounded-full px-2 py-1 text-xs ${s.frescura.color}`}>{s.frescura.label}</span></td>
              </tr>)}</tbody>
            </table></div>}
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-sm"><span className="text-gray-500">{sensoresConsulta.data !== null ? `${visibles.length} sensores en la selección` : 'Sin inventario disponible'}</span><Link to="/panel-tecnico" className="font-medium text-green-700 hover:underline">Abrir Panel Técnico y diagnóstico individual →</Link></div>
      </section>
    </div>
  );
};

const fetchRegla = (id) => id === ALL ? Promise.resolve(null) : getReglaDiagnostico(id);
export default Dashboard;