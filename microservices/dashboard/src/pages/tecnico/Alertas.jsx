import { useContext, useEffect, useRef, useState } from 'react';
import { AuthContext } from '../../context/AuthContext';
import {
  listarAlertasTecnicas,
  asumirAlerta,
  cerrarAlerta,
  obtenerAlerta,
} from '../../api/intervenciones';
import { detalleError } from '../../api/sensores';
import SensoresCamara from '../../components/shared/SensoresCamara';
import AuditoriaAlerta from '../../components/shared/AuditoriaAlerta';
import { formatDate } from '../../utils/formatters';
import { RefreshCw, AlertTriangle, Search } from 'lucide-react';

const states = {
  active: 'Pendiente',
  acknowledged: 'En atención',
  resolved: 'Resuelta',
};

const severity = {
  low: 'Baja',
  medium: 'Media',
  high: 'Alta',
  critical: 'Crítica',
};

const actions = [
  'Revisión del sensor',
  'Calibración del sensor',
  'Reparación de conectividad',
  'Reemplazo de sensor',
  'Revisión del sistema frigorífico',
  'Corrección de temperatura',
  'Otra intervención',
];

const btn = 'rounded-lg border px-3 py-2 text-sm disabled:opacity-50';
const green =
  'rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50';

export default function Alertas() {
  const { user } = useContext(AuthContext);

  const [tab, setTab] = useState('active');
  const [page, setPage] = useState(0);
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [detail, setDetail] = useState(null);
  const [detailError, setDetailError] = useState('');
  const [note, setNote] = useState('');
  const [action, setAction] = useState(actions[0]);
  const [sensorId, setSensorId] = useState(null);
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('');
  const [audit, setAudit] = useState(false);
  const [sensors, setSensors] = useState(false);

  const req = useRef(0);

  const load = async () => {
    const n = ++req.current;
    setLoading(true);
    setError('');

    try {
      const data = await listarAlertasTecnicas({
        status: tab,
        limit: 21,
        offset: page * 20,
        ...(tab === 'acknowledged' ? { mine: true } : {}),
        ...(filter ? { id_alert: filter } : {}),
      });
      if (n === req.current) setRows(data);
    } catch (e) {
      if (n === req.current) {
        setRows([]);
        setError(detalleError(e));
      }
    } finally {
      if (n === req.current) setLoading(false);
    }
  };

  useEffect(() => {
    load();
    return () => {
      ++req.current;
    };
  }, [tab, page, filter]); // eslint-disable-line react-hooks/exhaustive-deps

  const choose = (a) => {
    setDetail(a);
    setDetailError('');
    setNote('');
    setAction(actions[0]);
    setSensorId(null);
    setAudit(false);
    setSensors(false);
  };

  const update = async (kind) => {
    if (!detail || busy) return;

    setBusy(true);
    setDetailError('');

    try {
      const next =
        kind === 'claim'
          ? await asumirAlerta(detail.id_alert)
          : await cerrarAlerta(detail.id_alert, {
              note: note.trim(),
              intervention: action,
              id_sensor: sensorId,
            });
      setDetail(next);
      setNote('');
      setAudit(kind === 'close');
      await load();
    } catch (e) {
      setDetailError(detalleError(e));
      try {
        setDetail(await obtenerAlerta(detail.id_alert));
      } catch {
        /* conserva el mensaje original */
      }
      await load();
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">
            Alertas HACCP · Gestión técnica
          </h1>
          <p className="text-sm text-gray-500">
            Asume una alerta, diagnostica la cámara y registra evidencia del
            cierre.
          </p>
        </div>
        <button className={btn} disabled={loading || busy} onClick={load}>
          <RefreshCw size={16} className="inline" /> Actualizar
        </button>
      </header>

      <div className="flex flex-wrap gap-2">
        {[
          ['active', 'Pendientes'],
          ['acknowledged', 'Mis alertas en atención'],
          ['resolved', 'Resueltas'],
        ].map(([v, l]) => (
          <button
            key={v}
            className={tab === v ? green : btn}
            disabled={busy}
            onClick={() => {
              setTab(v);
              setPage(0);
              setDetail(null);
            }}
          >
            {l}
          </button>
        ))}
      </div>

      <form
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          const id = search.trim().replace(/^ALT-/i, '');
          if (id && !/^[1-9]\d*$/.test(id)) {
            setError('Ingresa un ID de alerta válido.');
            return;
          }
          setFilter(id);
          setPage(0);
        }}
      >
        <input
          className="rounded-lg border px-3 py-2 text-sm"
          placeholder="ID de alerta (ALT-123)"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <button className={btn}>
          <Search size={16} className="inline" /> Buscar
        </button>
      </form>

      {error && (
        <p role="alert" className="rounded bg-red-50 p-3 text-red-700">
          {error}
        </p>
      )}

      <section className="overflow-x-auto rounded-xl bg-white shadow-sm">
        {loading ? (
          <p className="p-4">Consultando alertas…</p>
        ) : !rows.length ? (
          <p className="p-4 text-gray-500">
            No hay alertas para esta consulta.
          </p>
        ) : (
          <table className="w-full text-left text-sm">
            <thead className="bg-gray-50">
              <tr>
                {[
                  'ID / Fecha',
                  'Cámara',
                  'Severidad',
                  'Estado',
                  'Responsable',
                  'Acción',
                ].map((x) => (
                  <th key={x} className="p-3">
                    {x}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.slice(0, 20).map((a) => (
                <tr key={a.id_alert} className="border-t">
                  <td className="p-3 font-medium">
                    ALT-{a.id_alert}
                    <br />
                    <span className="text-xs font-normal text-gray-500">
                      {formatDate(a.generation_date)}
                    </span>
                  </td>
                  <td className="p-3">{a.chamber_name}</td>
                  <td className="p-3">{severity[a.severity]}</td>
                  <td className="p-3">{states[a.status]}</td>
                  <td className="p-3">
                    {a.acknowledged_by || a.id_user_acknowledged || 'Sin asignar'}
                  </td>
                  <td className="p-3">
                    <button
                      className={btn}
                      disabled={busy}
                      onClick={() => choose(a)}
                    >
                      Ver detalle
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        <div className="flex items-center justify-between border-t p-3 text-sm">
          <span>Página {page + 1} · Máximo 20 alertas</span>
          <div className="flex gap-2">
            <button
              className={btn}
              disabled={page === 0 || loading || busy}
              onClick={() => setPage((p) => p - 1)}
            >
              Anterior
            </button>
            <button
              className={btn}
              disabled={rows.length <= 20 || loading || busy}
              onClick={() => setPage((p) => p + 1)}
            >
              Siguiente
            </button>
          </div>
        </div>
      </section>

      {detail && (
        <section className="space-y-4 rounded-xl bg-white p-5 shadow-sm">
          <div className="flex justify-between">
            <h2 className="text-lg font-semibold">
              <AlertTriangle className="inline text-amber-600" /> ALT-
              {detail.id_alert} · {detail.chamber_name}
            </h2>
            <button
              className={btn}
              disabled={busy}
              onClick={() => setDetail(null)}
            >
              Cerrar detalle
            </button>
          </div>

          <p className="text-sm">{detail.message || detail.alert_type}</p>
          <p className="text-sm">
            Estado: {states[detail.status]} · Responsable:{' '}
            {detail.acknowledged_by || detail.id_user_acknowledged || 'Sin asignar'}{' '}
            · Cerrada por:{' '}
            {detail.resolved_by || detail.id_user_resolved || '—'}
          </p>

          <div className="flex flex-wrap gap-2">
            <button
              className={btn}
              disabled={!detail.id_chamber}
              onClick={() => setSensors((v) => !v)}
            >
              {sensors ? 'Ocultar sensores' : 'Diagnosticar sensores de la cámara'}
            </button>
            <button className={btn} onClick={() => setAudit((v) => !v)}>
              {audit ? 'Ocultar auditoría' : 'Ver auditoría'}
            </button>
          </div>

          {sensors && (
            <SensoresCamara
              key={detail.id_chamber}
              chamberId={detail.id_chamber}
              chamberName={detail.chamber_name}
              selectedId={sensorId}
              onSelect={
                detail.status === 'acknowledged' &&
                detail.id_user_acknowledged === user?.id
                  ? setSensorId
                  : undefined
              }
            />
          )}

          {detailError && (
            <p role="alert" className="rounded bg-red-50 p-3 text-sm text-red-700">
              {detailError}
            </p>
          )}

          {detail.status === 'active' && (
            <button
              className={green}
              disabled={busy}
              onClick={() => update('claim')}
            >
              Hacerme cargo de esta alerta
            </button>
          )}

          {detail.status === 'acknowledged' &&
            (detail.id_user_acknowledged === user?.id ? (
              <form
                className="space-y-3 rounded-lg bg-gray-50 p-4"
                onSubmit={(e) => {
                  e.preventDefault();
                  update('close');
                }}
              >
                <h3 className="font-semibold">Registrar intervención y resolver</h3>

                <label className="block text-sm">
                  Acción realizada
                  <select
                    className="mt-1 w-full rounded border p-2"
                    value={action}
                    onChange={(e) => setAction(e.target.value)}
                  >
                    {actions.map((a) => (
                      <option key={a}>{a}</option>
                    ))}
                  </select>
                </label>

                <p className="text-sm">
                  Sensor intervenido:{' '}
                  {sensorId ? `#${sensorId}` : 'No identificado / no aplica'}{' '}
                  {sensorId && (
                    <button
                      type="button"
                      onClick={() => setSensorId(null)}
                      className="underline"
                    >
                      Quitar
                    </button>
                  )}
                </p>
                <p className="text-xs text-gray-500">
                  Selecciona un sensor en Diagnóstico solo si efectivamente fue
                  intervenido.
                </p>

                <label className="block text-sm">
                  Evidencia de cierre (obligatoria)
                  <textarea
                    required
                    minLength={15}
                    maxLength={500}
                    rows={4}
                    className="mt-1 w-full rounded border p-2"
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    placeholder="Problema encontrado, acción realizada y cómo comprobaste la solución."
                  />
                </label>
                <p className="text-xs text-gray-500">
                  {note.trim().length}/500 caracteres. Mínimo 15.
                </p>

                <button
                  className={green}
                  disabled={busy || note.trim().length < 15}
                >
                  Resolver y guardar evidencia
                </button>
              </form>
            ) : (
              <p className="text-sm text-gray-500">
                Solo el técnico responsable puede cerrar esta alerta.
              </p>
            ))}

          {audit && (
            <AuditoriaAlerta
              key={`${detail.id_alert}-${detail.status}`}
              id={detail.id_alert}
            />
          )}
        </section>
      )}
    </div>
  );
}