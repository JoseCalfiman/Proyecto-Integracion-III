import React, { useEffect, useMemo, useState } from "react";
import {
  BarChart, Bar, AreaChart, Area, CartesianGrid, XAxis, YAxis,
  Tooltip, ResponsiveContainer,
} from "recharts";
import { BarChart3, ChevronDown, ChevronUp, RefreshCw } from "lucide-react";
import { getAlertasParaEstadisticas } from "../../api/stats";
import { prepararEstadisticasAlertas, resumirConsumoDiario } from "../../utils/managerStats";

const formato = (valor) => Number(valor).toLocaleString("es-CL", {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
});

const TarjetaEstadistica = ({ titulo, valor, nota }) => (
  <div className="bg-gray-50 rounded-lg p-4 min-w-0">
    <p className="text-xs uppercase tracking-wide font-medium text-gray-500">{titulo}</p>
    <p className="mt-1 text-2xl font-semibold text-gray-800">{valor}</p>
    <p className="mt-1 text-xs text-gray-500">{nota}</p>
  </div>
);

// Se carga SOLO cuando el gerente solicita análisis. No se hacen consultas extra
// continuamente ni se carga una tabla con las 200 alertas en el DOM.
const ManagerAnalytics = ({ consumo = [] }) => {
  const [abierto, setAbierto] = useState(false);
  const [dias, setDias] = useState(7);
  const [recarga, setRecarga] = useState(0);
  const [registros, setRegistros] = useState([]);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState(null);
  const [cargado, setCargado] = useState(false);
  const [muestraLimitada, setMuestraLimitada] = useState(false);
  const [totalConsultadas, setTotalConsultadas] = useState(0);
  const [actualizado, setActualizado] = useState(null);

  useEffect(() => {
    if (!abierto) return undefined;
    const controller = new AbortController();
    let activo = true;
    setCargando(true);
    setError(null);
    getAlertasParaEstadisticas({ signal: controller.signal })
      .then(({ alertas, muestraLimitada: parcial, totalConsultadas: n }) => {
        if (!activo) return;
        setRegistros(alertas);
        setMuestraLimitada(parcial);
        setTotalConsultadas(n);
        setActualizado(new Date());
        setCargado(true);
      })
      .catch((err) => {
        if (activo) setError(err.message || "No se pudieron consultar las alertas.");
      })
      .finally(() => { if (activo) setCargando(false); });
    return () => { activo = false; controller.abort(); };
  }, [abierto, recarga]);

  const resumenConsumo = useMemo(() => resumirConsumoDiario(consumo), [consumo]);
  const estadisticas = useMemo(
    () => prepararEstadisticasAlertas(registros, dias),
    [registros, dias],
  );

  return (
    <section className="mt-6 bg-white rounded-lg shadow-md overflow-hidden" aria-label="Análisis estadístico gerencial">
      <button
        type="button"
        className="w-full px-6 py-5 flex items-center justify-between gap-4 text-left hover:bg-gray-50"
        onClick={() => setAbierto((actual) => !actual)}
        aria-expanded={abierto}
      >
        <span className="flex items-center gap-3">
          <BarChart3 size={22} className="text-green-600 shrink-0" aria-hidden="true" />
          <span>
            <span className="block text-lg font-semibold text-gray-800">Análisis estadístico de la planta</span>
            <span className="block text-xs text-gray-500">Comparaciones y tendencias con datos registrados</span>
          </span>
        </span>
        {abierto ? <ChevronUp size={20} aria-hidden="true" /> : <ChevronDown size={20} aria-hidden="true" />}
      </button>

      {abierto && (
        <div className="px-6 pb-6 space-y-6">
          <div>
            <h3 className="text-base font-semibold text-gray-800 mb-3">Consumo diario: resumen estadístico</h3>
            {resumenConsumo ? (
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <TarjetaEstadistica titulo="Media diaria" valor={`${formato(resumenConsumo.media)} kWh`} nota={`${resumenConsumo.n} días entregados por la API`} />
                <TarjetaEstadistica titulo="Mediana diaria" valor={`${formato(resumenConsumo.mediana)} kWh`} nota="Valor central ordenado" />
                <TarjetaEstadistica titulo="Desviación estándar" valor={`${formato(resumenConsumo.desviacion)} kWh`} nota="Variabilidad diaria, fórmula poblacional" />
              </div>
            ) : (
              <p className="text-sm text-gray-500">Aún no hay datos de consumo para calcular estadísticas.</p>
            )}
            <p className="text-xs text-gray-500 mt-2">
              Base: consumo total diario de los últimos 7 días. El backend devuelve 0 en días sin lecturas;
              ese 0 no demuestra ausencia de consumo.
            </p>
          </div>

          <div className="flex flex-wrap gap-3 items-center justify-between">
            <div>
              <h3 className="font-semibold text-gray-800">Análisis de alertas registradas</h3>
              <p className="text-xs text-gray-500">Incluye alertas activas, reconocidas y resueltas, sin contar lecturas individuales.</p>
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              <label className="text-sm text-gray-600" htmlFor="estadisticas-rango">Últimos</label>
              <select
                id="estadisticas-rango"
                className="border border-gray-200 rounded-md px-3 py-2 text-sm"
                value={dias}
                onChange={(e) => setDias(Number(e.target.value))}
              >
                <option value={7}>7 días</option>
                <option value={14}>14 días</option>
                <option value={30}>30 días</option>
              </select>
              <button
                type="button"
                className="inline-flex items-center gap-2 border border-gray-200 rounded-md px-3 py-2 text-sm hover:bg-gray-50 disabled:opacity-50"
                onClick={() => setRecarga((n) => n + 1)}
                disabled={cargando}
              >
                <RefreshCw size={15} aria-hidden="true" /> Actualizar
              </button>
            </div>
          </div>

          {error && <p role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}. No se muestran datos simulados.</p>}
          {cargando && !cargado && <p className="text-sm text-gray-500">Consultando alertas reales…</p>}
          {cargado && (
            <>
              <p className="text-xs text-gray-500" aria-live="polite">
                Se consultaron {totalConsultadas} registros recientes. {estadisticas.total} corresponden al periodo seleccionado.
                {actualizado && ` Actualizado: ${actualizado.toLocaleTimeString("es-CL")}.`}
                {cargando && " Actualizando…"}
              </p>
              {muestraLimitada && (
                <p className="text-xs text-amber-800 bg-amber-50 px-3 py-2 rounded-lg">
                  Muestra limitada a las 200 alertas más recientes: las cantidades podrían ser incompletas.
                  No son los totales oficiales de todas las alertas del periodo.
                </p>
              )}
              <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
                <div className="min-w-0 rounded-lg border border-gray-100 p-4">
                  <h4 className="font-semibold text-gray-700 mb-1">Evolución diaria de alertas</h4>
                  <p className="text-xs text-gray-500 mb-3">Registros generados por día · {dias} días</p>
                  {estadisticas.total === 0 ? (
                    <p className="h-[245px] flex items-center justify-center text-sm text-gray-500">No hay alertas en la muestra para este periodo.</p>
                  ) : (
                    <ResponsiveContainer width="100%" height={245}>
                      <AreaChart data={estadisticas.porDia} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                        <XAxis dataKey="etiqueta" minTickGap={25} stroke="#9ca3af" fontSize={11} />
                        <YAxis allowDecimals={false} stroke="#9ca3af" fontSize={11} />
                        <Tooltip formatter={(v) => [v, "Alertas generadas"]} />
                        <Area dataKey="cantidad" stroke="#2563eb" fill="#dbeafe" strokeWidth={2} isAnimationActive={false} />
                      </AreaChart>
                    </ResponsiveContainer>
                  )}
                </div>

                <div className="min-w-0 rounded-lg border border-gray-100 p-4">
                  <h4 className="font-semibold text-gray-700 mb-1">Top 5 cámaras con más alertas</h4>
                  <p className="text-xs text-gray-500 mb-3">Por cantidad de alertas registradas · {dias} días</p>
                  {estadisticas.ranking.length === 0 ? (
                    <p className="h-[245px] flex items-center justify-center text-sm text-gray-500">No hay cámaras con alertas en la muestra.</p>
                  ) : (
                    <ResponsiveContainer width="100%" height={245}>
                      <BarChart data={estadisticas.ranking} layout="vertical" margin={{ top: 8, right: 20, left: 10, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                        <XAxis type="number" allowDecimals={false} stroke="#9ca3af" fontSize={11} />
                        <YAxis type="category" dataKey="camara" width={135} tickFormatter={(nombre) => nombre.length > 20 ? `${nombre.slice(0, 20)}…` : nombre} stroke="#9ca3af" fontSize={11} />
                        <Tooltip formatter={(v) => [v, "Alertas registradas"]} />
                        <Bar dataKey="cantidad" fill="#0d9488" radius={[0, 4, 4, 0]} isAnimationActive={false} />
                      </BarChart>
                    </ResponsiveContainer>
                  )}
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </section>
  );
};

export default ManagerAnalytics;