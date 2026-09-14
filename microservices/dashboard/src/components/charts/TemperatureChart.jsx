// graficos de temperatura de los ultimos 2 horas, con recharts

import React from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ReferenceLine, ResponsiveContainer, Legend,
} from 'recharts';

const TemperatureChart = ({ data }) => {
  // Datos de ejemplo (reemplazar por datos reales de la API)
  const defaultData = data || [
    { time: '-120s', temp: -2.5 },
    { time: '-90s', temp: -2.3 },
    { time: '-60s', temp: -2.8 },
    { time: '-30s', temp: -1.5 },
    { time: 'now', temp: 2.5 },
  ];

  return (
    <div className="bg-white p-6 rounded-lg shadow-md">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-700">
          Temperature Evolution (Last 2h)
        </h2>
        <div className="flex items-center gap-4 text-sm">
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-green-500"></span>
            <span className="text-gray-600">Avg Temp</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-4 h-0.5 bg-red-500"></span>
            <span className="text-gray-600">Limit (4°C)</span>
          </div>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={defaultData}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis dataKey="time" stroke="#9ca3af" />
          <YAxis
            stroke="#9ca3af"
            domain={[-6, 6]}
            ticks={[-6, -4, -2, 0, 2, 4, 6]}
            tickFormatter={(value) => `${value}°C`}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#fff',
              border: '1px solid #e5e7eb',
              borderRadius: '8px',
            }}
            formatter={(value) => [`${value}°C`, 'Temperatura']}
          />
          <ReferenceLine
            y={4}
            stroke="#ef4444"
            strokeDasharray="5 5"
            strokeWidth={2}
          />
          <Line
            type="monotone"
            dataKey="temp"
            stroke="#10b981"
            strokeWidth={3}
            dot={false}
            activeDot={{ r: 6 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default TemperatureChart;