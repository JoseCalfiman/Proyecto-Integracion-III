import React, { useEffect, useState } from "react";
import { Camera, AlertTriangle, Zap, TrendingUp, Activity } from "lucide-react";
import MetricCard from "../../components/ui/MetricCard";
import ConsumptionChart from "../../components/charts/ConsumptionChart";
import { getDashboardLive, getConsumptionSeries } from "../../api/dashboard";

// Resumen de negocio: sin métricas de infraestructura ni datos simulados.
const RESUMEN_INTERVALO_MS = 15000; // Cada 15 segundos, para que la gerencia vea cambios de estado rápido.
const CONSUMO_INTERVALO_MS = 60000; // Cada 60 segundos, para no sobrecargar la API con series de consumo que cambian lentamente.
const numeroValido = (n) => n !== null && n !== undefined && Number.isFinite(Number(n));

const Dashboard = () => {
  const [datos, setDatos] = useState(null);
  const [consumo, setConsumo] = useState([]);
  const [cargaResumen, setCargaResumen] = useState(true);
  const [cargaConsumo, setCargaConsumo] = useState(true);
  const [errorResumen, setErrorResumen] = useState(null);
  const [errorConsumo, setErrorConsumo] = useState(null);
  const [ultimaActualizacion, setUltimaActualizacion] = useState(null);

  // Planificar la siguiente consulta al finalizar la anterior evita solapamientos.
  useEffect(() => {
    let vigente = true;
    let timeout;
    const actualizar = async () => {
      try {
        const respuesta = await getDashboardLive();
        if (!vigente) return;
        setDatos(respuesta);
        setErrorResumen(null);
        setUltimaActualizacion(new Date());
      } catch (error) {
        if (vigente) setErrorResumen(error.message);
      } finally {
        if (vigente) {
          setCargaResumen(false);
          timeout = setTimeout(actualizar, RESUMEN_INTERVALO_MS);
        }
      }
    };
    actualizar();
    return () => { vigente = false; clearTimeout(timeout); };
  }, []);

  useEffect(() => {
    let vigente = true;
    let timeout;
    const actualizar = async () => {
      try {
        const respuesta = await getConsumptionSeries(7);
        if (!vigente) return;
        setConsumo(Array.isArray(respuesta) ? respuesta : []);
        setErrorConsumo(null);
      } catch (error) {
        if (vigente) setErrorConsumo(error.message);
      } finally {
        if (vigente) {
          setCargaConsumo(false);
          timeout = setTimeout(actualizar, CONSUMO_INTERVALO_MS);
        }
      }
    };
    actualizar();
    return () => { vigente = false; clearTimeout(timeout); };
  }, []);

  const convertir = (n) => numeroValido(n) ? Number(n) : null;
  const camaras = convertir(datos?.active_chambers);
  const sinReconocer = convertir(datos?.active_alerts);
  const potencia = convertir(datos?.total_consumption_kw);
  const ahorro = convertir(datos?.estimated_savings_clp);
  const formato = (n, decimales = 0) => n === null ? "—" : n.toLocaleString("es-CL", {
    minimumFractionDigits: decimales, maximumFractionDigits: decimales,
  });

  // Backend /dashboard/live cuenta 'active', no 'acknowledged'.
  // Por eso no aseguramos que la planta esté saludable cuando el contador sea cero.
  const estado = errorResumen
    ? { titulo: "Datos sin actualizar", detalle: "No se pudo actualizar el resumen. Se muestra el último dato disponible.", estilo: "bg-amber-50 text-amber-800 border-amber-200" }
    : cargaResumen || !datos || sinReconocer === null
      ? { titulo: "Consultando estado", detalle: "Obteniendo indicadores de la planta.", estilo: "bg-gray-50 text-gray-700 border-gray-200" }
      : sinReconocer > 0
        ? { titulo: "Requiere atención", detalle: `${sinReconocer} alerta(s) sin reconocer. Revisar HACCP.`, estilo: "bg-red-50 text-red-800 border-red-200" }
        : { titulo: "Sin alertas sin reconocer", detalle: "Consultar HACCP para incidentes que ya fueron reconocidos.", estilo: "bg-green-50 text-green-800 border-green-200" };

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Resumen de la planta</h1>
          <p className="text-sm text-gray-500">Indicadores operativos y económicos para gerencia</p>
        </div>
        <p className="text-sm text-gray-500" aria-live="polite">
          {ultimaActualizacion ? `Actualizado: ${ultimaActualizacion.toLocaleTimeString("es-CL")}` : "Esperando datos de la API"}
        </p>
      </div>

      <section className={`mb-6 rounded-lg border px-5 py-4 ${estado.estilo}`} aria-live="polite">
        <div className="flex items-start gap-3">
          <Activity className="mt-0.5 shrink-0" size={22} aria-hidden="true" />
          <div>
            <h2 className="font-semibold">Estado de atención: {estado.titulo}</h2>
            <p className="text-sm mt-1">{estado.detalle}</p>
          </div>
        </div>
      </section>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6 mb-6">
        <MetricCard title="Cámaras habilitadas" value={cargaResumen ? "…" : formato(camaras)} icon={Camera} color="green" />
        <MetricCard title="Alertas sin reconocer" value={cargaResumen ? "…" : formato(sinReconocer)} icon={AlertTriangle} color="red" borderColor={sinReconocer > 0 ? "border-l-4 border-red-500" : undefined} />
        <MetricCard title="Potencia actual" value={cargaResumen ? "…" : formato(potencia, 2)} unit="kW" icon={Zap} color="yellow" />
        <MetricCard title="Ahorro potencial pendiente" value={cargaResumen ? "…" : ahorro === null ? "—" : `$${formato(ahorro)}`} unit="CLP" icon={TrendingUp} color="green" />
      </div>

      <p className="text-xs text-gray-500 mb-6">
        Cámaras habilitadas según registro; potencia instantánea en kW (no energía acumulada).
        El ahorro corresponde a recomendaciones pendientes, no a ahorro realizado.
      </p>
      {errorResumen && <p role="alert" className="mb-4 text-sm text-red-700">Error al consultar indicadores: {errorResumen}</p>}
      {errorConsumo && <p role="alert" className="mb-4 text-sm text-red-700">No se pudo actualizar la tendencia de consumo: {errorConsumo}</p>}
      <section aria-label="Tendencia de consumo energético">
        <ConsumptionChart data={consumo} loading={cargaConsumo} />
      </section>
    </div>
  );
};

export default Dashboard;