import React from 'react';
import { Camera, AlertTriangle, Zap, TrendingUp } from 'lucide-react';
import MetricCard from '../../components/ui/MetricCard';
import TemperatureChart from '../../components/charts/TemperatureChart';
import ConsumptionChart from '../../components/charts/ConsumptionChart';

const Dashboard = () => {
  return (
    <div>
      {/* Título */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Live Monitoring</h1>
          <p className="text-sm text-gray-500">Planta Principal - Sector Frío</p>
        </div>
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <span className="w-2 h-2 rounded-full bg-green-500"></span>
          Última actualización: 10:45:12 AM
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
          title="Active Alerts"
          value="3"
          icon={AlertTriangle}
          color="red"
          borderColor="border-l-4 border-red-500"
        />
        <MetricCard
          title="Total Power"
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