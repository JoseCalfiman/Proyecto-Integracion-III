// graficos de consumo electrico de los ultimos 7 dias, con recharts 
import React from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';

const ConsumptionChart = ({ data }) => {
  // Datos de ejemplo (reemplazar por datos reales de la API)
  const defaultData = data || [
    { day: 'Lun', kwh: 35 },
    { day: 'Mar', kwh: 42 },
    { day: 'Mié', kwh: 38 },
    { day: 'Jue', kwh: 45 },
    { day: 'Vie', kwh: 40 },
    { day: 'Sáb', kwh: 48 },
    { day: 'Dom', kwh: 46 },
  ];

  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-lg font-semibold text-gray-700">
            Historial de Consumo Eléctrico (7 Días)
          </h2>
          <p className="text-xs text-gray-500">
            Datos consultados del historial de la base de datos
          </p>
        </div>
        <div className="flex items-center gap-6 text-sm">
          <div>
            <p className="text-xs text-gray-500">CONSUMO TOTAL 7 DÍAS</p>
            <p className="text-lg font-bold text-green-600">294.5 kWh</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">PROMEDIO DIARIO</p>
            <p className="text-lg font-bold text-green-600">42.1 kWh</p>
          </div>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={250}>
        <LineChart data={defaultData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis dataKey="day" stroke="#9ca3af" />
          <YAxis
            stroke="#9ca3af"
            tickFormatter={(value) => `${value}kWh`}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#fff',
              border: '1px solid #e5e7eb',
              borderRadius: '8px',
            }}
            formatter={(value) => [`${value} kWh`, 'Consumo']}
          />
          <Line
            type="monotone"
            dataKey="kwh"
            stroke="#10b981"
            strokeWidth={3}
            dot={{ fill: '#10b981', r: 5 }}
            activeDot={{ r: 7 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default ConsumptionChart;