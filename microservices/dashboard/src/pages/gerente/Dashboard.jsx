import React, { useState, useEffect } from 'react';
import { Camera, AlertTriangle, Zap, TrendingUp } from 'lucide-react';
import MetricCard from '../../components/ui/MetricCard';
import TemperatureChart from '../../components/charts/TemperatureChart';
import ConsumptionChart from '../../components/charts/ConsumptionChart';

const Dashboard = () => {
  // TODO: conectar con API (GET /api/v1/dashboard/live)
  const [ultimaActualizacion, setUltimaActualizacion] = useState(new Date());

  useEffect(() => {
    const interval = setInterval(() => setUltimaActualizacion(new Date()), 2000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div>
      {/* Título */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Monitoreo en Vivo</h1>
          <p className="text-sm text-gray-500">Planta Principal - Sector Frío</p>
        </div>
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
          Última actualización: {ultimaActualizacion.toLocaleTimeString('es-CL')}
        </div>
      </div>

      {/* Tarjetas de resumen */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
        <MetricCard
          title="Total Cámaras"
          value="12"
          icon={Camera}
          color="green"
        />
        <MetricCard
          title="Alertas Activas"
          value="3"
          icon={AlertTriangle}
          color="red"
          borderColor="border-l-4 border-red-500"
        />
        <MetricCard
          title="Consumo Total"
          value="4.2"
          unit="kW"
          icon={Zap}
          color="yellow"
        />
        <MetricCard
          title="Ahorro Estimado"
          value="$125.000"
          unit="CLP"
          icon={TrendingUp}
          color="green"
        />
      </div>

      {/* Gráficos */}
      <div className="space-y-6">
        <TemperatureChart />
        <ConsumptionChart />
      </div>
    </div>
  );
};

export default Dashboard;