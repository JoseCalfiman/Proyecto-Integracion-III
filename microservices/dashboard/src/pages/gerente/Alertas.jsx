import { useEffect, useRef, useState } from 'react';
import { AlertTriangle, CheckCircle2, Clock, Search, RefreshCw } from 'lucide-react';
import { getResumenAlertas, getHistorialAlertas, errorAlertas } from '../../api/alertasGerente';
import AuditoriaAlerta from '../../components/shared/AuditoriaAlerta';
import { obtenerTecnicos, descargarReporte, obtenerAlerta } from '../../api/intervenciones';
import { detalleError } from '../../api/sensores';
import { formatDate } from '../../utils/formatters';

const localInput = (date) => new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
const initialFilters = () => {
  const end = new Date(Math.ceil(Date.now() / 60000) * 60000);
  return { date_from: localInput(new Date(end.getTime() - 86400000)), date_to: localInput(end), status: '', severity: '', id_alert: '', resolved_by: '' };
};
const states = { active: 'Activa', acknowledged: 'Reconocida', resolved: 'Resuelta' };
const severities = { low: 'Baja', medium: 'Media', high: 'Alta', critical: 'Crítica' };
const stateClass = { active: 'bg-red-50 text-red-700', acknowledged: 'bg-amber-50 text-amber-800', resolved: 'bg-green-50 text-green-700' };
const fieldClass = 'w-full rounded-lg border border-gray-200 px-3 py-2 text-sm';

export default function Alertas({ historial = false }) {
  const [summary, setSummary] = useState(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryError, setSummaryError] = useState('');
  const [draft, setDraft] = useState(initialFilters);
  const [applied, setApplied] = useState(null);
  const [page, setPage] = useState(null);
  const [cursors, setCursors] = useState([null]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [technicians, setTechnicians] = useState([]);
  const [techniciansError, setTechniciansError] = useState('');
  const [auditId, setAuditId] = useState(null);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState('');
  const [directId, setDirectId] = useState('');
  const [directResult, setDirectResult] = useState(null);
  const [directError, setDirectError] = useState('');
  const [directLoading, setDirectLoading] = useState(false);
  const summaryRequest = useRef(null);
  const historyRequest = useRef(null);

  const refreshSummary = async () => {
    summaryRequest.current?.abort();
    const controller = new AbortController();
    summaryRequest.current = controller;
    setSummaryLoading(true);
    setSummaryError('');
    try {
      const result = await getResumenAlertas(controller.signal);
      if (!controller.signal.aborted) setSummary(result);
    } catch (err) {
      if (!controller.signal.aborted) setSummaryError(errorAlertas(err));
    } finally {
      if (!controller.signal.aborted) setSummaryLoading(false);
    }
  };

  // Únicamente un resumen al entrar. Sin polling ni descarga automática de alertas.
  useEffect(() => {
    if (!historial) refreshSummary();
    let alive = true;
    obtenerTecnicos().then(r=>{if(alive)setTechnicians(r);}).catch(e=>{if(alive)setTechniciansError(detalleError(e));});
    return () => {
      alive = false;
      summaryRequest.current?.abort();
      historyRequest.current?.abort();
    };
  }, []);

  const fetchPage = async (filters, stack) => {
    historyRequest.current?.abort();
    const controller = new AbortController();
    historyRequest.current = controller;
    setLoading(true);
    setError('');
    setAuditId(null);
    setExportError('');
    try {
      const result = await getHistorialAlertas(filters, stack[stack.length - 1], controller.signal);
      if (!controller.signal.aborted) {
        setPage(result);
        setApplied(filters);
        setCursors(stack);
      }
    } catch (err) {
      if (!controller.signal.aborted) setError(errorAlertas(err));
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  };

  const search = (event) => {
    event.preventDefault();
    const from = new Date(draft.date_from);
    const to = new Date(draft.date_to);
    if (!Number.isFinite(from.getTime()) || !Number.isFinite(to.getTime()) || to <= from || to - from > 31 * 86400000) {
      setError('Selecciona un período válido de hasta 31 días.');
      return;
    }
    const id = draft.id_alert.trim().replace(/^ALT-/i,'');
    if (id && !/^[1-9]\d*$/.test(id)) { setError('ID de alerta inválido.'); return; }
    fetchPage({ ...draft, id_alert: id, date_from: from.toISOString(), date_to: to.toISOString() }, [null]);
  };

  const exportReport = async () => { if (!applied || exporting) return; setExporting(true);setExportError('');try{await descargarReporte(applied);}catch(e){setExportError(detalleError(e));}finally{setExporting(false);} };
  const searchDirect = async (event) => { event.preventDefault();const id=directId.trim().replace(/^ALT-/i,'');setDirectError('');setDirectResult(null);if(!/^[1-9]\d*$/.test(id)){setDirectError('Ingresa un ID válido.');return;}setDirectLoading(true);try{setDirectResult(await obtenerAlerta(id));}catch(e){setDirectError(detalleError(e));}finally{setDirectLoading(false);} };
  const change = (key) => (event) => setDraft((prev) => ({ ...prev, [key]: event.target.value }));
  const cards = [
    { key: 'active', label: 'Activas', icon: AlertTriangle, color: 'text-red-600' },
    { key: 'acknowledged', label: 'Reconocidas', icon: Clock, color: 'text-amber-600' },
    { key: 'resolved', label: 'Resueltas', icon: CheckCircle2, color: 'text-green-600' },
    { key: 'high_priority_open', label: 'Alta / crítica sin resolver', icon: AlertTriangle, color: 'text-red-700' },
  ];

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">{historial ? 'Historial y reportes de intervenciones HACCP' : 'Alertas HACCP'}</h1>
          <p className="text-sm text-gray-500">Supervisión gerencial y consulta de incidentes bajo demanda.</p>
        </div>
        {!historial && <button type="button" onClick={refreshSummary} disabled={summaryLoading} className="flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium disabled:opacity-50">
          <RefreshCw size={16} className={summaryLoading ? 'animate-spin' : ''} /> Actualizar resumen
        </button>}
      </header>
      {!historial && <section aria-label="Resumen de las últimas 24 horas" className="space-y-3">
        <div>
          <h2 className="font-semibold text-gray-800">Resumen de las últimas 24 horas</h2>
          <p className="text-xs text-gray-500">Estado actual de las alertas generadas durante este período. No incluye incidentes anteriores.</p>
          {summary && <p className="mt-1 text-xs text-gray-500">Consultado: {formatDate(summary.to)}{summaryError ? ' · Último resumen disponible' : ''}</p>}
        </div>
        {summaryError && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{summaryError}</p>}
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {cards.map(({ key, label, icon: Icon, color }) => (
            <div key={key} className="rounded-lg border border-gray-100 bg-white p-5 shadow-sm">
              <div className="flex items-center justify-between gap-2 text-sm text-gray-500">{label}<Icon size={19} className={color} /></div>
              <p className={`mt-3 text-3xl font-bold ${color}`}>{summary ? summary[key] : '—'}</p>
            </div>
          ))}
        </div>
      </section>}
      <section className="rounded-lg border border-gray-100 bg-white p-5 shadow-sm">
        <h2 className="font-semibold text-gray-800">Consultar historial</h2>
        <p className="mb-4 text-sm text-gray-500">Selecciona un período (máximo 31 días) y aplica los filtros. Solo se cargan 20 alertas por página.</p>
        <form onSubmit={search} className="grid grid-cols-1 items-end gap-3 md:grid-cols-2 xl:grid-cols-5">
          <label className="text-sm text-gray-600">Desde<input className={fieldClass} type="datetime-local" required value={draft.date_from} onChange={change('date_from')} /></label>
          <label className="text-sm text-gray-600">Hasta (excluyente)<input className={fieldClass} type="datetime-local" required value={draft.date_to} onChange={change('date_to')} /></label>
          <label className="text-sm text-gray-600">Estado<select className={fieldClass} value={draft.status} onChange={change('status')}><option value="">Todos</option>{Object.entries(states).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
          <label className="text-sm text-gray-600">Severidad<select className={fieldClass} value={draft.severity} onChange={change('severity')}><option value="">Todas</option>{Object.entries(severities).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label>
          <label className="text-sm text-gray-600">ID de alerta<input className={fieldClass} value={draft.id_alert} onChange={change('id_alert')} placeholder="ALT-123" /></label>
          <label className="text-sm text-gray-600">Cerrada por<select className={fieldClass} value={draft.resolved_by} onChange={change('resolved_by')}><option value="">Todos</option>{technicians.map(t=><option key={t.id} value={t.id}>{t.name||t.id}</option>)}</select></label>
          <button type="submit" disabled={loading || exporting} className="flex items-center justify-center gap-2 rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"><Search size={16} /> Consultar</button>
        </form>
        {techniciansError&&<p className="mt-2 text-xs text-red-700">No se pudo cargar el filtro de técnicos: {techniciansError}</p>}
        {error && <p role="alert" className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}{page ? ' Se mantiene la consulta anterior.' : ''}</p>}
      </section>
      <section className="rounded-lg border bg-white p-4 space-y-3"><h2 className="font-semibold">Buscar una alerta por ID (sin restricción de fecha)</h2><form onSubmit={searchDirect} className="flex flex-wrap gap-2"><input className="rounded border p-2 text-sm" placeholder="ALT-123" required value={directId} onChange={e=>setDirectId(e.target.value)}/><button disabled={directLoading} className="rounded-lg border px-3 py-2 text-sm">{directLoading?'Consultando…':'Buscar ID'}</button></form>{directError&&<p role="alert" className="text-sm text-red-700">{directError}</p>}{directResult&&<div className="space-y-2"><p className="font-medium">ALT-{directResult.id_alert} · {directResult.chamber_name} · {states[directResult.status]}</p><p className="text-sm">Responsable: {directResult.acknowledged_by||directResult.id_user_acknowledged||'—'} · Cerrada por: {directResult.resolved_by||directResult.id_user_resolved||'—'} · {formatDate(directResult.resolution_date)}</p><p className="text-sm">{directResult.message}</p><AuditoriaAlerta id={directResult.id_alert}/></div>}</section>
      <section aria-busy={loading} className="overflow-hidden rounded-lg border border-gray-100 bg-white shadow-sm">
        {loading && <p role="status" className="p-4 text-sm text-gray-500">Consultando alertas…</p>}
        {!page && !loading && <p className="p-8 text-center text-sm text-gray-500">El historial no se carga automáticamente. Presiona Consultar para visualizar los registros.</p>}
        {page && <>
          <div className="border-b border-gray-100 p-4 text-sm text-gray-500">
            Consulta: {formatDate(applied.date_from)} — {formatDate(applied.date_to)} · {states[applied.status] || 'Todos los estados'} · {severities[applied.severity] || 'Todas las severidades'}
          </div>
          {page.items.length === 0 ? <p className="p-8 text-center text-sm text-gray-500">No hay alertas para los filtros seleccionados.</p> : (
            <div className="overflow-x-auto"><table className="w-full text-left text-sm">
              <thead className="bg-gray-50 text-gray-500"><tr>{['Alerta', 'Cámara', 'Fecha', 'Severidad', 'Estado', 'Responsable', 'Cerrada por', 'Fecha de cierre', 'Descripción', 'Evidencia'].map((label) => <th key={label} scope="col" className="px-4 py-3 font-medium">{label}</th>)}</tr></thead>
              <tbody className="divide-y divide-gray-100">{page.items.map((alert) => <tr key={alert.id_alert}>
                <td className="whitespace-nowrap px-4 py-3 font-medium">ALT-{alert.id_alert}</td>
                <td className="px-4 py-3">{alert.chamber_name || 'Sin cámara'}</td>
                <td className="whitespace-nowrap px-4 py-3">{formatDate(alert.generation_date)}</td>
                <td className="px-4 py-3">{severities[alert.severity] || alert.severity}</td>
                <td className="px-4 py-3"><span className={`rounded-full px-2 py-1 text-xs ${stateClass[alert.status] || 'bg-gray-100'}`}>{states[alert.status] || alert.status}</span></td>
                <td className="px-4 py-3 break-all">{alert.acknowledged_by || alert.id_user_acknowledged || '—'}</td>
                <td className="px-4 py-3 break-all">{alert.resolved_by || alert.id_user_resolved || '—'}</td>
                <td className="px-4 py-3 whitespace-nowrap">{formatDate(alert.resolution_date)}</td>
                <td className="max-w-md break-words px-4 py-3 text-gray-600">{alert.message || alert.alert_type || '—'}</td>
                <td className="px-4 py-3"><button type="button" className="rounded border px-2 py-1 text-xs" onClick={()=>setAuditId(auditId===alert.id_alert?null:alert.id_alert)}>{auditId===alert.id_alert?'Ocultar':'Ver auditoría'}</button></td>
              </tr>)}</tbody>
            </table></div>
          )}
          {auditId!==null&&<div className="p-4"><AuditoriaAlerta key={auditId} id={auditId}/></div>}
          <div className="border-t p-4 text-sm"><button type="button" disabled={loading||exporting} onClick={exportReport} className="rounded-lg bg-green-600 px-4 py-2 text-white disabled:opacity-50">{exporting?'Generando…':'Exportar consulta completa (CSV)'}</button><p className="mt-2 text-xs text-gray-500">Máximo 1000 alertas por reporte. Incluye ID, responsable, cierre y evidencia. Se exporta el período aplicado, no solo la página visible.</p>{exportError&&<p role="alert" className="mt-2 text-red-700">{exportError}</p>}</div>
          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-gray-100 p-4 text-sm">
            <span className="text-gray-500">Página {cursors.length} · {page.items.length} registros</span>
            <div className="flex gap-2">
              <button type="button" disabled={loading || cursors.length === 1} onClick={() => fetchPage(applied, cursors.slice(0, -1))} className="rounded-lg border px-4 py-2 disabled:opacity-40">Anterior</button>
              <button type="button" disabled={loading || !page.next_cursor} onClick={() => fetchPage(applied, [...cursors, page.next_cursor])} className="rounded-lg border px-4 py-2 disabled:opacity-40">Siguiente</button>
            </div>
          </div>
        </>}
      </section>
      <p className="text-xs text-gray-500">El reconocimiento y resolución de alertas corresponde al perfil técnico. Esta página es de solo consulta.</p>
    </div>
  );
}