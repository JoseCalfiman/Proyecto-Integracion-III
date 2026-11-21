import React, { useEffect, useMemo, useState } from 'react';
import PredictionDiagnostics from '../../components/shared/PredictionDiagnostics';
import {
  Activity,
  AlertTriangle,
  Clock3,
  RefreshCw,
  Thermometer,
  TrendingDown,
  TrendingUp,
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
import {
  getAlertasDiagnostico,
  getLecturasDiagnostico,
  getPrediccionesDiagnostico,
  getReglaDiagnostico,
} from '../../api/diagnosticoCamara';
import {
  calcularEstadisticasTemperatura,
  nivelRiesgoTexto,
  prepararSerieGrafico,
  tendenciaDesdePendiente,
} from '../../utils/diagnosticoCamara';

const numero = (value, digits = 2) => {
  if (value == null || value === '' || !Number.isFinite(Number(value))) return '—';
  return Number(value).toLocaleString('es-CL', { maximumFractionDigits: digits });
};

const fecha = (value) => {
  if (!value || Number.isNaN(Date.parse(value))) return 'Fecha no informada';
  return new Date(value).toLocaleString('es-CL');
};

const riesgoClase = (riskLevel) => {
  const value = String(riskLevel || '').toLowerCase();
  if (['critical', 'critico', 'crítico'].includes(value)) return 'border-red-200 bg-red-50 text-red-800';
  if (['high', 'alto'].includes(value)) return 'border-orange-200 bg-orange-50 text-orange-800';
  if (['medium', 'medio'].includes(value)) return 'border-amber-200 bg-amber-50 text-amber-800';
  if (['low', 'bajo', 'sin_riesgo'].includes(value)) return 'border-green-200 bg-green-50 text-green-800';
  return 'border-gray-200 bg-gray-50 text-gray-700';
};

const EstadoSeccion = ({ loading, error, empty, emptyText, children }) => {
  if (loading) return <p className="py-4 text-sm text-gray-500" role="status">Consultando servicio…</p>;
  if (error) {
    return (
      <div className="flex gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900" role="alert">
        <AlertTriangle size={18} className="mt-0.5 shrink-0" />
        <span>{error}</span>
      </div>
    );
  }
  if (empty) return <p className="py-4 text-sm text-gray-500">{emptyText}</p>;
  return children;
};

const TarjetaMetrica = ({ etiqueta, valor, unidad, detalle }) => (
  <article className="rounded-lg border border-gray-200 bg-white p-4">
    <p className="text-xs font-medium uppercase tracking-wide text-gray-500">{etiqueta}</p>
    <p className="mt-2 text-2xl font-semibold text-gray-800">
      {valor} <span className="text-sm font-normal text-gray-500">{unidad}</span>
    </p>
    {detalle && <p className="mt-1 text-xs text-gray-500">{detalle}</p>}
  </article>
);

const DiagnosticoCamara = ({ camaras = [] }) => {
  const [idSeleccionado, setIdSeleccionado] = useState(camaras[0]?.id || '');
  const [recarga, setRecarga] = useState(0);
  const [cargando, setCargando] = useState(false);
  const [errores, setErrores] = useState({});
  const [datos, setDatos] = useState({
    lecturas: null,
    predicciones: null,
    regla: null,
    alertas: null,
  });

  useEffect(() => {
    if (!camaras.length) {
      setIdSeleccionado('');
      return;
    }
    if (!camaras.some((camara) => camara.id === idSeleccionado)) {
      setIdSeleccionado(camaras[0].id);
    }
  }, [camaras, idSeleccionado]);

  useEffect(() => {
    if (!idSeleccionado) {
      setCargando(false);
      setDatos({ lecturas: null, predicciones: null, regla: null, alertas: null });
      setErrores({});
      return undefined;
    }

    let vigente = true;
    setCargando(true);
    setErrores({});
    setDatos({ lecturas: null, predicciones: null, regla: null, alertas: null });

    const solicitudes = [
      ['lecturas', getLecturasDiagnostico(idSeleccionado)],
      ['predicciones', getPrediccionesDiagnostico(idSeleccionado)],
      ['regla', getReglaDiagnostico(idSeleccionado)],
      ['alertas', getAlertasDiagnostico(idSeleccionado)],
    ];

    Promise.allSettled(solicitudes.map(([, promesa]) => promesa)).then((resultados) => {
      if (!vigente) return;
      const nuevosDatos = {};
      const nuevosErrores = {};

      resultados.forEach((resultado, index) => {
        const clave = solicitudes[index][0];
        if (resultado.status === 'fulfilled') {
          nuevosDatos[clave] = resultado.value;
        } else {
          nuevosDatos[clave] = null;
          nuevosErrores[clave] = resultado.reason?.message || 'Error desconocido al consultar el servicio';
        }
      });

      setDatos(nuevosDatos);
      setErrores(nuevosErrores);
      setCargando(false);
    });

    return () => {
      vigente = false;
    };
  }, [idSeleccionado, recarga]);

  const camara = camaras.find((item) => item.id === idSeleccionado);
  const lecturas = datos.lecturas || [];
  const estadisticas = useMemo(
    () => calcularEstadisticasTemperatura(lecturas),
    [lecturas],
  );
  const serie = useMemo(() => prepararSerieGrafico(lecturas), [lecturas]);
  const prediccion = datos.predicciones?.[0] || null;
  const pendiente = prediccion?.slope ?? prediccion?.calculated_slope ?? prediccion?.slope_per_minute;
  const riesgo = prediccion?.risk_level;
  const alertas = datos.alertas || [];
  const lecturasRecientes = useMemo(
    () => [...(estadisticas ? estadisticas.outliers : [])].slice(-5).reverse(),
    [estadisticas],
  );

  const tendencia = tendenciaDesdePendiente(pendiente);
  const iconoTendencia = Number(pendiente) > 0.01
    ? <TrendingUp size={17} />
    : Number(pendiente) < -0.01 ? <TrendingDown size={17} /> : <Activity size={17} />;

  return (
    <section className="space-y-5 rounded-xl border border-gray-200 bg-gray-50 p-4 md:p-6" aria-label="Diagnóstico individual por cámara">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-gray-800">Diagnóstico por cámara</h2>
          <p className="mt-1 text-sm text-gray-500">
            Lecturas reales de las últimas 24 horas, estadísticas, predicción, regla HACCP y alertas de la cámara seleccionada.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setRecarga((value) => value + 1)}
          disabled={!idSeleccionado || cargando}
          className="inline-flex items-center gap-2 rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <RefreshCw size={15} className={cargando ? 'animate-spin' : ''} />
          Actualizar diagnóstico
        </button>
      </div>

      {!camaras.length ? (
        <p className="rounded-lg border border-gray-200 bg-white p-4 text-sm text-gray-600">
          No hay cámaras disponibles para diagnosticar. La lista proviene del endpoint real de cámaras del Panel Técnico.
        </p>
      ) : (
        <>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-[minmax(0,1fr)_2fr] md:items-end">
            <label className="block">
              <span className="mb-1 block text-sm font-medium text-gray-700">Seleccionar cámara</span>
              <select
                value={idSeleccionado}
                onChange={(event) => setIdSeleccionado(event.target.value)}
                className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-800 outline-none focus:border-green-600 focus:ring-2 focus:ring-green-100"
              >
                {camaras.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.nombre} · {item.id}
                  </option>
                ))}
              </select>
            </label>
            <p className="text-xs text-gray-500">
              {camara?.ubicacion ? `Ubicación: ${camara.ubicacion}. ` : ''}
              Los datos se solicitan filtrando por el identificador UUID de esta cámara.
            </p>
          </div>

          <div className="space-y-5">
            <PredictionDiagnostics idChamber={idSeleccionado} detailed />
            <section className="space-y-3" aria-label="Estadísticas de temperatura">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="font-semibold text-gray-800">Estadísticas de temperatura</h3>
                <span className="text-xs text-gray-500">Calculadas sobre las lecturas devueltas por /historial</span>
              </div>
              <EstadoSeccion
                loading={cargando}
                error={errores.lecturas}
                empty={!errores.lecturas && datos.lecturas !== null && !estadisticas}
                emptyText="Esta cámara no tiene lecturas de temperatura en las últimas 24 horas."
              >
                {estadisticas && (
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-5">
                    <TarjetaMetrica etiqueta="Media" valor={numero(estadisticas.mean)} unidad="°C" detalle={`${estadisticas.count} lecturas válidas`} />
                    <TarjetaMetrica etiqueta="Mediana" valor={numero(estadisticas.median)} unidad="°C" />
                    <TarjetaMetrica etiqueta="Desv. estándar" valor={numero(estadisticas.standardDeviation)} unidad="°C" detalle="Poblacional (divide por N)" />
                    <TarjetaMetrica etiqueta="Rango intercuartílico" valor={numero(estadisticas.iqr)} unidad="°C" detalle={`Q1 ${numero(estadisticas.q1)} · Q3 ${numero(estadisticas.q3)}`} />
                    <TarjetaMetrica etiqueta="Valores atípicos" valor={String(estadisticas.outliers.length)} unidad="" detalle="Regla de Tukey · 1,5 × IQR" />
                  </div>
                )}
              </EstadoSeccion>
            </section>

            <section className="rounded-lg border border-gray-200 bg-white p-4" aria-label="Tendencia de temperatura">
              <div className="mb-3 flex items-center gap-2">
                <Thermometer size={18} className="text-green-700" />
                <h3 className="font-semibold text-gray-800">Evolución de temperatura · 24 horas</h3>
              </div>
              <EstadoSeccion
                loading={cargando}
                error={errores.lecturas}
                empty={!errores.lecturas && datos.lecturas !== null && serie.length === 0}
                emptyText="No existen puntos suficientes para graficar la temperatura de esta cámara."
              >
                {serie.length > 0 && (
                  <>
                    <div style={{ width: '100%', height: 250 }}>
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={serie} margin={{ top: 8, right: 16, left: 0, bottom: 4 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                          <XAxis dataKey="hora" minTickGap={28} tick={{ fontSize: 11 }} stroke="#6b7280" />
                          <YAxis width={58} unit=" °C" tick={{ fontSize: 11 }} stroke="#6b7280" domain={['auto', 'auto']} />
                          <Tooltip
                            labelFormatter={(_, payload) => payload?.[0]?.payload?.timestamp ? fecha(payload[0].payload.timestamp) : ''}
                            formatter={(value) => [`${numero(value)} °C`, 'Temperatura']}
                          />
                          <Line type="monotone" dataKey="temperatura" name="Temperatura" stroke="#059669" strokeWidth={2} dot={false} connectNulls={false} />
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                    <p className="mt-2 text-xs text-gray-500">
                      {serie.length} puntos graficados. Si existen más de 300 lecturas, el gráfico muestra las 300 más recientes; las estadísticas usan todas las lecturas recibidas.
                    </p>
                  </>
                )}
              </EstadoSeccion>
            </section>

            <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
              <section className="rounded-lg border border-gray-200 bg-white p-4" aria-label="Predicción de la cámara">
                <div className="mb-3 flex items-center gap-2">
                  <Activity size={18} className="text-blue-700" />
                  <h3 className="font-semibold text-gray-800">Diagnóstico predictivo</h3>
                </div>
                <EstadoSeccion
                  loading={cargando}
                  error={errores.predicciones}
                  empty={!errores.predicciones && datos.predicciones !== null && !prediccion}
                  emptyText="El Worker Predictivo todavía no ha guardado una predicción para esta cámara. No se estima una predicción desde el dashboard."
                >
                  {prediccion && (
                    <div className="space-y-3">
                      <div className={`inline-flex items-center rounded-full border px-3 py-1 text-sm font-semibold ${riesgoClase(riesgo)}`}>
                        Riesgo: {nivelRiesgoTexto(riesgo)}
                      </div>
                      <div className="grid grid-cols-2 gap-3">
                        <div className="rounded-md bg-gray-50 p-3">
                          <p className="text-xs text-gray-500">Pendiente</p>
                          <p className="mt-1 font-semibold text-gray-800">{numero(pendiente, 4)} °C/min</p>
                        </div>
                        <div className="rounded-md bg-gray-50 p-3">
                          <p className="text-xs text-gray-500">Tiempo restante estimado</p>
                          <p className="mt-1 font-semibold text-gray-800">
                            {prediccion.remaining_time_min == null ? 'No calculable' : `${numero(prediccion.remaining_time_min)} min`}
                          </p>
                        </div>
                        <div className="rounded-md bg-gray-50 p-3">
                          <p className="text-xs text-gray-500">Temperatura proyectada</p>
                          <p className="mt-1 font-semibold text-gray-800">
                            {prediccion.projected_temperature == null ? '—' : `${numero(prediccion.projected_temperature)} °C`}
                          </p>
                        </div>
                        <div className="rounded-md bg-gray-50 p-3">
                          <p className="text-xs text-gray-500">Tendencia del modelo</p>
                          <p className="mt-1 flex items-center gap-2 font-semibold text-gray-800">{iconoTendencia}{tendencia}</p>
                        </div>
                      </div>
                      <p className="text-xs text-gray-500">
                        Predicción #{prediccion.id_prediction ?? 'sin ID'} · calculada: {fecha(prediccion.calculation_date)}
                      </p>
                    </div>
                  )}
                </EstadoSeccion>
              </section>

              <section className="rounded-lg border border-gray-200 bg-white p-4" aria-label="Regla HACCP de la cámara">
                <div className="mb-3 flex items-center gap-2">
                  <Clock3 size={18} className="text-amber-700" />
                  <h3 className="font-semibold text-gray-800">Regla HACCP aplicada</h3>
                </div>
                <EstadoSeccion
                  loading={cargando}
                  error={errores.regla}
                  empty={!errores.regla && datos.regla !== null && !datos.regla}
                  emptyText="No se recibió una regla HACCP para esta cámara."
                >
                  {datos.regla && (
                    <div className="space-y-3">
                      <div className={`inline-flex rounded-full border px-3 py-1 text-sm font-semibold ${datos.regla.active ? 'border-green-200 bg-green-50 text-green-800' : 'border-gray-200 bg-gray-100 text-gray-700'}`}>
                        {datos.regla.active ? 'Regla activa' : 'Regla inactiva'}
                      </div>
                      <div className="grid grid-cols-2 gap-3">
                        <div className="rounded-md bg-gray-50 p-3">
                          <p className="text-xs text-gray-500">Temperatura mínima</p>
                          <p className="mt-1 font-semibold text-gray-800">{numero(datos.regla.min_absolute_temp)} °C</p>
                        </div>
                        <div className="rounded-md bg-gray-50 p-3">
                          <p className="text-xs text-gray-500">Temperatura máxima</p>
                          <p className="mt-1 font-semibold text-gray-800">{numero(datos.regla.max_absolute_temp)} °C</p>
                        </div>
                        <div className="rounded-md bg-gray-50 p-3">
                          <p className="text-xs text-gray-500">Tolerancia</p>
                          <p className="mt-1 font-semibold text-gray-800">{numero(datos.regla.tolerance_time_min, 0)} min</p>
                        </div>
                        <div className="rounded-md bg-gray-50 p-3">
                          <p className="text-xs text-gray-500">Severidad configurada</p>
                          <p className="mt-1 font-semibold capitalize text-gray-800">{datos.regla.severity || 'No informada'}</p>
                        </div>
                      </div>
                      <p className="text-xs text-gray-500">
                        {datos.regla.id_rule == null
                          ? 'Valores predeterminados devueltos por Ingesta; no hay una regla persistida para esta cámara.'
                          : `Regla #${datos.regla.id_rule} · revisión: ${fecha(datos.regla.review_date)}`}
                      </p>
                    </div>
                  )}
                </EstadoSeccion>
              </section>
            </div>

            <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
              <section className="rounded-lg border border-gray-200 bg-white p-4" aria-label="Lecturas recientes">
                <h3 className="mb-3 font-semibold text-gray-800">Últimas lecturas recibidas</h3>
                <EstadoSeccion
                  loading={cargando}
                  error={errores.lecturas}
                  empty={!errores.lecturas && datos.lecturas !== null && !lecturas.length}
                  emptyText="No hay lecturas recientes para esta cámara."
                >
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm">
                      <thead>
                        <tr className="border-b text-xs uppercase text-gray-500">
                          <th className="py-2 pr-3">Fecha</th>
                          <th className="py-2 pr-3">Temperatura</th>
                          <th className="py-2">Consumo</th>
                        </tr>
                      </thead>
                      <tbody>
                        {[...lecturas].slice(-10).reverse().map((item) => (
                          <tr key={`${item.id_data ?? item.timestamp}-${item.timestamp}`} className="border-b border-gray-100 text-gray-700">
                            <td className="py-2 pr-3 whitespace-nowrap text-xs">{fecha(item.timestamp)}</td>
                            <td className="py-2 pr-3 font-semibold">{numero(item.temperature)} °C</td>
                            <td className="py-2">{item.consumption_kw == null ? '—' : `${numero(item.consumption_kw, 3)} kW`}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </EstadoSeccion>
              </section>

              <section className="rounded-lg border border-gray-200 bg-white p-4" aria-label="Valores atípicos detectados">
                <h3 className="mb-3 font-semibold text-gray-800">Valores atípicos detectados</h3>
                <EstadoSeccion
                  loading={cargando}
                  error={errores.lecturas}
                  empty={!errores.lecturas && estadisticas !== null && estadisticas.outliers.length === 0}
                  emptyText="No se detectaron valores fuera de los límites de Tukey en las últimas 24 horas."
                >
                  {estadisticas && estadisticas.outliers.length > 0 && (
                    <div className="space-y-2">
                      <p className="text-sm text-gray-600">
                        Límites estadísticos: {numero(estadisticas.lowerFence)} °C a {numero(estadisticas.upperFence)} °C.
                      </p>
                      {lecturasRecientes.map((item) => (
                        <div key={`${item.id_data ?? item.timestamp}-${item.timestamp}`} className="flex flex-wrap justify-between gap-2 rounded-md border border-orange-200 bg-orange-50 p-3 text-sm text-orange-900">
                          <span>{fecha(item.timestamp)}</span>
                          <strong>{numero(item.temperature)} °C</strong>
                        </div>
                      ))}
                      {estadisticas.outliers.length > lecturasRecientes.length && (
                        <p className="text-xs text-gray-500">Se muestran los 5 más recientes de {estadisticas.outliers.length} valores atípicos.</p>
                      )}
                    </div>
                  )}
                </EstadoSeccion>
              </section>
            </div>

            <section className="rounded-lg border border-gray-200 bg-white p-4" aria-label="Alertas recientes por cámara">
              <h3 className="mb-3 font-semibold text-gray-800">Alertas recientes de esta cámara</h3>
              <EstadoSeccion
                loading={cargando}
                error={errores.alertas}
                empty={!errores.alertas && datos.alertas !== null && !alertas.length}
                emptyText="Esta cámara no tiene alertas devueltas por la consulta actual."
              >
                <div className="space-y-2">
                  {alertas.slice(0, 10).map((alerta) => (
                    <article key={alerta.id_alert} className="flex flex-wrap items-start justify-between gap-2 rounded-md border border-gray-200 p-3">
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium text-gray-800">{alerta.message || alerta.alert_type || 'Alerta sin descripción'}</p>
                        <p className="mt-1 text-xs text-gray-500">{fecha(alerta.generation_date)} · Alerta #{alerta.id_alert}</p>
                      </div>
                      <div className="flex gap-2 text-xs">
                        <span className={`rounded-full border px-2 py-1 ${riesgoClase(alerta.severity)}`}>{alerta.severity || 'Sin severidad'}</span>
                        <span className="rounded-full border border-gray-200 bg-gray-50 px-2 py-1 text-gray-700">{alerta.status || 'Sin estado'}</span>
                      </div>
                    </article>
                  ))}
                </div>
              </EstadoSeccion>
            </section>
          </div>
        </>
      )}
    </section>
  );
};

export default DiagnosticoCamara;
