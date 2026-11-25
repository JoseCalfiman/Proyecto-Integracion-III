import { useEffect, useState } from 'react';
import { obtenerAuditoria } from '../../api/intervenciones';
import { detalleError } from '../../api/sensores';
import { formatDate } from '../../utils/formatters';

export default function AuditoriaAlerta({ id }) {
  const [rows, setRows] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    setRows(null);
    setError('');

    obtenerAuditoria(id)
      .then((r) => {
        if (active) setRows(r);
      })
      .catch((e) => {
        if (active) setError(detalleError(e));
      });

    return () => {
      active = false;
    };
  }, [id]);

  return (
    <section className="space-y-2 rounded-lg border bg-gray-50 p-4">
      <h3 className="font-semibold">Auditoría · ALT-{id}</h3>

      {error ? (
        <p role="alert" className="text-sm text-red-700">
          {error}
        </p>
      ) : !rows ? (
        <p className="text-sm">Cargando intervenciones…</p>
      ) : rows.length === 0 ? (
        <p className="text-sm">No existen intervenciones registradas.</p>
      ) : (
        rows.map((r) => (
          <div
            key={r.id_audit}
            className="rounded border bg-white p-3 text-sm"
          >
            <p className="font-medium">
              {r.action === 'resolved'
                ? 'Resolución'
                : r.action === 'acknowledged'
                  ? 'Atención asumida'
                  : r.action}{' '}
              · {r.user_name || r.id_user || 'Sin usuario'}
            </p>
            <p className="text-xs text-gray-500">{formatDate(r.action_date)}</p>
            <p className="mt-2 whitespace-pre-wrap break-words">
              {r.detail || 'Sin evidencia registrada'}
            </p>
          </div>
        ))
      )}

      <p className="text-xs text-gray-500">
        Hasta las últimas 100 acciones de la alerta.
      </p>
    </section>
  );
}