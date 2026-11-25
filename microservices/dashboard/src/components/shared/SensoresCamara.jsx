import { useEffect, useRef, useState } from 'react';
import { Cpu, RefreshCw, X, Pencil, Plus, Activity } from 'lucide-react';
import {
  listarSensores,
  guardarSensor,
  diagnosticarSensor,
  detalleError,
} from '../../api/sensores';
import { formatDate } from '../../utils/formatters';

const empty = {
  sensor_type: '',
  mqtt_identifier: '',
  model: '',
  mcu_id: '',
  firmware: '',
  last_calibration: '',
  status: 'active',
};

const fields = [
  ['sensor_type', 'Tipo de sensor', 50],
  ['mqtt_identifier', 'Identificador MQTT', 100],
  ['model', 'Modelo', 50],
  ['mcu_id', 'Microcontrolador', 50],
  ['firmware', 'Firmware', 50],
];

const states = {
  active: 'Activo',
  inactive: 'Inactivo',
  maintenance: 'En mantenimiento',
};

const btn = 'rounded-lg border px-3 py-2 text-sm disabled:opacity-50';
const input = 'w-full rounded-lg border border-gray-200 px-3 py-2 text-sm';

export default function SensoresCamara({
  chamberId,
  chamberName,
  canManage = false,
  onClose,
  onSelect,
  selectedId,
}) {
  const [page, setPage] = useState(null);
  const [cursors, setCursors] = useState([0]);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(empty);
  const [diagnostic, setDiagnostic] = useState(null);

  const seq = useRef(0);
  const diagSeq = useRef(0);

  const load = async (stack) => {
    const request = ++seq.current;
    setLoading(true);
    setError('');

    try {
      const result = await listarSensores(chamberId, stack.at(-1));
      if (request === seq.current) {
        setPage(result);
        setCursors(stack);
      }
    } catch (e) {
      if (request === seq.current) {
        setError(detalleError(e));
        setPage(null);
      }
    } finally {
      if (request === seq.current) setLoading(false);
    }
  };

  useEffect(() => {
    setPage(null);
    setDiagnostic(null);
    setEditing(null);
    setForm(empty);
    load([0]);

    return () => {
      ++seq.current;
      ++diagSeq.current;
    };
  }, [chamberId]); // eslint-disable-line react-hooks/exhaustive-deps

  const start = (sensor) => {
    setEditing(sensor?.id_sensor ?? 'new');
    setForm(
      sensor
        ? Object.fromEntries(
            Object.keys(empty).map((k) => [k, sensor[k] ?? empty[k]])
          )
        : empty
    );
    setError('');
  };

  const save = async (event) => {
    event.preventDefault();
    if (busy) return;

    setBusy(true);
    setError('');

    try {
      await guardarSensor(
        chamberId,
        editing === 'new' ? null : editing,
        { ...form, last_calibration: form.last_calibration || null }
      );
      setEditing(null);
      setDiagnostic(null);
      await load([0]);
    } catch (e) {
      setError(detalleError(e));
    } finally {
      setBusy(false);
    }
  };

  const inspect = async (sensor) => {
    const request = ++diagSeq.current;
    setDiagnostic({ loading: true });
    setError('');

    try {
      const result = await diagnosticarSensor(chamberId, sensor.id_sensor);
      if (request === diagSeq.current) setDiagnostic(result);
    } catch (e) {
      if (request === diagSeq.current) {
        setDiagnostic(null);
        setError(detalleError(e));
      }
    }
  };

  return (
    <section className="space-y-4 rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
      <header className="flex flex-wrap items-center gap-2">
        <Cpu className="text-green-600" />
        <div className="flex-1">
          <h2 className="font-semibold text-gray-800">
            Sensores · {chamberName}
          </h2>
          <p className="text-xs text-gray-500">
            Inventario real de esta cámara. No se elimina el historial.
          </p>
        </div>

        <button
          type="button"
          disabled={loading || busy}
          onClick={() => load(cursors)}
          className={btn}
        >
          <RefreshCw size={16} />
        </button>

        {canManage && (
          <button
            type="button"
            disabled={busy || loading}
            onClick={() => start(null)}
            className="flex items-center gap-1 rounded-lg bg-green-600 px-3 py-2 text-sm text-white"
          >
            <Plus size={16} /> Registrar sensor
          </button>
        )}

        {onClose && (
          <button
            type="button"
            disabled={busy}
            onClick={onClose}
            aria-label="Cerrar sensores"
            className={btn}
          >
            <X size={16} />
          </button>
        )}
      </header>

      {error && (
        <p role="alert" className="rounded bg-red-50 p-3 text-sm text-red-700">
          {error}
        </p>
      )}

      {editing !== null && (
        <form
          onSubmit={save}
          className="grid gap-3 rounded-lg bg-gray-50 p-4 md:grid-cols-2"
        >
          <h3 className="font-medium md:col-span-2">
            {editing === 'new' ? 'Nuevo sensor' : `Editar sensor #${editing}`}
          </h3>

          {fields.map(([key, label, max]) => (
            <label key={key} className="text-sm">
              {label}
              <input
                className={input}
                required={key === 'sensor_type' || key === 'mqtt_identifier'}
                maxLength={max}
                value={form[key]}
                onChange={(e) => setForm({ ...form, [key]: e.target.value })}
              />
            </label>
          ))}

          <label className="text-sm">
            Última calibración
            <input
              type="date"
              className={input}
              value={form.last_calibration}
              onChange={(e) =>
                setForm({ ...form, last_calibration: e.target.value })
              }
            />
          </label>

          <label className="text-sm">
            Estado administrativo
            <select
              className={input}
              value={form.status}
              onChange={(e) => setForm({ ...form, status: e.target.value })}
            >
              {Object.entries(states).map(([v, l]) => (
                <option key={v} value={v}>
                  {l}
                </option>
              ))}
            </select>
          </label>

          <div className="flex items-end gap-2">
            <button
              disabled={busy}
              className="rounded-lg bg-green-600 px-4 py-2 text-sm text-white"
            >
              {busy ? 'Guardando…' : 'Guardar sensor'}
            </button>
            <button
              type="button"
              disabled={busy}
              className={btn}
              onClick={() => setEditing(null)}
            >
              Cancelar
            </button>
          </div>
        </form>
      )}

      {loading ? (
        <p className="text-sm text-gray-500">Consultando sensores…</p>
      ) : page?.items.length === 0 ? (
        <p className="text-sm text-gray-500">
          Esta cámara no tiene sensores registrados.
        </p>
      ) : (
        page && (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    {['ID / Tipo', 'MQTT / Modelo', 'Estado', 'Acciones'].map(
                      (x) => (
                        <th key={x} className="p-3">
                          {x}
                        </th>
                      )
                    )}
                  </tr>
                </thead>
                <tbody>
                  {page.items.map((s) => (
                    <tr key={s.id_sensor} className="border-t">
                      <td className="p-3 font-medium">
                        #{s.id_sensor}
                        <br />
                        {s.sensor_type || '—'}
                      </td>
                      <td className="p-3 break-all">
                        {s.mqtt_identifier || '—'}
                        <br />
                        <span className="text-gray-500">
                          {s.model || '—'}
                        </span>
                      </td>
                      <td className="p-3">
                        {states[s.status] || s.status || 'Sin estado'}
                      </td>
                      <td className="p-3">
                        <div className="flex flex-wrap gap-2">
                          <button
                            type="button"
                            className={btn}
                            onClick={() => inspect(s)}
                          >
                            <Activity size={14} className="inline" /> Diagnóstico
                          </button>

                          {canManage && (
                            <button
                              type="button"
                              disabled={busy}
                              className={btn}
                              onClick={() => start(s)}
                            >
                              <Pencil size={14} className="inline" /> Editar
                            </button>
                          )}

                          {onSelect && (
                            <button
                              type="button"
                              className={btn}
                              onClick={() => onSelect(s.id_sensor)}
                            >
                              {selectedId === s.id_sensor
                                ? 'Seleccionado'
                                : 'Sensor intervenido'}
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="flex items-center justify-between text-sm text-gray-500">
              <span>Página {cursors.length}</span>
              <div className="flex gap-2">
                <button
                  type="button"
                  className={btn}
                  disabled={cursors.length === 1 || busy}
                  onClick={() => load(cursors.slice(0, -1))}
                >
                  Anterior
                </button>
                <button
                  type="button"
                  className={btn}
                  disabled={!page.next_cursor || busy}
                  onClick={() => load([...cursors, page.next_cursor])}
                >
                  Siguiente
                </button>
              </div>
            </div>
          </>
        )
      )}

      {diagnostic &&
        (diagnostic.loading ? (
          <p>Consultando telemetría…</p>
        ) : (
          <div className="rounded-lg border bg-gray-50 p-4">
            <h3 className="font-semibold">
              Diagnóstico del sensor #{diagnostic.sensor.id_sensor}
            </h3>
            <p className="text-sm">
              Firmware: {diagnostic.sensor.firmware || '—'} · MCU:{' '}
              {diagnostic.sensor.mcu_id || '—'} · Calibración:{' '}
              {diagnostic.sensor.last_calibration || 'Sin registro'}
            </p>
            <p className="mt-2 text-sm">
              Última lectura identificada:{' '}
              {formatDate(diagnostic.last_reading?.timestamp)} · Temperatura:{' '}
              {diagnostic.last_reading?.temperature ?? '—'} °C · Potencia:{' '}
              {diagnostic.last_reading?.consumption_kw ?? '—'} kW
            </p>
            <p className="mt-2 text-xs text-gray-500">
              La ausencia de datos identificados no demuestra una falla física.
              No se atribuyen lecturas históricas sin id_sensor.
            </p>
            <div className="mt-2 max-h-56 overflow-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr>
                    <th>Fecha</th>
                    <th>Temperatura °C</th>
                    <th>Potencia kW</th>
                  </tr>
                </thead>
                <tbody>
                  {diagnostic.readings.map((r, i) => (
                    <tr key={i}>
                      <td>{formatDate(r.timestamp)}</td>
                      <td>{r.temperature ?? '—'}</td>
                      <td>{r.consumption_kw ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {!diagnostic.readings.length && (
                <p className="py-2 text-sm">
                  Sin lecturas identificadas en las últimas 24 h.
                </p>
              )}
            </div>
          </div>
        ))}
    </section>
  );
}