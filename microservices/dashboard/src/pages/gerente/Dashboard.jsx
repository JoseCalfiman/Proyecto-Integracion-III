import React, { useState, useEffect } from "react";
import { Camera, AlertTriangle, Zap, TrendingUp } from "lucide-react";
import MetricCard from "../../components/ui/MetricCard";
import TemperatureChart from "../../components/charts/TemperatureChart";
import ConsumptionChart from "../../components/charts/ConsumptionChart";
import {
  getDashboardLive,
  getTemperatureSeries,
  getConsumptionSeries,
} from "../../api/dashboard";

const Dashboard = () => {
  const [ultimaActualizacion, setUltimaActualizacion] = useState(new Date());
  const [datos, setDatos] = useState({
    active_chambers: 0,
    active_alerts: 0,
    total_consumption_kw: 0,
    estimated_savings_clp: 0,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Series de los gráficos (arrays vacíos mientras cargan, para no mostrar datos falsos)
  const [temperatura, setTemperatura] = useState({ data: [], series: [] });
  const [consumo, setConsumo] = useState([]);
  const [errorGraficos, setErrorGraficos] = useState(null);

  // Tarjetas: cada 2 s
  useEffect(() => {
    const fetchDatos = async () => {
      try {
        setDatos(await getDashboardLive());
        setError(null);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
        setUltimaActualizacion(new Date());
      }
    };
    fetchDatos();
    const interval = setInterval(fetchDatos, 2000);
    return () => clearInterval(interval);
  }, []);

  // Gráficos: cada 30s
  useEffect(() => {
    const fetchGraficos = async () => {
      try {
        const [t, c] = await Promise.all([
          getTemperatureSeries(120),
          getConsumptionSeries(7),
        ]);
        setTemperatura(t);
        setConsumo(c);
        setErrorGraficos(null);
      } catch (err) {
        setErrorGraficos(err.message);
      }
    };
    fetchGraficos();
    const interval = setInterval(fetchGraficos, 30000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">
            Monitoreo en Vivo
          </h1>
          <p className="text-sm text-gray-500">
            Planta Principal - Sector Frío
          </p>
        </div>
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
          Última actualización:{" "}
          {ultimaActualizacion.toLocaleTimeString("es-CL")}
        </div>
      </div>

      {(error || errorGraficos) && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-2 rounded-lg mb-4 text-sm">
          {error || errorGraficos}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
        <MetricCard
          title="Total Cámaras"
          value={loading ? "..." : datos.active_chambers}
          icon={Camera}
          color="green"
        />
        <MetricCard
          title="Alertas Activas"
          value={loading ? "..." : datos.active_alerts}
          icon={AlertTriangle}
          color="red"
          borderColor="border-l-4 border-red-500"
        />
        <MetricCard
          title="Consumo Total"
          value={loading ? "..." : datos.total_consumption_kw?.toFixed(2)}
          unit="kW"r
          icon={Zap}
          color="yellow"
        />
        <MetricCard
          title="Ahorro Estimado"
          value={
            loading
              ? "..."
              : `$${(datos.estimated_savings_clp || 0).toLocaleString("es-CL")}`
          }
          unit="CLP"
          icon={TrendingUp}
          color="green"
        />
      </div>

      <div className="space-y-6">
        <TemperatureChart data={temperatura.data} series={temperatura.series} />
        <ConsumptionChart data={consumo} />
      </div>
    </div>
  );
};

export default Dashboard;