import { useEffect, useState } from 'react';
import { getCamaras } from '../../api/camaras';
import { getUltimaPrediccion } from '../../api/predicciones';

const numero = (value) => value == null || !Number.isFinite(Number(value))
  ? '—' : Number(value).toLocaleString('es-CL', { maximumFractionDigits: 3 });
const fecha = (value) => value && !Number.isNaN(Date.parse(value))
  ? new Date(value).toLocaleString('es-CL') : 'Sin fecha disponible';
const CONDICIONES = {
  VENTANA_INSUFICIENTE: 'Datos insuficientes para estimar una tendencia.',
  DATOS_VARIABLES: 'Las temperaturas presentan dispersión elevada en esta ventana.',
  CON_ATIPICOS: 'Hay lecturas atípicas registradas para revisión.',
};
const METRICAS = [
  ['sample_count', 'Muestras'], ['media', 'Media'], ['mediana', 'Mediana'],
  ['std', 'Desviación muestral'], ['min', 'Mínimo'], ['max', 'Máximo'],
  ['q1', 'Q1'], ['q3', 'Q3'], ['iqr', 'IQR'],
];

export default function PredictionDiagnostics({ idChamber, detailed = false }) {
  const [camaras, setCamaras] = useState([]);
  const [seleccion, setSeleccion] = useState('');
  const [errorCamaras, setErrorCamaras] = useState(null);
  const [estado, setEstado] = useState(null);
  const [recarga, setRecarga] = useState(0);
  const id = idChamber ?? seleccion;

  useEffect(() => {
    if (idChamber !== undefined) return undefined;
    let vigente = true;
    getCamaras().then((lista) => {
      if (!vigente) return;
      setCamaras(lista);
      setErrorCamaras(null);
      setSeleccion((actual) => lista.some((c) => c.id === actual) ? actual : lista[0]?.id || '');
    }).catch((error) => {
      if (vigente) setErrorCamaras(error.message);
    });
    return () => { vigente = false; };
  }, [idChamber, recarga]);

  useEffect(() => {
    if (!id) return undefined;
    let vigente = true;
    let timeout;
    const actualizar = async () => {
      try {
        const prediccion = await getUltimaPrediccion(id);
        if (vigente) setEstado({ id, prediccion, error: null });
      } catch (error) {
        if (vigente) setEstado({ id, prediccion: null, error: error.message });
      } finally {
        if (vigente) timeout = setTimeout(actualizar, 15000);
      }
    };
    actualizar();
    return () => { vigente = false; clearTimeout(timeout); };
  }, [id, recarga]);

  const actual = estado?.id === id ? estado : null;
  const prediccion = actual?.prediccion;
  const diagnostico = prediccion?.diagnostico;
  const insuficiente = diagnostico?.condiciones.includes('VENTANA_INSUFICIENTE');
  const fechaLectura = Date.parse(diagnostico?.recorded_at);
  const atrasado = Number.isFinite(fechaLectura) && Date.now() - fechaLectura > 120000;

  return (
    <section className="my-6 rounded-xl border border-gray-200 bg-white p-5" aria-label="Calidad de la ventana predictiva">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-gray-800">Calidad de datos y tendencia por cámara</h2>
          <p className="text-sm text-gray-600">Ventana analizada por el Predictor · Actualización cada 15 segundos</p>
        </div>
        <button type="button" onClick={() => setRecarga((n) => n + 1)}
          className="rounded border border-gray-300 px-3 py-2 text-sm">Actualizar</button>
      </div>
      {idChamber === undefined && (
        <label className="mt-4 block text-sm">
          Cámara
          <select value={seleccion} onChange={(event) => setSeleccion(event.target.value)}
            className="ml-2 max-w-full rounded border border-gray-300 p-2">
            {!camaras.length && <option value="">Sin cámaras disponibles</option>}
            {camaras.map((camara) => <option key={camara.id} value={camara.id}>{camara.nombre || camara.id}</option>)}
          </select>
        </label>
      )}
      <div aria-live="polite" className="mt-4">
        {errorCamaras && <p role="alert" className="text-amber-800">{errorCamaras}</p>}
        {id && !actual && <p>Consultando la última predicción…</p>}
        {actual?.error && <p role="alert" className="text-amber-800">{actual.error}</p>}
        {prediccion && !diagnostico && <p>Esta predicción es anterior al diagnóstico estadístico. Se mostrará cuando el Predictor procese nuevas lecturas.</p>}
        {diagnostico && (
          <>
            <p className="text-sm text-gray-600">Última lectura de la ventana: {fecha(diagnostico.recorded_at)} · Cálculo: {fecha(prediccion.calculation_date)}</p>
            {atrasado && <p className="mt-2 text-amber-800">Las lecturas tienen más de dos minutos de antigüedad. Comprueba el envío del sensor.</p>}
            <div className="mt-3 rounded-lg bg-gray-50 p-3">
              {diagnostico.condiciones.length
                ? diagnostico.condiciones.map((condicion) => <p key={condicion}>{CONDICIONES[condicion] || condicion}</p>)
                : <p>Ventana suficiente, con baja dispersión y sin atípicos detectados.</p>}
              <p className="mt-2 text-sm">{diagnostico.sample_count} muestras recibidas · {diagnostico.usable_sample_count} utilizables · {numero(diagnostico.span_minutes)} min · {diagnostico.outlier_count} atípicas</p>
            </div>
            <div className="mt-4 grid gap-3 sm:grid-cols-3">
              <p>Pendiente <strong>{numero(prediccion.slope)} °C/min</strong></p>
              <p>Tiempo hasta el límite <strong>{numero(prediccion.remaining_time_min)} min</strong></p>
              <p>{insuficiente ? 'Evaluación pendiente por datos insuficientes' : `Nivel predictivo: ${prediccion.risk_level}`}</p>
            </div>
            <p className="mt-2 text-xs text-gray-600">Tiempo estimado desde la última lectura aceptada: {fecha(diagnostico.reference_timestamp)}.</p>
            <p className="mt-1 text-xs text-gray-600">Límite de temperatura: {numero(diagnostico.absolute_max_temp)} °C · Umbral de alerta: {numero(diagnostico.umbral_alerta_minutos)} min.</p>
            <div className="mt-4 overflow-x-auto">
              <table className="w-full text-left text-sm">
                <caption className="mb-2 text-left text-gray-600">Estadísticas de la ventana original, incluyendo atípicos</caption>
                <thead><tr><th className="p-2">Métrica</th><th className="p-2">Temperatura (°C)</th><th className="p-2">Potencia (kW)</th></tr></thead>
                <tbody>{METRICAS.map(([clave, etiqueta]) => (
                  <tr key={clave} className="border-t border-gray-100"><th className="p-2 font-normal">{etiqueta}</th>
                    <td className="p-2">{numero(diagnostico.temperature?.[clave])}</td>
                    <td className="p-2">{numero(diagnostico.consumption_kw?.[clave])}</td></tr>
                ))}</tbody>
              </table>
            </div>
            <p className="mt-2 text-xs text-gray-600">La desviación es muestral (n − 1). El resumen histórico por fechas usa desviación poblacional (n).</p>
            {detailed && (
              <details className="mt-4">
                <summary className="cursor-pointer font-medium">Criterios y lecturas atípicas</summary>
                <p className="mt-2 text-sm">Variabilidad desde {numero(diagnostico.umbral_std_temp)} °C de desviación. Atípicos fuera de Q1 − {numero(diagnostico.factor_iqr)} × IQR y Q3 + {numero(diagnostico.factor_iqr)} × IQR.</p>
                <ul className="mt-2 list-inside list-disc text-sm">
                  {diagnostico.outliers.map((lectura) => <li key={lectura.index}>Lectura {lectura.index + 1} · {fecha(lectura.timestamp)} · {numero(lectura.temperature)} °C</li>)}
                </ul>
                {!diagnostico.outliers.length && <p className="text-sm">Sin lecturas atípicas en esta ventana.</p>}
              </details>
            )}
          </>
        )}
      </div>
    </section>
  );
}
