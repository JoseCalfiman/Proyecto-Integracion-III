import React from 'react';
import { Camera, AlertTriangle, Activity, Wrench } from 'lucide-react';
import MetricCard from '../../components/ui/MetricCard';
import TemperatureChart from '../../components/charts/TemperatureChart';

const Dashboard = () => {
  return (
    <div>
      {/* Título */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Panel Técnico</h1>
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
          title="Cámaras Activas"
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
          title="Sensores Activos"
          value="24"
          icon={Activity}
          color="blue"
        />
        <MetricCard
          title="Mantenimientos"
          value="2"
          icon={Wrench}
          color="yellow"
        />
      </div>

      {/* Gráfico de temperatura */}
      <div className="space-y-6">
        <TemperatureChart />

        {/* Tabla de estado de sensores */}
        <div className="bg-white p-6 rounded-lg shadow-md">
          <h2 className="text-lg font-semibold text-gray-700 mb-4">
            Estado de Sensores
          </h2>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left py-2 text-gray-500 font-medium">Sensor</th>
                <th className="text-left py-2 text-gray-500 font-medium">Cámara</th>
                <th className="text-left py-2 text-gray-500 font-medium">Estado</th>
                <th className="text-left py-2 text-gray-500 font-medium">Última lectura</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-gray-100">
                <td className="py-3">Sensor Temp 01</td>
                <td className="py-3">Cámara Principal 01</td>
                <td className="py-3">
                  <span className="px-2 py-1 rounded-full text-xs bg-green-100 text-green-700">
                    Activo
                  </span>
                </td>
                <td className="py-3 text-gray-500">Hace 5s</td>
              </tr>
              <tr className="border-b border-gray-100">
                <td className="py-3">Sensor Consumo 01</td>
                <td className="py-3">Cámara Principal 01</td>
                <td className="py-3">
                  <span className="px-2 py-1 rounded-full text-xs bg-green-100 text-green-700">
                    Activo
                  </span>
                </td>
                <td className="py-3 text-gray-500">Hace 5s</td>
              </tr>
              <tr className="border-b border-gray-100">
                <td className="py-3">Sensor Temp 02</td>
                <td className="py-3">Cámara Principal 02</td>
                <td className="py-3">
                  <span className="px-2 py-1 rounded-full text-xs bg-yellow-100 text-yellow-700">
                    Mantenimiento
                  </span>
                </td>
                <td className="py-3 text-gray-500">Hace 10m</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;